"""Session and status handlers."""

from telegram import Update
from telegram.ext import ContextTypes

from core.session_manager import (
    SESSION_STORE,
    get_session,
    purge_expired_sessions,
)
from handlers.ui import (
    build_session_overview,
    main_menu_keyboard,
    quick_actions_inline_keyboard,
)


async def get_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Return the last captured offer link for this session."""
    chat_id = update.effective_chat.id
    session = get_session(chat_id)
    link = session.get("offer_link")

    if link:
        await update.message.reply_text(
            f"🔗 <b>Latest captured offer link</b>\n\n{link}",
            parse_mode="HTML",
            reply_markup=quick_actions_inline_keyboard(),
        )
    else:
        await update.message.reply_text(
            "ℹ️ No offer link has been captured yet. "
            "Use /check\\_offer to search for the Gemini Pro offer.",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard(),
        )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show current session and device profile summary."""
    chat_id = update.effective_chat.id

    if chat_id not in SESSION_STORE or not SESSION_STORE[chat_id]:
        await update.message.reply_text(
            "ℹ️ No active session found. Run /login to get started.",
            reply_markup=main_menu_keyboard(),
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

    await update.message.reply_text(
        build_session_overview(
            email=email,
            has_creds=has_creds,
            has_offer_link=bool(offer_link),
            device_summary=device.summary() if device else None,
        ),
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(),
    )


async def session_cleanup_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Periodic callback to purge expired sessions."""
    purge_expired_sessions()
