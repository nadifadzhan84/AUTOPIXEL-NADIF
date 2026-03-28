"""Public facade for Google One automation service."""

from services.google_automation_core.api import (
    check_offer_with_driver,
    close_driver,
    diagnose_offer_page,
    dump_offer_debug_artifacts,
    resolve_manual_login,
    start_login,
    submit_2fa_code,
)
from services.google_automation_core.errors import GoogleAutomationError

__all__ = [
    "GoogleAutomationError",
    "start_login",
    "submit_2fa_code",
    "resolve_manual_login",
    "check_offer_with_driver",
    "diagnose_offer_page",
    "dump_offer_debug_artifacts",
    "close_driver",
]
