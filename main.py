"""
Telegram Bot entry point for the Pixel 10 Pro Google One Gemini Bot.

Commands:
  /start        – Show welcome message and available commands
  /login        – Begin credential capture flow (email → password)
  /logout       – Clear stored credentials and session data
  /check_offer  – Run Google One automation and look for Gemini Pro offer
  /get_link     – Show the last captured offer link
  /status       – Show current session status and device profile

Supports both Gmail (user@gmail.com) and Google Workspace (user@company.com)
accounts.
"""

import logging
import os
import sys

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

import config
from handlers.bot_handlers import (
    AWAIT_2FA_CODE,
    AWAIT_EMAIL,
    AWAIT_PASSWORD,
    cancel_2fa,
    check_offer,
    get_link,
    handle_2fa_code,
    lang_en,
    lang_id,
    login_cancel,
    login_email,
    login_password,
    login_start,
    logout,
    offer_timeout,
    session_cleanup_job,
    start,
    status,
)

# ── Logging ───────────────────────────────────────────────────────────────────
from datetime import datetime as _dt

_LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(_LOG_DIR, exist_ok=True)

_formatter = logging.Formatter(config.LOG_FORMAT)

# Console handler
_console_handler = logging.StreamHandler()
_console_handler.setFormatter(_formatter)

# File handler – new file per startup: bot_YYYYMMDD_HHMMSS.log
_log_filename = f"bot_{_dt.now().strftime('%Y%m%d_%H%M%S')}.log"
_file_handler = logging.FileHandler(
    os.path.join(_LOG_DIR, _log_filename),
    encoding="utf-8",
)
_file_handler.setFormatter(_formatter)

logging.basicConfig(
    level=config.LOG_LEVEL,
    handlers=[_console_handler, _file_handler],
)
logger = logging.getLogger(__name__)


# ── Application setup ─────────────────────────────────────────────────────────

def main() -> None:
    token = config.TELEGRAM_BOT_TOKEN
    if not token:
        logger.error(
            "TELEGRAM_BOT_TOKEN environment variable is not set. "
            "Set it as an environment variable (e.g. via .env file or "
            "system environment) and restart."
        )
        sys.exit(1)

    app = Application.builder().token(token).build()

    # /login conversation
    login_conv = ConversationHandler(
        entry_points=[CommandHandler("login", login_start)],
        states={
            AWAIT_EMAIL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, login_email)
            ],
            AWAIT_PASSWORD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, login_password)
            ],
        },
        fallbacks=[CommandHandler("cancel", login_cancel)],
        allow_reentry=True,
    )

    offer_conv = ConversationHandler(
        entry_points=[CommandHandler("check_offer", check_offer)],
        states={
            AWAIT_2FA_CODE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_2fa_code)
            ],
            ConversationHandler.TIMEOUT: [
                MessageHandler(filters.ALL, offer_timeout)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_2fa)],
        allow_reentry=True,
        conversation_timeout=120,  # 2 minutes to enter 2FA code
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("lang_en", lang_en))
    app.add_handler(CommandHandler("lang_id", lang_id))
    app.add_handler(login_conv)
    app.add_handler(CommandHandler("logout", logout))
    app.add_handler(offer_conv)
    app.add_handler(CommandHandler("get_link", get_link))
    app.add_handler(CommandHandler("status", status))

    # Periodic job: purge expired sessions every 5 minutes
    app.job_queue.run_repeating(
        session_cleanup_job, interval=300, first=300,
    )

    logger.info("Bot is running. Press Ctrl-C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
