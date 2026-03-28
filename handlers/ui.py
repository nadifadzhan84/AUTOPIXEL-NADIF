"""Reusable UI helpers for Telegram bot messages, keyboards, and i18n."""

from __future__ import annotations

import html
import logging
import os
import re

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, Update

import config

logger = logging.getLogger(__name__)

DEFAULT_LANG = "en"
SUPPORTED_LANGS = {"en", "id"}

MENU_ROWS = [
    ("menu_login", "menu_check_offer"),
    ("menu_status", "menu_get_link"),
    ("menu_proxy", "menu_ip"),
    ("menu_rotate_proxy", "menu_disable_proxy"),
    ("menu_lang_en", "menu_lang_id"),
    ("menu_home", "menu_logout"),
]

INLINE_PANEL_HEADER_KEY = "menu_panel_header"
INLINE_PANEL_FOOTER_KEY = "menu_panel_refresh"

I18N = {
    "en": {
        "start_title": "🚀 Pixel 10 Pro Google One Assistant",
        "start_header_caption": "🚀 Pixel Control Panel • Created by Nadif Rizky",
        "start_subtitle": "⌬ Pixel Control Panel • Google One • Modern Offer Deck",
        "start_body": (
            "A modern Telegram control deck for secure Google sign-in, Pixel 10 Pro "
            "device simulation, proxy-aware networking, and live Gemini offer checks."
        ),
        "start_deck_intro": "Use the control deck below to launch login, diagnostics, proxy tools, and offer checks in one tap.",
        "start_tip": "💡 Gmail and Google Workspace accounts are supported.",
        "start_privacy": "🔒 Credentials stay in memory only for the active session.",
        "creator_line": "Created by Nadif Rizky",
        "quick_actions_title": (
            "<b>⌬ Pixel Control Panel</b>\n"
            "<code>Pixel 10 Pro • Google One • Modern Offer Deck</code>\n"
            "<i>Created by Nadif Rizky</i>\n\n"
            "Tap a module below to continue."
        ),
        "section_quick_start": "Quick Start",
        "section_commands": "Core Commands",
        "section_language": "Language",
        "section_tools": "Modules",
        "section_session": "Session",
        "section_device": "Device Profile",
        "section_proxy": "Proxy Mode",
        "section_flow": "Recommended Flow",
        "section_power": "Power Tools",
        "start_flow_1": "Launch a secure login session with /login",
        "start_flow_2": "Review proxy identity or switch to direct mode",
        "start_flow_3": "Run /check_offer and inspect the live result",
        "command_login_desc": "Open a secure login session",
        "command_check_offer_desc": "Run the Gemini offer scanner",
        "command_get_link_desc": "Show the latest captured offer link",
        "command_status_desc": "View account, proxy, and device status",
        "command_proxy_desc": "Inspect the active proxy and pool",
        "command_ip_desc": "Check the current public IP and geo",
        "command_rotate_proxy_desc": "Switch to another proxy from the pool",
        "command_disable_proxy_desc": "Use your local/direct IP for this session",
        "command_lang_en_desc": "Switch the interface to English",
        "command_lang_id_desc": "Switch the interface to Indonesian",
        "command_logout_desc": "Clear the active session and browser state",
        "lang_set": "🌐 Language set to English.",
        "login_prompt_email": (
            "📧 [·] Login\n"
            "Send your Google email address.\n"
            "Supported: Gmail and Google Workspace."
        ),
        "login_invalid_email": (
            "⚠️ [·] Invalid Email\n"
            "Please enter a valid email address.\n"
            "Example: user@gmail.com or user@company.com."
        ),
        "login_password_prompt": (
            "✅ [·] Email Accepted\n"
            "<code>{email}</code>\n\n"
            "🔒 Send your password now.\n"
            "Optional format: <code>password|totp_secret</code>"
        ),
        "login_saved_title": "✅ [·] Session Ready",
        "login_saved_body": "Credentials saved successfully. A fresh Pixel 10 Pro profile is ready for this session.",
        "login_saved_totp": "🔑 TOTP secret detected. Auto-2FA is available for this session.",
        "login_saved_next": "Next step: run <code>/check_offer</code>",
        "login_cancelled": "❌ Login flow cancelled.",
        "logout_success": "🗑️ Session, credentials, and temporary browser state were cleared.",
        "logout_none": "ℹ️ No active session to clear.",
        "status_no_session": "ℹ️ No active session found. Run /login to get started.",
        "status_title": "📊 Session Overview",
        "status_account": "👤 Account",
        "status_creds": "🔐 Credentials loaded",
        "status_offer": "🎁 Offer link captured",
        "status_yes": "✅ Yes",
        "status_no": "❌ No",
        "proxy_summary_direct": "direct / local IP",
        "proxy_summary_direct_locked": "direct / local IP (manual override)",
        "proxy_summary_pool": "🧩 Proxy pool: {available}/{total} available",
        "proxy_disabled_set": "⛔ [·] Direct Mode Enabled\nThis session will now use your local/direct IP.",
        "proxy_disabled_already": "⛔ [·] Direct Mode Already Active\nThis session is already using your local/direct IP.",
        "proxy_rotated": "🔄 [·] Proxy Rotated\nNew proxy: <code>{proxy}</code>",
        "proxy_no_pool": "ℹ️ No proxies were loaded from the pool.\nThe bot will continue using a direct connection.",
        "proxy_no_healthy": "⚠️ No healthy alternative proxy is available right now.\nThe bot will continue using a direct connection.",
        "ip_checking": "🔎 Checking current network identity...",
        "ip_check_failed": "⚠️ IP check failed.\n\nReason: {reason}",
        "network_title": "🌍 Connection Identity",
        "proxy_panel_title": "🌍 Active Proxy Panel",
        "proxy_rotated_title": "🔄 Rotated Proxy Panel",
        "direct_panel_title": "🧷 Direct Network Panel",
        "menu_login": "🚀 Login",
        "menu_check_offer": "🎯 Check Offer",
        "menu_status": "📊 Status",
        "menu_get_link": "🔗 Get Link",
        "menu_proxy": "🌐 Proxy",
        "menu_ip": "🧭 Check IP",
        "menu_rotate_proxy": "🔄 Rotate Proxy",
        "menu_disable_proxy": "⛔ Direct Mode",
        "menu_lang_en": "🇺🇸 English",
        "menu_lang_id": "🇮🇩 Indonesian",
        "menu_home": "🏠 Home",
        "menu_logout": "🗑️ Logout",
        "menu_panel_header": "⌬ PIXEL CONTROL PANEL",
        "menu_panel_refresh": "🪄 Open Dashboard",
    },
    "id": {
        "start_title": "🚀 Pixel 10 Pro Google One Assistant",
        "start_header_caption": "🚀 Panel Kontrol Pixel • Created by Nadif Rizky",
        "start_subtitle": "⌬ Panel Kontrol Pixel • Google One • Deck Offer Modern",
        "start_body": (
            "Panel kontrol Telegram modern untuk login Google yang aman, simulasi "
            "device Pixel 10 Pro, jaringan berbasis proxy, dan pengecekan offer Gemini secara live."
        ),
        "start_deck_intro": "Gunakan control deck di bawah untuk membuka login, diagnostik, alat proxy, dan pengecekan offer hanya dengan satu tap.",
        "start_tip": "💡 Mendukung akun Gmail dan Google Workspace.",
        "start_privacy": "🔒 Kredensial hanya disimpan di memori selama sesi aktif.",
        "creator_line": "Dibuat oleh Nadif Rizky",
        "quick_actions_title": (
            "<b>⌬ Pixel Control Panel</b>\n"
            "<code>Pixel 10 Pro • Google One • Deck Offer Modern</code>\n"
            "<i>Created by Nadif Rizky</i>\n\n"
            "Pilih modul di bawah untuk melanjutkan."
        ),
        "section_quick_start": "Mulai Cepat",
        "section_commands": "Perintah Inti",
        "section_language": "Bahasa",
        "section_tools": "Modul",
        "section_session": "Sesi",
        "section_device": "Profil Device",
        "section_proxy": "Mode Proxy",
        "section_flow": "Alur Rekomendasi",
        "section_power": "Power Tools",
        "start_flow_1": "Mulai sesi login aman dengan /login",
        "start_flow_2": "Periksa identitas proxy atau pindah ke mode direct",
        "start_flow_3": "Jalankan /check_offer dan lihat hasil live-nya",
        "command_login_desc": "Buka sesi login yang aman",
        "command_check_offer_desc": "Jalankan scanner offer Gemini",
        "command_get_link_desc": "Tampilkan link offer terakhir yang tertangkap",
        "command_status_desc": "Lihat status akun, proxy, dan device",
        "command_proxy_desc": "Periksa proxy aktif dan pool",
        "command_ip_desc": "Cek IP publik dan geo saat ini",
        "command_rotate_proxy_desc": "Ganti ke proxy lain dari pool",
        "command_disable_proxy_desc": "Gunakan IP lokal/direct untuk sesi ini",
        "command_lang_en_desc": "Ubah antarmuka ke Bahasa Inggris",
        "command_lang_id_desc": "Ubah antarmuka ke Bahasa Indonesia",
        "command_logout_desc": "Hapus sesi aktif dan state browser sementara",
        "lang_set": "🌐 Bahasa diubah ke Indonesia.",
        "login_prompt_email": (
            "📧 [·] Login\n"
            "Kirim alamat email Google Anda.\n"
            "Didukung: Gmail dan Google Workspace."
        ),
        "login_invalid_email": (
            "⚠️ [·] Email Tidak Valid\n"
            "Masukkan alamat email yang valid.\n"
            "Contoh: user@gmail.com atau user@company.com."
        ),
        "login_password_prompt": (
            "✅ [·] Email Diterima\n"
            "<code>{email}</code>\n\n"
            "🔒 Sekarang kirim password Anda.\n"
            "Format opsional: <code>password|totp_secret</code>"
        ),
        "login_saved_title": "✅ [·] Sesi Siap",
        "login_saved_body": "Kredensial berhasil disimpan. Profil Pixel 10 Pro baru sudah siap untuk sesi ini.",
        "login_saved_totp": "🔑 TOTP terdeteksi. Auto-2FA tersedia untuk sesi ini.",
        "login_saved_next": "Langkah berikutnya: jalankan <code>/check_offer</code>",
        "login_cancelled": "❌ Alur login dibatalkan.",
        "logout_success": "🗑️ Sesi, kredensial, dan state browser sementara berhasil dibersihkan.",
        "logout_none": "ℹ️ Tidak ada sesi aktif untuk dibersihkan.",
        "status_no_session": "ℹ️ Tidak ada sesi aktif. Jalankan /login untuk memulai.",
        "status_title": "📊 Ringkasan Sesi",
        "status_account": "👤 Akun",
        "status_creds": "🔐 Kredensial dimuat",
        "status_offer": "🎁 Link offer tertangkap",
        "status_yes": "✅ Ya",
        "status_no": "❌ Tidak",
        "proxy_summary_direct": "direct / IP lokal",
        "proxy_summary_direct_locked": "direct / IP lokal (override manual)",
        "proxy_summary_pool": "🧩 Pool proxy: {available}/{total} tersedia",
        "proxy_disabled_set": "⛔ [·] Mode Direct Aktif\nSesi ini sekarang akan memakai IP lokal/direct Anda.",
        "proxy_disabled_already": "⛔ [·] Mode Direct Sudah Aktif\nSesi ini memang sudah memakai IP lokal/direct Anda.",
        "proxy_rotated": "🔄 [·] Proxy Diganti\nProxy baru: <code>{proxy}</code>",
        "proxy_no_pool": "ℹ️ Tidak ada proxy yang dimuat dari pool.\nBot akan lanjut memakai koneksi direct.",
        "proxy_no_healthy": "⚠️ Tidak ada proxy alternatif yang sehat saat ini.\nBot akan lanjut memakai koneksi direct.",
        "ip_checking": "🔎 Sedang memeriksa identitas jaringan...",
        "ip_check_failed": "⚠️ Cek IP gagal.\n\nAlasan: {reason}",
        "network_title": "🌍 Identitas Koneksi",
        "proxy_panel_title": "🌍 Panel Proxy Aktif",
        "proxy_rotated_title": "🔄 Panel Proxy Baru",
        "direct_panel_title": "🧷 Panel Jaringan Direct",
        "menu_login": "🚀 Login",
        "menu_check_offer": "🎯 Cek Offer",
        "menu_status": "📊 Status",
        "menu_get_link": "🔗 Ambil Link",
        "menu_proxy": "🌐 Proxy",
        "menu_ip": "🧭 Cek IP",
        "menu_rotate_proxy": "🔄 Ganti Proxy",
        "menu_disable_proxy": "⛔ Mode Direct",
        "menu_lang_en": "🇺🇸 Inggris",
        "menu_lang_id": "🇮🇩 Indonesia",
        "menu_home": "🏠 Beranda",
        "menu_logout": "🗑️ Logout",
        "menu_panel_header": "⌬ PANEL KONTROL PIXEL",
        "menu_panel_refresh": "🪄 Buka Dashboard",
    },
}


