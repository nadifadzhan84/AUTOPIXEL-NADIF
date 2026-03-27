"""Compatibility facade for split handler modules."""

from handlers.auth_handlers import (
    start,
    lang_en,
    lang_id,
    login_start,
    login_email,
    login_password,
    login_cancel,
    logout,
)
from handlers.offer_handlers import (
    check_offer,
    handle_2fa_code,
    cancel_2fa,
    offer_timeout,
)
from handlers.session_handlers import (
    get_link,
    status,
    session_cleanup_job,
)
from handlers.states import AWAIT_EMAIL, AWAIT_PASSWORD, AWAIT_2FA_CODE

__all__ = [
    "start",
    "lang_en",
    "lang_id",
    "login_start",
    "login_email",
    "login_password",
    "login_cancel",
    "logout",
    "check_offer",
    "handle_2fa_code",
    "cancel_2fa",
    "offer_timeout",
    "get_link",
    "status",
    "session_cleanup_job",
    "AWAIT_EMAIL",
    "AWAIT_PASSWORD",
    "AWAIT_2FA_CODE",
]
