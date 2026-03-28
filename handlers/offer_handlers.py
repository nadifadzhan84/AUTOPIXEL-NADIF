"""Offer detection and 2FA-related handlers."""

import asyncio
import logging
import random
import time

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

import config
from core.proxy_manager import PROXY_MANAGER, mask_proxy_url
from core.runtime_state import (
    CHECK_OFFER_COOLDOWN,
    CHROME_SEMAPHORE,
    LAST_CHECK_TIME,
)
from core.session_manager import (
    SESSION_STORE,
    get_session,
    secure_wipe,
)
from services.device_simulator import create_device_profile
from services.google_automation import (
    GoogleAutomationError,
    check_offer_with_driver,
    close_driver,
    diagnose_offer_page,
    dump_offer_debug_artifacts,
    resolve_manual_login,
    start_login,
    submit_2fa_code,
)
from services.network_diagnostics import (
    format_connection_identity,
    inspect_connection,
    probe_google_signin,
)

from handlers.states import AWAIT_2FA_CODE, AWAIT_MANUAL_VERIFICATION
from handlers.ui import (
    main_menu_keyboard,
    prepare_action_message,
    quick_actions_inline_keyboard,
    tr,
)

logger = logging.getLogger(__name__)


def _clear_pending_verification(session: dict) -> None:
    """Drop temporary verification metadata from the session."""
    session.pop("_manual_challenge_type", None)


def _format_artifact_note(artifacts: dict[str, str] | None) -> str:
    """Return a short text block that points to saved debug artifacts."""
    if not artifacts:
        return ""

    lines = ["", "Debug artifacts saved:"]
    screenshot_path = artifacts.get("screenshot")
    html_path = artifacts.get("html")
    if screenshot_path:
        lines.append(f"Screenshot: {screenshot_path}")
    if html_path:
        lines.append(f"HTML: {html_path}")
    return "\n".join(lines)


def _format_diagnostic_note(diagnostic: str | None) -> str:
    """Return a short diagnostic block for no-offer results."""
    if not diagnostic:
        return ""
    return f"\n\nDiagnosis: {diagnostic}"


def _is_manual_challenge_error(exc: Exception) -> bool:
    """Return True when login failed because Google requested non-TOTP verification."""
    message = str(exc).lower()
    return "no authenticator option found" in message and "requires" in message


def _is_dead_driver_error(exc: Exception) -> bool:
    """Return True when Chrome/WebDriver session has already died."""
    message = str(exc).lower()
    signals = (
        "invalid session id",
        "session deleted",
        "not connected to devtools",
        "chrome not reachable",
        "target window already closed",
        "disconnected",
    )
    return any(signal in message for signal in signals)


def _driver_session_is_alive(driver) -> bool:
    """Return False when the stored WebDriver can no longer answer commands."""
    if not driver:
        return False
    try:
        _ = driver.current_url
        return True
    except Exception:
        return False


def _looks_like_proxy_error(exc: Exception) -> bool:
    """Return True for errors that are likely caused by proxy/network transport."""
    message = str(exc).lower()
    signals = (
        "proxy",
        "timeout",
        "timed out",
        "connection",
        "tunnel",
        "refused",
        "dns",
        "net::err",
        "ssl",
        "unreachable",
    )
    return any(signal in message for signal in signals)


async def _safe_send_bot_message(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    text: str,
    **kwargs,
) -> None:
    """Send a Telegram message without letting a transport timeout crash the handler."""
    try:
        await context.bot.send_message(chat_id=chat_id, text=text, **kwargs)
    except Exception as exc:
        logger.warning("Failed to send Telegram message to chat %s: %s", chat_id, exc)


async def _send_proxy_identity_panel(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    proxy_url: str | None,
    title: str,
) -> None:
    """Probe the selected proxy and send a readable info panel."""
    try:
        result = await asyncio.to_thread(inspect_connection, proxy_url)
    except Exception as exc:
        logger.warning(
            "Failed to inspect proxy identity for chat %s via %s: %s",
            chat_id,
            mask_proxy_url(proxy_url),
            exc,
        )
        await _safe_send_bot_message(
            context,
            chat_id=chat_id,
            text=(
                f"{title}\n"
                f"🌐 Proxy: {mask_proxy_url(proxy_url)}\n"
                f"⚠️ Detailed proxy identity lookup failed: {exc}"
            ),
        )
        return

    await _safe_send_bot_message(
        context,
        chat_id=chat_id,
        text=format_connection_identity(result, title=title),
    )