def get_user_lang(context) -> str:
    """Return active language code for a user context."""
    lang = getattr(context, "user_data", {}).get("lang", DEFAULT_LANG)
    return lang if lang in SUPPORTED_LANGS else DEFAULT_LANG


def set_user_lang(context, lang: str) -> str:
    """Persist language preference and return the active language."""
    active = lang if lang in SUPPORTED_LANGS else DEFAULT_LANG
    context.user_data["lang"] = active
    return active


def _resolve_lang(context=None, lang: str | None = None) -> str:
    if lang in SUPPORTED_LANGS:
        return lang
    if context is not None:
        return get_user_lang(context)
    return DEFAULT_LANG


def tr(context, key: str, **kwargs) -> str:
    """Translate a UI message key based on current user language."""
    lang = _resolve_lang(context)
    template = I18N.get(lang, I18N[DEFAULT_LANG]).get(
        key,
        I18N[DEFAULT_LANG].get(key, key),
    )
    return template.format(**kwargs) if kwargs else template


def menu_label(key: str, context=None, lang: str | None = None) -> str:
    """Return a translated menu label."""
    active_lang = _resolve_lang(context, lang)
    return I18N.get(active_lang, I18N[DEFAULT_LANG]).get(key, key)


def button_regex(key: str) -> str:
    """Return an exact-match regex for a menu button across all languages."""
    labels = [
        re.escape(I18N[lang][key])
        for lang in sorted(SUPPORTED_LANGS)
        if key in I18N[lang]
    ]
    return f"^({'|'.join(labels)})$"


