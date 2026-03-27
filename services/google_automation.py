"""Public facade for Google One automation service."""

from services.google_automation_core.api import (
    check_offer_with_driver,
    close_driver,
    start_login,
    submit_2fa_code,
)
from services.google_automation_core.errors import GoogleAutomationError

__all__ = [
    "GoogleAutomationError",
    "start_login",
    "submit_2fa_code",
    "check_offer_with_driver",
    "close_driver",
]
