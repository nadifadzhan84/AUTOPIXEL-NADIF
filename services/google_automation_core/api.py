"""Public API for Google One automation service."""

import logging
from typing import Optional

from services.device_simulator import DeviceProfile
from services.google_automation_core.driver_factory import build_driver
from services.google_automation_core.errors import GoogleAutomationError
from services.google_automation_core.login_flow import gmail_login, submit_totp_code
from services.google_automation_core.offer_scanner import navigate_google_one

logger = logging.getLogger(__name__)


def start_login(email: str, password: str, device: DeviceProfile) -> tuple:
    """Start login process and return (driver, status)."""
    logger.info("Starting WebDriver for session %s", device.session_id)
    driver = build_driver(device)

    try:
        status = gmail_login(driver, email, password)
        if status == "failed":
            driver.quit()
            raise GoogleAutomationError("Login failed - please check your credentials.")
        return driver, status
    except GoogleAutomationError:
        driver.quit()
        raise
    except Exception:
        driver.quit()
        raise


def submit_2fa_code(driver, code: str) -> bool:
    """Submit TOTP code on a driver that is on the 2FA challenge page."""
    return submit_totp_code(driver, code)


def check_offer_with_driver(driver) -> Optional[str]:
    """Navigate to Google One and find the Gemini Pro offer link."""
    return navigate_google_one(driver)


def close_driver(driver) -> None:
    """Safely close WebDriver instance."""
    if driver:
        try:
            driver.quit()
        except Exception:
            pass