def section_header(context, key: str) -> str:
    """Return a consistent section header."""
    return f"[·] <b>{html.escape(tr(context, key))}</b>"


def menu_callback_data(key: str) -> str:
    """Return callback data for an inline control-panel button."""
    if key in {INLINE_PANEL_HEADER_KEY, INLINE_PANEL_FOOTER_KEY, "menu_home"}:
        return "menu:home"
    return f"menu:{key.removeprefix('menu_')}"


async def prepare_action_message(update: Update):
    """Answer callback queries when needed and return the best reply target."""
    query = getattr(update, "callback_query", None)
    if query:
        try:
            await query.answer()
        except Exception:
            pass
    return update.effective_message


def send_header_media(context, chat_id: int, caption: str | None = None) -> None:
    """Compatibility shim for callers that may import this name directly."""
    raise RuntimeError("send_header_media is async; use send_header_media_async instead.")


async def send_header_media_async(context, chat_id: int, caption: str | None = None) -> None:
    """Send a header image or GIF when configured."""
    media_url = (config.BOT_HEADER_MEDIA_URL or "").strip()
    if not media_url:
        return

    try:
        lowered = media_url.lower()
        is_local_file = os.path.exists(media_url)
        if is_local_file:
            with open(media_url, "rb") as handle:
                if lowered.endswith((".gif", ".mp4")):
                    await context.bot.send_animation(
                        chat_id=chat_id,
                        animation=handle,
                        caption=caption,
                        parse_mode="HTML" if caption else None,
                    )
                else:
                    await context.bot.send_photo(
                        chat_id=chat_id,
                        photo=handle,
                        caption=caption,
                        parse_mode="HTML" if caption else None,
                    )
            return

        if lowered.endswith((".gif", ".mp4")):
            await context.bot.send_animation(
                chat_id=chat_id,
                animation=media_url,
                caption=caption,
                parse_mode="HTML" if caption else None,
            )
        else:
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=media_url,
                caption=caption,
                parse_mode="HTML" if caption else None,
            )
    except Exception as exc:
        logger.warning("Failed to send header media to chat %s: %s", chat_id, exc)