async def _report_offer(
    update_or_chat_id,
    context,
    session,
    offer_link,
    artifacts: dict[str, str] | None = None,
    diagnostic: str | None = None,
) -> None:
    """Send the offer result message."""
    chat_id = (
        update_or_chat_id
        if isinstance(update_or_chat_id, int)
        else update_or_chat_id.effective_chat.id
    )
    if offer_link:
        session["offer_link"] = offer_link
        text = (
            "🎉 <b>Gemini Pro Offer Found!</b>\n\n"
            "Use the link below to activate your 12-month free Gemini Pro:\n\n"
            f"🔗 {offer_link}\n\n"
            "You can run /get_link anytime to retrieve this link again."
        )
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="HTML",
                reply_markup=quick_actions_inline_keyboard(context),
            )
        except Exception:
            await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    "🎉 Gemini Pro Offer Found!\n\n"
                    f"🔗 {offer_link}\n\n"
                    "You can run /get_link anytime to retrieve this link again."
                ),
                reply_markup=main_menu_keyboard(context),
            )
    else:
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "😔 No active Gemini Pro offer was detected on your Google One "
                "account at this time.\n\n"
                "The offer may not be available for your account region or may "
                "have already been activated. You can try again later."
                f"{_format_diagnostic_note(diagnostic)}"
                f"{_format_artifact_note(artifacts)}"
            ),
            reply_markup=quick_actions_inline_keyboard(context),
        )


