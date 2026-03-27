"""Authentication-related Telegram handlers."""

import logging
import re
import time

from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler

import config
from core.session_manager import (
    SESSION_STORE,
    clear_session,
    get_session,
)
from services.device_simulator import create_device_profile

from handlers.states import AWAIT_EMAIL, AWAIT_PASSWORD
from handlers.ui import (
    main_menu_keyboard,
    quick_actions_inline_keyboard,
    set_user_lang,
    tr,
)

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send welcome message with command menu."""
    await update.message.reply_text(
        f"{tr(context, 'start_title')}\n\n"
        f"{tr(context, 'start_body')}\n\n"
        "*Quick Start*\n"
        "1. /login\n"
        "2. /check\\_offer\n"
        "3. /get\\_link\n\n"
        "*Commands*\n"
        "• /login - Save your account for this session\n"
        "• /logout - Clear session and credentials\n"
        "• /check\\_offer - Run offer detection\n"
        "• /get\\_link - Show the last captured link\n"
        "• /status - Show session and device info\n\n"
        "*Language*\n"
        "• /lang_en - English\n"
        "• /lang_id - Bahasa Indonesia\n\n"
        f"{tr(context, 'start_tip')}\n"
        f"{tr(context, 'start_privacy')}",
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(),
    )
    await update.message.reply_text(
        "⚡ Quick Actions",
        reply_markup=quick_actions_inline_keyboard(),
    )


async def lang_en(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Switch chat language to English."""
    set_user_lang(context, "en")
    await update.message.reply_text(
        tr(context, "lang_set"),
        reply_markup=main_menu_keyboard(),
    )


async def lang_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Switch chat language to Indonesian."""
    set_user_lang(context, "id")
    await update.message.reply_text(
        tr(context, "lang_set"),
        reply_markup=main_menu_keyboard(),
    )


async def login_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Begin the login conversation - ask for email."""
    await update.message.reply_text(
        "📧 Enter your Google email address "
        "(Gmail or Google Workspace).",
        reply_markup=ReplyKeyboardRemove(),
    )
    return AWAIT_EMAIL


async def login_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store the email and ask for password."""
    email = update.message.text.strip()

    if not re.match(r"^[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}$", email, re.IGNORECASE):
        await update.message.reply_text(
            "⚠️ Please enter a valid email address "
            "(e.g. user@gmail.com or user@company.com)."
        )
        return AWAIT_EMAIL

    allowed = config.ALLOWED_EMAIL_DOMAINS
    if allowed:
        domain = email.rsplit("@", 1)[1].lower()
        if domain not in [d.lower() for d in allowed]:
            domains_str = ", ".join(f"@{d}" for d in allowed)
            await update.message.reply_text(
                f"⚠️ Only the following email domains are accepted: "
                f"{domains_str}\n\nPlease try again."
            )
            return AWAIT_EMAIL

    context.user_data["pending_email"] = email
    await update.message.reply_text(
        f"✅ Email received: `{email}`\n\n🔒 Now send your password.\n"
        "Optional format: `password|totp_secret` for auto-2FA.",
        parse_mode="Markdown",
    )
    return AWAIT_PASSWORD


async def login_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store credentials, generate a new device profile, and finish."""
    chat_id = update.effective_chat.id
    raw_input = update.message.text.strip()
    email = context.user_data.pop("pending_email", "")

    if "|" in raw_input:
        password, totp_secret = raw_input.split("|", 1)
        password = password.strip()
        totp_secret = totp_secret.strip()
    else:
        password = raw_input
        totp_secret = None

    session = get_session(chat_id)
    session["email"] = bytearray(email.encode("utf-8"))
    session["password"] = bytearray(password.encode("utf-8"))
    if totp_secret:
        session["totp_secret"] = totp_secret
    session["device"] = create_device_profile()
    session["offer_link"] = None
    session["created_at"] = time.time()

    try:
        await update.message.delete()
    except Exception:
        pass

    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            "✅ *Credentials saved successfully.*\n"
            "A fresh Pixel 10 Pro profile has been created for this session.\n\n"
            + session["device"].summary()
            + (
                "\n\n🔑 TOTP secret detected. 2FA can be handled automatically."
                if totp_secret
                else ""
            )
            + "\n\nNext step: run /check\\_offer"
        ),
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(),
    )
    return ConversationHandler.END


async def login_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the login conversation."""
    context.user_data.pop("pending_email", None)
    await update.message.reply_text(
        "❌ Login flow cancelled.",
        reply_markup=main_menu_keyboard(),
    )
    return ConversationHandler.END


async def logout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clear stored credentials and destroy the session."""
    chat_id = update.effective_chat.id
    if chat_id in SESSION_STORE:
        clear_session(chat_id)
        await update.message.reply_text(
            "🔒 Credentials and session data were cleared successfully.",
            reply_markup=main_menu_keyboard(),
        )
    else:
        await update.message.reply_text(
            "ℹ️ No active session to clear.",
            reply_markup=main_menu_keyboard(),
        )
