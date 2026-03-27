"""Reusable UI helpers for Telegram bot messages, keyboards, and i18n."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

DEFAULT_LANG = "en"
SUPPORTED_LANGS = {"en", "id"}

I18N = {
    "en": {
        "start_title": "🤖 *Pixel 10 Pro Google One Bot*",
        "start_body": (
            "Welcome! I can simulate a Pixel 10 Pro (Android 16), sign in to your "
            "Google account, and check whether your account has the *12-month Gemini Pro* offer."
        ),
        "start_tip": "💡 Gmail and Google Workspace accounts are supported.",
        "start_privacy": "🔒 Credentials are kept in memory only and are never stored permanently.",
        "lang_set": "🌐 Language set to English.",
    },
    "id": {
        "start_title": "🤖 *Bot Google One Pixel 10 Pro*",
        "start_body": (
            "Selamat datang! Bot ini bisa mensimulasikan Pixel 10 Pro (Android 16), "
            "login ke akun Google kamu, dan mengecek apakah akun kamu punya penawaran *Gemini Pro 12 bulan*."
        ),
        "start_tip": "💡 Mendukung akun Gmail dan Google Workspace.",
        "start_privacy": "🔒 Kredensial hanya disimpan di memori sesi dan tidak disimpan permanen.",
        "lang_set": "🌐 Bahasa diubah ke Indonesia.",
    },
}


def get_user_lang(context) -> str:
    """Return active language code for a user context."""
    lang = context.user_data.get("lang", DEFAULT_LANG)
    return lang if lang in SUPPORTED_LANGS else DEFAULT_LANG


def set_user_lang(context, lang: str) -> str:
    """Persist language preference and return the active language."""
    active = lang if lang in SUPPORTED_LANGS else DEFAULT_LANG
    context.user_data["lang"] = active
    return active


def tr(context, key: str) -> str:
    """Translate a UI message key based on current user language."""
    lang = get_user_lang(context)
    return I18N.get(lang, I18N[DEFAULT_LANG]).get(key, I18N[DEFAULT_LANG].get(key, key))


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Return a persistent command keyboard for easier bot navigation."""
    return ReplyKeyboardMarkup(
        [
            ["/login", "/check_offer"],
            ["/status", "/get_link"],
            ["/logout"],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
        is_persistent=True,
    )


def quick_actions_inline_keyboard() -> InlineKeyboardMarkup:
    """Inline quick actions that prefill slash commands in chat input."""
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Check Offer", switch_inline_query_current_chat="/check_offer"),
                InlineKeyboardButton("Status", switch_inline_query_current_chat="/status"),
            ],
            [
                InlineKeyboardButton("Get Link", switch_inline_query_current_chat="/get_link"),
                InlineKeyboardButton("Logout", switch_inline_query_current_chat="/logout"),
            ],
            [
                InlineKeyboardButton("English", switch_inline_query_current_chat="/lang_en"),
                InlineKeyboardButton("Indonesia", switch_inline_query_current_chat="/lang_id"),
            ],
        ]
    )


def build_session_overview(
    email: str,
    has_creds: bool,
    has_offer_link: bool,
    device_summary: str | None,
) -> str:
    """Return a formatted markdown status card for `/status`."""
    lines = [
        "📊 *Session Overview*\n",
        f"👤 Account: `{email}`",
        f"🔐 Credentials loaded: {'✅ Yes' if has_creds else '❌ No'}",
        f"🎁 Offer link captured: {'✅ Yes' if has_offer_link else '❌ No'}",
    ]
    if device_summary:
        lines.append("\n" + device_summary)
    return "\n".join(lines)