async def check_offer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Run Google One automation and report the result."""
    max_offer_attempts = 3
    message = await prepare_action_message(update)
    chat_id = update.effective_chat.id
    session = get_session(chat_id)
    stale_driver = session.pop("_driver", None)
    close_driver(stale_driver)
    _clear_pending_verification(session)

    if not session.get("email") or not session.get("password"):
        await message.reply_text(
            "⚠️ No credentials found. Run /login first.",
            reply_markup=main_menu_keyboard(context),
        )
        return ConversationHandler.END

    last_check = LAST_CHECK_TIME.get(chat_id, 0)
    elapsed = time.time() - last_check
    if elapsed < CHECK_OFFER_COOLDOWN:
        remaining = int(CHECK_OFFER_COOLDOWN - elapsed)
        mins, secs = divmod(remaining, 60)
        await message.reply_text(f"⏳ Please wait {mins}m {secs}s before checking again.")
        return ConversationHandler.END
    LAST_CHECK_TIME[chat_id] = time.time()

    if CHROME_SEMAPHORE.locked():
        await message.reply_text(
            "🔄 The system is currently at maximum capacity. Please try again in a minute.",
            reply_markup=main_menu_keyboard(context),
        )
        LAST_CHECK_TIME.pop(chat_id, None)
        return ConversationHandler.END

    await message.reply_text(
        "⏳ Starting secure check...\n"
        "Launching Pixel 10 Pro simulation and signing in.\n"
        "This usually takes up to 60 seconds."
    )

    offer_link = None
    no_offer_artifacts: dict[str, str] | None = None
    no_offer_diagnostic: str | None = None
    try:
        async with CHROME_SEMAPHORE:
            email_str = bytes(session["email"]).decode("utf-8")
            pw_str = bytes(session["password"]).decode("utf-8")
            device = session.get("device")
            if not device:
                device = create_device_profile()
                session["device"] = device
            used_proxies: set[str] = set()
            proxy_url = None
            if config.PROXY_ENABLED and not session.get("proxy_disabled"):
                proxy_url = PROXY_MANAGER.get_proxy(preferred=session.get("proxy"))
                if proxy_url:
                    session["proxy"] = proxy_url
                    await _send_proxy_identity_panel(
                        context,
                        chat_id,
                        proxy_url,
                        tr(context, "proxy_panel_title"),
                    )
                else:
                    session.pop("proxy", None)
                    await _send_proxy_identity_panel(
                        context,
                        chat_id,
                        None,
                        tr(context, "direct_panel_title"),
                    )
            else:
                session.pop("proxy", None)
                await _send_proxy_identity_panel(
                    context,
                    chat_id,
                    None,
                    tr(context, "direct_panel_title"),
                )

            for attempt in range(1, max_offer_attempts + 1):
                if attempt > 1:
                    await message.reply_text(
                        f"🔄 Retry {attempt}/{max_offer_attempts}: "
                        "reusing the same session device and trying again."
                    )

                driver = None
                preserve_driver = False
                proxy_latency_ms = 0.0
                try:
                    if proxy_url and config.PROXY_PRECHECK_ENABLED:
                        try:
                            probe_result = await asyncio.to_thread(
                                probe_google_signin,
                                proxy_url,
                                config.PROXY_PRECHECK_TIMEOUT_SECONDS,
                            )
                            proxy_latency_ms = float(probe_result["latency_ms"])
                            logger.info(
                                "Proxy preflight passed for chat %s via %s in %.2f ms",
                                chat_id,
                                mask_proxy_url(proxy_url),
                                proxy_latency_ms,
                            )
                        except Exception as exc:
                            logger.warning(
                                "Proxy preflight failed for chat %s via %s: %s",
                                chat_id,
                                mask_proxy_url(proxy_url),
                                exc,
                            )
                            if attempt < max_offer_attempts:
                                PROXY_MANAGER.mark_failed(proxy_url, "precheck_failed")
                                used_proxies.add(proxy_url)
                                next_proxy = PROXY_MANAGER.get_proxy(excluded=used_proxies)
                                if next_proxy:
                                    proxy_url = next_proxy
                                    session["proxy"] = proxy_url
                                    await _safe_send_bot_message(
                                        context,
                                        chat_id=chat_id,
                                        text="⚠️ Proxy precheck failed before opening Chrome. Rotating proxy...",
                                    )
                                    await _send_proxy_identity_panel(
                                        context,
                                        chat_id,
                                        proxy_url,
                                        tr(context, "proxy_rotated_title"),
                                    )
                                    continue
                            raise GoogleAutomationError(
                                f"Proxy precheck failed before opening Chrome: {exc}"
                            ) from exc

                    try:
                        driver, status = await asyncio.to_thread(
                            start_login,
                            email_str,
                            pw_str,
                            device,
                            proxy_url=proxy_url,
                        )
                    except GoogleAutomationError as exc:
                        if config.HEADLESS and _is_manual_challenge_error(exc):
                            await message.reply_text(
                                "🔐 Google requested manual verification.\n"
                                "Reopening Chrome in visible mode with the same session device..."
                            )
                            driver, status = await asyncio.to_thread(
                                start_login,
                                email_str,
                                pw_str,
                                device,
                                False,
                                proxy_url,
                            )
                        else:
                            raise

                    if proxy_url:
                        PROXY_MANAGER.mark_success(proxy_url, latency_ms=proxy_latency_ms)

                    if status == "needs_totp":
                        totp_secret = session.get("totp_secret")
                        if totp_secret:
                            try:
                                import pyotp

                                code = pyotp.TOTP(totp_secret).now()
                                logger.info(
                                    "Auto-generated TOTP code for chat %s (attempt %d)",
                                    chat_id,
                                    attempt,
                                )
                                accepted = await asyncio.to_thread(submit_2fa_code, driver, code)
                                if not accepted:
                                    close_driver(driver)
                                    driver = None
                                    await message.reply_text(
                                        "❌ Auto-generated TOTP code was rejected. "
                                        "Please check your TOTP secret key.",
                                        reply_markup=main_menu_keyboard(context),
                                    )
                                    return ConversationHandler.END

                                await message.reply_text(
                                    f"✅ Login successful ({attempt}/{max_offer_attempts}).\n"
                                    "Checking Gemini Pro offer now..."
                                )
                                offer_link = await asyncio.to_thread(check_offer_with_driver, driver)
                                if not offer_link and attempt == max_offer_attempts:
                                    no_offer_diagnostic = await asyncio.to_thread(
                                        diagnose_offer_page,
                                        driver,
                                    )
                                    no_offer_artifacts = await asyncio.to_thread(
                                        dump_offer_debug_artifacts,
                                        driver,
                                        chat_id,
                                        attempt,
                                        device.session_id,
                                    )
                            except Exception as exc:
                                logger.warning("Auto-TOTP failed: %s", exc)
                                close_driver(driver)
                                driver = None
                                await message.reply_text(
                                    f"❌ Auto-TOTP error: {exc}\n"
                                    "Please check your TOTP secret key.",
                                    reply_markup=main_menu_keyboard(context),
                                )
                                return ConversationHandler.END
                        else:
                            session["_driver"] = driver
                            preserve_driver = True
                            await message.reply_text(
                                "🔐 *Two-Factor Authentication Required*\n\n"
                                "Please send your 6-digit authenticator code *here in Telegram only*.\n"
                                "Do not type that code in the Chrome window.",
                                parse_mode="Markdown",
                            )
                            return AWAIT_2FA_CODE
                    elif status == "needs_manual_verification":
                        challenge_type = getattr(
                            driver,
                            "_autopixel_challenge_type",
                            "manual verification",
                        )
                        session["_driver"] = driver
                        session["_manual_challenge_type"] = challenge_type
                        preserve_driver = True
                        await message.reply_text(
                            "🔐 Manual verification required.\n\n"
                            f"Google requested: {challenge_type}\n"
                            "Complete that step in the Chrome window that just opened.\n"
                            "After the browser leaves the Google sign-in page, send `done` here.\n"
                            "Send /cancel to stop this check.",
                            parse_mode="Markdown",
                        )
                        return AWAIT_MANUAL_VERIFICATION
                    else:
                        await message.reply_text(
                            f"✅ Login successful ({attempt}/{max_offer_attempts}).\n"
                            "Checking Gemini Pro offer now..."
                        )
                        offer_link = await asyncio.to_thread(check_offer_with_driver, driver)
                        if not offer_link and attempt == max_offer_attempts:
                            no_offer_diagnostic = await asyncio.to_thread(
                                diagnose_offer_page,
                                driver,
                            )
                            no_offer_artifacts = await asyncio.to_thread(
                                dump_offer_debug_artifacts,
                                driver,
                                chat_id,
                                attempt,
                                device.session_id,
                            )
                except GoogleAutomationError as exc:
                    if proxy_url and _looks_like_proxy_error(exc) and attempt < max_offer_attempts:
                        PROXY_MANAGER.mark_failed(proxy_url, "automation_error")
                        used_proxies.add(proxy_url)
                        next_proxy = PROXY_MANAGER.get_proxy(excluded=used_proxies)
                        if next_proxy:
                            proxy_url = next_proxy
                            session["proxy"] = proxy_url
                            await _safe_send_bot_message(
                                context,
                                chat_id=chat_id,
                                text="⚠️ Proxy transport issue detected. Rotating proxy...",
                            )
                            await _send_proxy_identity_panel(
                                context,
                                chat_id,
                                proxy_url,
                                tr(context, "proxy_rotated_title"),
                            )
                            continue
                    raise
                except Exception as exc:
                    if proxy_url and _looks_like_proxy_error(exc) and attempt < max_offer_attempts:
                        PROXY_MANAGER.mark_failed(proxy_url, "runtime_error")
                        used_proxies.add(proxy_url)
                        next_proxy = PROXY_MANAGER.get_proxy(excluded=used_proxies)
                        if next_proxy:
                            proxy_url = next_proxy
                            session["proxy"] = proxy_url
                            await _safe_send_bot_message(
                                context,
                                chat_id=chat_id,
                                text="⚠️ Runtime network issue detected. Rotating proxy...",
                            )
                            await _send_proxy_identity_panel(
                                context,
                                chat_id,
                                proxy_url,
                                tr(context, "proxy_rotated_title"),
                            )
                            continue
                    raise
                finally:
                    if driver and not preserve_driver:
                        close_driver(driver)

                if offer_link:
                    logger.info(
                        "Offer found on attempt %d for chat %s: %s",
                        attempt,
                        chat_id,
                        offer_link,
                    )
                    break

                logger.info(
                    "No offer found on attempt %d/%d for chat %s",
                    attempt,
                    max_offer_attempts,
                    chat_id,
                )

                if attempt < max_offer_attempts:
                    delay = random.randint(15, 30)
                    await message.reply_text(
                        f"⏳ Offer not found yet. Retrying in {delay} seconds..."
                    )
                    await asyncio.sleep(delay)
                    await message.reply_text(
                        f"🔄 Starting retry {attempt + 1}/{max_offer_attempts}: "
                        "reusing the same session device and signing in again."
                    )

    except GoogleAutomationError as exc:
        await message.reply_text(
            f"❌ <b>Automation Error:</b> {exc}",
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(context),
        )
        return ConversationHandler.END
    except Exception as exc:
        logger.exception("Unexpected error in check_offer for chat %s", chat_id)
        await message.reply_text(f"❌ An unexpected error occurred: {exc}")
        return ConversationHandler.END
    finally:
        pw = session.get("password")
        if isinstance(pw, bytearray):
            secure_wipe(pw)
        session.pop("password", None)

    if not offer_link:
        await message.reply_text(
            f"❌ No Gemini Pro offer found after {max_offer_attempts} attempts.\n\n"
            "Possible reasons:\n"
            "• Your account region is not eligible\n"
            "• An active Gemini subscription already exists\n"
            "• Family group eligibility has already been used\n"
            "• New-account risk controls are in effect"
            f"{_format_diagnostic_note(no_offer_diagnostic)}"
            f"{_format_artifact_note(no_offer_artifacts)}",
            reply_markup=quick_actions_inline_keyboard(context),
        )
        return ConversationHandler.END

    await _report_offer(update, context, session, offer_link)
    return ConversationHandler.END


async def handle_2fa_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the TOTP code submitted by the user during 2FA."""
    chat_id = update.effective_chat.id
    session = get_session(chat_id)
    code = update.message.text.strip()
    preserve_driver = False
    artifacts: dict[str, str] | None = None
    diagnostic: str | None = None

    try:
        await update.message.delete()
    except Exception:
        pass

    driver = session.pop("_driver", None)
    if not driver:
        _clear_pending_verification(session)
        await _safe_send_bot_message(
            context,
            chat_id=chat_id,
            text="⚠️ Session expired. Please run /check\\_offer again.",
            reply_markup=main_menu_keyboard(context),
        )
        return ConversationHandler.END

    if not _driver_session_is_alive(driver):
        _clear_pending_verification(session)
        close_driver(driver)
        await _safe_send_bot_message(
            context,
            chat_id=chat_id,
            text=(
                "⚠️ The Chrome verification session has already closed or crashed.\n"
                "Please run /check\\_offer again."
            ),
            reply_markup=main_menu_keyboard(context),
        )
        return ConversationHandler.END

    if not code.isdigit() or len(code) != 6:
        await _safe_send_bot_message(
            context,
            chat_id=chat_id,
            text="⚠️ Invalid code. Please enter a 6-digit number.",
            reply_markup=main_menu_keyboard(context),
        )
        session["_driver"] = driver
        return AWAIT_2FA_CODE

    await _safe_send_bot_message(context, chat_id=chat_id, text="🔄 Verifying code…")

    try:
        async with CHROME_SEMAPHORE:
            accepted = await asyncio.to_thread(submit_2fa_code, driver, code)

            if not accepted:
                session["_driver"] = driver
                preserve_driver = True
                await _safe_send_bot_message(
                    context,
                    chat_id=chat_id,
                    text=(
                        "❌ Code rejected or expired.\n"
                        "Please send a fresh 6-digit authenticator code.\n"
                        "Send /cancel to stop this check."
                    ),
                    reply_markup=main_menu_keyboard(context),
                )
                return AWAIT_2FA_CODE

            try:
                offer_link = await asyncio.to_thread(check_offer_with_driver, driver)
                if not offer_link:
                    diagnostic = await asyncio.to_thread(diagnose_offer_page, driver)
                    device = session.get("device")
                    artifacts = await asyncio.to_thread(
                        dump_offer_debug_artifacts,
                        driver,
                        chat_id,
                        None,
                        getattr(device, "session_id", None),
                    )
            finally:
                close_driver(driver)

    except Exception as exc:
        logger.exception("Error in 2FA for chat %s", chat_id)
        close_driver(driver)
        error_text = (
            "⚠️ The Chrome verification session has already closed or crashed.\n"
            "Please run /check\\_offer again."
            if _is_dead_driver_error(exc)
            else f"❌ Error: {exc}"
        )
        await _safe_send_bot_message(context, chat_id=chat_id, text=error_text)
        return ConversationHandler.END
    finally:
        if not preserve_driver:
            _clear_pending_verification(session)
            pw = session.get("password")
            if isinstance(pw, bytearray):
                secure_wipe(pw)
            session.pop("password", None)

    await _report_offer(
        chat_id,
        context,
        session,
        offer_link,
        artifacts=artifacts,
        diagnostic=diagnostic,
    )
    return ConversationHandler.END


