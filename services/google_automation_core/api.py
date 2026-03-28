"""Public API for Google One automation service."""

import logging
import os
from datetime import datetime, timezone
from typing import Optional

import config
from services.device_simulator import DeviceProfile
from services.google_automation_core.driver_factory import build_driver
from services.google_automation_core.errors import GoogleAutomationError
from services.google_automation_core.login_flow import (
    gmail_login,
    get_signin_error_text,
    submit_totp_code,
    wait_for_login_resolution,
)
from services.google_automation_core.offer_scanner import (
    diagnose_google_one_page,
    navigate_google_one,
)

logger = logging.getLogger(__name__)


def dump_offer_debug_artifacts(
    driver,
    chat_id: int,
    attempt: int | None = None,
    session_id: str | None = None,
) -> dict[str, str]:
    """Persist screenshot + page HTML for a no-offer debugging snapshot."""
    project_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    dump_dir = os.path.join(project_root, "logs", "offer_debug", f"chat_{chat_id}")
    os.makedirs(dump_dir, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    token = (session_id or "nosession").replace("-", "")[:8]
    suffix = f"_attempt{attempt}" if attempt is not None else ""
    basename = f"{timestamp}_session_{token}{suffix}"

    screenshot_path = os.path.join(dump_dir, f"{basename}.png")
    html_path = os.path.join(dump_dir, f"{basename}.html")

    artifacts: dict[str, str] = {}
    current_url = ""
    try:
        current_url = driver.current_url or ""
    except Exception:
        current_url = ""

    try:
        driver.save_screenshot(screenshot_path)
        artifacts["screenshot"] = screenshot_path
    except Exception as exc:
        logger.warning("Failed to save no-offer screenshot for chat %s: %s", chat_id, exc)

    try:
        page_source = driver.page_source
        with open(html_path, "w", encoding="utf-8") as handle:
            if current_url:
                handle.write(f"<!-- URL: {current_url} -->\n")
            handle.write(page_source)
        artifacts["html"] = html_path
    except Exception as exc:
        logger.warning("Failed to save no-offer HTML for chat %s: %s", chat_id, exc)

    if artifacts:
        logger.info("Saved no-offer debug artifacts for chat %s", chat_id)

    return artifacts


def start_login(
    email: str,
    password: str,
    device: DeviceProfile,
    headless: bool | None = None,
    proxy_url: str | None = None,
) -> tuple:
    """Start login process and return (driver, status)."""
    effective_headless = config.HEADLESS if headless is None else headless
    logger.info(
        "Starting WebDriver for session %s (headless=%s)",
        device.session_id,
        effective_headless,
    )
    driver = build_driver(
        device,
        headless=effective_headless,
        proxy_url=proxy_url,
    )

    try:
        status = gmail_login(driver, email, password)
        if status == "failed":
            detail = get_signin_error_text(driver)
            driver.quit()
            if detail:
                raise GoogleAutomationError(f"Google sign-in rejected the login: {detail}")
            raise GoogleAutomationError(
                "Google sign-in rejected the login. "
                "This can be caused by invalid credentials, account protection, or proxy issues."
            )
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


def resolve_manual_login(driver, timeout: int = 10) -> str:
    """Wait briefly for a manual Google verification step to finish."""
    return wait_for_login_resolution(driver, timeout=timeout)


def check_offer_with_driver(driver) -> Optional[str]:
    """Navigate to Google One and find the Gemini Pro offer link."""
    return navigate_google_one(driver)


def diagnose_offer_page(driver) -> str | None:
    """Return a short diagnosis for the currently loaded Google One page."""
    return diagnose_google_one_page(driver)


def close_driver(driver) -> None:
    """Safely close WebDriver instance."""
    if driver:
        try:
            driver.quit()
        except Exception:
            pass