def main_menu_keyboard(context=None) -> ReplyKeyboardMarkup:
    """Return a persistent, emoji-rich navigation keyboard."""
    keyboard = [
        [menu_label(left, context), menu_label(right, context)]
        for left, right in MENU_ROWS
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
        is_persistent=True,
    )


def quick_actions_inline_keyboard(context=None) -> InlineKeyboardMarkup:
    """Return a tidy 2-column inline action grid."""
    rows = [
        [
            InlineKeyboardButton(
                menu_label(INLINE_PANEL_HEADER_KEY, context),
                callback_data=menu_callback_data("menu_home"),
            )
        ]
    ]
    for left, right in MENU_ROWS:
        rows.append(
            [
                InlineKeyboardButton(
                    menu_label(left, context),
                    callback_data=menu_callback_data(left),
                ),
                InlineKeyboardButton(
                    menu_label(right, context),
                    callback_data=menu_callback_data(right),
                ),
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(
                menu_label(INLINE_PANEL_FOOTER_KEY, context),
                callback_data=menu_callback_data(INLINE_PANEL_FOOTER_KEY),
            )
        ]
    )
    return InlineKeyboardMarkup(rows)


def build_welcome_message(context) -> str:
    """Return the redesigned start/welcome card."""
    lines = [
        f"<b>{html.escape(tr(context, 'start_title'))}</b>",
        f"<code>{html.escape(tr(context, 'start_subtitle'))}</code>",
        f"👑 <b>{html.escape(tr(context, 'creator_line'))}</b>",
        "",
        html.escape(tr(context, "start_body")),
        "",
        f"🔥 {section_header(context, 'section_tools')}",
        html.escape(tr(context, "start_deck_intro")),
        "",
        f"⚡ {section_header(context, 'section_quick_start')}",
        f"• 🚀 <code>/login</code> · {html.escape(tr(context, 'command_login_desc'))}",
        f"• 🎯 <code>/check_offer</code> · {html.escape(tr(context, 'command_check_offer_desc'))}",
        f"• 🔗 <code>/get_link</code> · {html.escape(tr(context, 'command_get_link_desc'))}",
        "",
        f"🧭 {section_header(context, 'section_flow')}",
        f"• 1 · {html.escape(tr(context, 'start_flow_1'))}",
        f"• 2 · {html.escape(tr(context, 'start_flow_2'))}",
        f"• 3 · {html.escape(tr(context, 'start_flow_3'))}",
        "",
        f"🧩 {section_header(context, 'section_commands')}",
        f"• 📊 <code>/status</code> · {html.escape(tr(context, 'command_status_desc'))}",
        f"• 🌐 <code>/proxy</code> · {html.escape(tr(context, 'command_proxy_desc'))}",
        f"• 🧭 <code>/ip</code> · {html.escape(tr(context, 'command_ip_desc'))}",
        f"• 🔄 <code>/rotate_proxy</code> · {html.escape(tr(context, 'command_rotate_proxy_desc'))}",
        f"• ⛔ <code>/disable_proxy</code> · {html.escape(tr(context, 'command_disable_proxy_desc'))}",
        "",
        f"🛠️ {section_header(context, 'section_power')}",
        f"• 🇺🇸 <code>/lang_en</code> · {html.escape(tr(context, 'command_lang_en_desc'))}",
        f"• 🇮🇩 <code>/lang_id</code> · {html.escape(tr(context, 'command_lang_id_desc'))}",
        f"• 🗑️ <code>/logout</code> · {html.escape(tr(context, 'command_logout_desc'))}",
        "",
        f"🛡️ {html.escape(tr(context, 'start_privacy'))}",
        f"💡 {html.escape(tr(context, 'start_tip'))}",
    ]
    return "\n".join(lines)


def build_session_overview(
    context,
    email: str,
    has_creds: bool,
    has_offer_link: bool,
    device_summary: str | None,
    proxy_summary: str | None = None,
) -> str:
    """Return a formatted HTML status card for `/status`."""
    lines = [
        f"<b>{html.escape(tr(context, 'status_title'))}</b>",
        f"<code>{html.escape(tr(context, 'start_subtitle'))}</code>",
        f"👑 <b>{html.escape(tr(context, 'creator_line'))}</b>",
        "",
        section_header(context, "section_session"),
        f"{html.escape(tr(context, 'status_account'))}: <code>{html.escape(email)}</code>",
        f"{html.escape(tr(context, 'status_creds'))}: {tr(context, 'status_yes') if has_creds else tr(context, 'status_no')}",
        f"{html.escape(tr(context, 'status_offer'))}: {tr(context, 'status_yes') if has_offer_link else tr(context, 'status_no')}",
    ]
    if proxy_summary:
        lines.append("")
        lines.append(section_header(context, "section_proxy"))
        lines.append(proxy_summary)
    if device_summary:
        lines.append("")
        lines.append(section_header(context, "section_device"))
        lines.append(device_summary)
    return "\n".join(lines)
