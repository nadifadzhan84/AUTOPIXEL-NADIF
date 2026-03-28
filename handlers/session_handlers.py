"""Session and status handlers."""

import asyncio
import html

from telegram import Update
from telegram.ext import ContextTypes

import config
from core.proxy_manager import PROXY_MANAGER, mask_proxy_url
from core.session_manager import (
    SESSION_STORE,
    get_session,
    purge_expired_sessions,
)
from handlers.ui import (
    build_session_overview,
    main_menu_keyboard,
    prepare_action_message,
    quick_actions_inline_keyboard,
    tr,
)
from services.network_diagnostics import format_connection_identity, inspect_connection


def _build_proxy_summary(context, proxy_url: str | None, direct_mode: bool = False) -> str:
    """Return a compact proxy summary for status views."""
    stats = PROXY_MANAGER.stats()
    if direct_mode:
        mode = tr(context, "proxy_summary_direct_locked")
    elif proxy_url:
        mode = mask_proxy_url(proxy_url)
    else:
        mode = tr(context, "proxy_summary_direct")
    return (
        f"🌐 {html.escape(mode)}\n"
        f"{html.escape(tr(context, 'proxy_summary_pool', available=stats['available'], total=stats['total']))}"
    )


async def get_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Return the last captured offer link for this session."""
    message = await prepare_action_message(update)
    chat_id = update.effective_chat.id
    session = get_session(chat_id)
    link = session.get("offer_link")

    if link:
        await message.reply_text(
            f"🔗 <b>Latest captured offer link</b>\n\n{link}",
            parse_mode="HTML",
            reply_markup=quick_actions_inline_keyboard(context),
        )
    else:
        await message.reply_text(
            "ℹ️ No offer link has been captured yet. "
            "Use /check\\_offer to search for the Gemini Pro offer.",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard(context),
        )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show current session and device profile summary."""
    message = await prepare_action_message(update)
    chat_id = update.effective_chat.id

    if chat_id not in SESSION_STORE or not SESSION_STORE[chat_id]:
        await message.reply_text(
            tr(context, "status_no_session"),
            reply_markup=main_menu_keyboard(context),
        )
        return

    session = SESSION_STORE[chat_id]
    email_raw = session.get("email", "-")
    if isinstance(email_raw, bytearray):
        email = bytes(email_raw).decode("utf-8")
    else:
        email = str(email_raw) if email_raw else "-"

    has_creds = bool(session.get("email") and session.get("password"))
    offer_link = session.get("offer_link")
    device = session.get("device")
    proxy_url = session.get("proxy")
    direct_mode = bool(session.get("proxy_disabled"))

    await message.reply_text(
        build_session_overview(
            context,
            email=email,
            has_creds=has_creds,
            has_offer_link=bool(offer_link),
            device_summary=device.summary() if device else None,
            proxy_summary=_build_proxy_summary(context, proxy_url, direct_mode=direct_mode),
        ),
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(context),
    )


async def proxy_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the current session proxy and global pool counters."""
    message = await prepare_action_message(update)
    chat_id = update.effective_chat.id
    session = get_session(chat_id)
    if not session.get("proxy_disabled") and not session.get("proxy") and config.PROXY_ENABLED:
        selected_proxy = PROXY_MANAGER.get_proxy()
        if selected_proxy:
            session["proxy"] = selected_proxy
    await message.reply_text(
        _build_proxy_summary(
            context,
            session.get("proxy"),
            direct_mode=bool(session.get("proxy_disabled")),
        ),
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(context),
    )


async def rotate_proxy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Rotate the current session proxy to another healthy entry."""
    message = await prepare_action_message(update)
    chat_id = update.effective_chat.id
    session = get_session(chat_id)
    session["proxy_disabled"] = False
    current_proxy = session.get("proxy")
    next_proxy = PROXY_MANAGER.get_proxy(excluded={current_proxy} if current_proxy else None)

    if next_proxy:
        session["proxy"] = next_proxy
        await message.reply_text(
            tr(context, "proxy_rotated", proxy=html.escape(mask_proxy_url(next_proxy))),
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(context),
        )
        return

    session.pop("proxy", None)
    stats = PROXY_MANAGER.stats()
    if stats["total"] == 0:
        text = tr(context, "proxy_no_pool")
    else:
        text = tr(context, "proxy_no_healthy")

    await message.reply_text(
        text,
        reply_markup=main_menu_keyboard(context),
    )


async def disable_proxy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Force the current session to use direct/local IP instead of the proxy pool."""
    message = await prepare_action_message(update)
    chat_id = update.effective_chat.id
    session = get_session(chat_id)
    already_disabled = bool(session.get("proxy_disabled"))
    session["proxy_disabled"] = True
    session.pop("proxy", None)

    await message.reply_text(
        tr(context, "proxy_disabled_already" if already_disabled else "proxy_disabled_set"),
        reply_markup=main_menu_keyboard(context),
    )


async def ip_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Probe the current public IP through the active session proxy."""
    message = await prepare_action_message(update)
    chat_id = update.effective_chat.id
    session = get_session(chat_id)
    proxy_url = session.get("proxy")
    if not session.get("proxy_disabled") and not proxy_url and config.PROXY_ENABLED:
        proxy_url = PROXY_MANAGER.get_proxy()
        if proxy_url:
            session["proxy"] = proxy_url

    await message.reply_text(tr(context, "ip_checking"))

    try:
        result = await asyncio.to_thread(inspect_connection, proxy_url)
    except Exception as exc:
        await message.reply_text(
            tr(context, "ip_check_failed", reason=exc),
            reply_markup=main_menu_keyboard(context),
        )
        return

    await message.reply_text(
        format_connection_identity(result, title=tr(context, "network_title")),
        reply_markup=main_menu_keyboard(context),
    )


async def session_cleanup_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Periodic callback to purge expired sessions."""
    purge_expired_sessions()