async def handle_manual_verification(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """Continue the offer flow after the user finishes manual Chrome verification."""
    chat_id = update.effective_chat.id
    session = get_session(chat_id)
    preserve_driver = False
    artifacts: dict[str, str] | None = None
    diagnostic: str | None = None

    try:
        await update.message.delete()
    except Exception:
        pass

    driver = session.pop("_driver", None)
    challenge_type = session.get("_manual_challenge_type", "manual verification")
    if not driver:
        _clear_pending_verification(session)
        await _safe_send_bot_message(
            context,
            chat_id=chat_id,
            text="⚠️ Session expired. Please run /check\\_offer again.",
            reply_markup=main_menu_keyboard(context),
        )
        return ConversationHandler.END

    if not _driver_session_is_alive(driver):
        _clear_pending_verification(session)
        close_driver(driver)
        await _safe_send_bot_message(
            context,
            chat_id=chat_id,
            text=(
                "⚠️ The Chrome verification window has already closed or crashed.\n"
                "Please run /check\\_offer again."
            ),
            reply_markup=main_menu_keyboard(context),
        )
        return ConversationHandler.END

    await _safe_send_bot_message(
        context,
        chat_id=chat_id,
        text="🔄 Checking the Chrome window…",
    )

    try:
        state = await asyncio.to_thread(resolve_manual_login, driver, 8)
        if state == "needs_totp":
            session["_driver"] = driver
            preserve_driver = True
            await _safe_send_bot_message(
                context,
                chat_id=chat_id,
                text=(
                    "🔐 *Two-Factor Authentication Required*\n\n"
                    "Google has moved to the authenticator-code step.\n"
                    "Please send your 6-digit code *here in Telegram only*.\n"
                    "Do not type that code in the Chrome window."
                ),
                parse_mode="Markdown",
                reply_markup=main_menu_keyboard(context),
            )
            return AWAIT_2FA_CODE

        if state in {"challenge", "signin"}:
            session["_driver"] = driver
            preserve_driver = True
            await _safe_send_bot_message(
                context,
                chat_id=chat_id,
                text=(
                    "⏳ Google is still waiting for verification in Chrome.\n"
                    f"Pending step: {challenge_type}\n"
                    "Finish it there first, then send `done` again.\n"
                    "Send /cancel to stop this check."
                ),
                parse_mode="Markdown",
                reply_markup=main_menu_keyboard(context),
            )
            return AWAIT_MANUAL_VERIFICATION

        await _safe_send_bot_message(
            context,
            chat_id=chat_id,
            text="✅ Verification completed. Checking Gemini Pro offer now...",
        )
        try:
            offer_link = await asyncio.to_thread(check_offer_with_driver, driver)
            if not offer_link:
                diagnostic = await asyncio.to_thread(diagnose_offer_page, driver)
                device = session.get("device")
                artifacts = await asyncio.to_thread(
                    dump_offer_debug_artifacts,
                    driver,
                    chat_id,
                    None,
                    getattr(device, "session_id", None),
                )
        finally:
            close_driver(driver)

    except Exception as exc:
        logger.exception("Error in manual verification for chat %s", chat_id)
        close_driver(driver)
        error_text = (
            "⚠️ The Chrome verification window has already closed or crashed.\n"
            "Please run /check\\_offer again."
            if _is_dead_driver_error(exc)
            else f"❌ Error: {exc}"
        )
        await _safe_send_bot_message(context, chat_id=chat_id, text=error_text)
        return ConversationHandler.END
    finally:
        if not preserve_driver:
            _clear_pending_verification(session)
            pw = session.get("password")
            if isinstance(pw, bytearray):
                secure_wipe(pw)
            session.pop("password", None)

    await _report_offer(
        chat_id,
        context,
        session,
        offer_link,
        artifacts=artifacts,
        diagnostic=diagnostic,
    )
    return ConversationHandler.END


async def cancel_2fa(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel a pending verification step and close the driver."""
    chat_id = update.effective_chat.id
    session = get_session(chat_id)
    driver = session.pop("_driver", None)
    _clear_pending_verification(session)
    close_driver(driver)
    await update.message.reply_text(
        "❌ Verification cancelled.",
        reply_markup=main_menu_keyboard(context),
    )
    return ConversationHandler.END


async def offer_timeout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle conversation timeout by cleaning up a pending verification flow."""
    if update and update.effective_chat:
        chat_id = update.effective_chat.id
        session = SESSION_STORE.get(chat_id, {})
        driver = session.pop("_driver", None)
        _clear_pending_verification(session)
        close_driver(driver)
        await context.bot.send_message(
            chat_id=chat_id,
            text="⏰ Verification timed out. Please run /check_offer again.",
            reply_markup=main_menu_keyboard(context),
        )
    return ConversationHandler.END
