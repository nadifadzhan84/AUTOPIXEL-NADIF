"""Google account login and TOTP challenge handlers."""

import logging
import time
from urllib.parse import urlparse

from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

import config
from services.google_automation_core.errors import GoogleAutomationError

logger = logging.getLogger(__name__)


def _driver_is_headless(driver: webdriver.Chrome) -> bool:
    """Return whether this driver instance is running headless."""
    return bool(getattr(driver, "_autopixel_headless", config.HEADLESS))


def _is_google_challenge_url(url: str) -> bool:
    """Return True when Google is still showing a sign-in challenge page."""
    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    path = parsed.path or ""
    return hostname == "accounts.google.com" and "challenge" in path


def get_signin_error_text(driver: webdriver.Chrome) -> str | None:
    """Return visible Google sign-in error text when present."""
    selectors = (
        '[jsname="B34EJ"]',
        '[aria-live="assertive"]',
        '[role="alert"]',
    )
    for selector in selectors:
        try:
            element = driver.find_element(By.CSS_SELECTOR, selector)
        except NoSuchElementException:
            continue

        text = " ".join((element.text or "").split())
        if text:
            return text

    return None


def get_login_debug_snapshot(driver: webdriver.Chrome) -> dict[str, str]:
    """Return a small snapshot of the current login page for diagnostics."""
    current_url = ""
    title = ""
    excerpt = ""

    try:
        current_url = driver.current_url or ""
    except Exception:
        current_url = ""

    try:
        title = " ".join((driver.title or "").split())
    except Exception:
        title = ""

    selectors = ("body", "main", '[role="main"]')
    for selector in selectors:
        try:
            element = driver.find_element(By.CSS_SELECTOR, selector)
        except NoSuchElementException:
            continue

        text = " ".join((element.text or "").split())
        if text:
            excerpt = text[:240]
            break

    return {
        "url": current_url,
        "title": title,
        "excerpt": excerpt,
    }


def get_google_login_state(driver: webdriver.Chrome) -> str:
    """Return a coarse login state for the current Google page."""
    parsed = urlparse(driver.current_url)
    hostname = parsed.hostname or ""
    path = parsed.path or ""

    if _is_google_challenge_url(driver.current_url):
        if _is_totp_challenge(driver):
            return "needs_totp"
        return "challenge"

    if hostname == "accounts.google.com" and path.startswith("/signin"):
        return "signin"

    if hostname == "myaccount.google.com":
        return "success"

    if hostname.endswith(".google.com") and "/u/" in path:
        return "success"

    if hostname.endswith(".google.com") and "signin" not in path:
        return "success"

    return "unknown"


def wait_for_login_resolution(driver: webdriver.Chrome, timeout: int = 10) -> str:
    """Wait briefly for Google to leave the sign-in/challenge flow."""
    deadline = time.time() + timeout
    state = get_google_login_state(driver)

    while time.time() < deadline and state in {"challenge", "signin"}:
        time.sleep(0.5)
        state = get_google_login_state(driver)

    return state


def _has_totp_error(driver: webdriver.Chrome) -> bool:
    """Best-effort detection of inline TOTP errors on the Google challenge page."""
    try:
        page_text = driver.page_source.lower()
    except Exception:
        return False

    error_indicators = (
        "wrong code",
        "incorrect code",
        "invalid code",
        "enter a valid code",
        "couldn't verify",
        "could not verify",
        "try again",
        "expired code",
    )
    return any(indicator in page_text for indicator in error_indicators)


def _is_totp_challenge(driver: webdriver.Chrome) -> bool:
    """Return True only when the challenge page really looks like TOTP input."""
    specific_selectors = ('input[name="totpPin"]', "#totpPin")
    for selector in specific_selectors:
        try:
            driver.find_element(By.CSS_SELECTOR, selector)
            return True
        except NoSuchElementException:
            continue

    try:
        driver.find_element(By.CSS_SELECTOR, 'input[type="tel"]')
    except NoSuchElementException:
        return False

    page_text = driver.page_source.lower()
    positive_indicators = (
        "authenticator",
        "google authenticator",
        "verification code",
        "6-digit",
        "6 digit",
        "enter the code",
        "totp",
    )
    negative_indicators = (
        "security key",
        "usb",
        "phone",
        "sms",
        "tap yes",
        "google prompt",
    )

    return (
        any(indicator in page_text for indicator in positive_indicators)
        and not any(indicator in page_text for indicator in negative_indicators)
    )


def _resolve_post_password_state(driver: webdriver.Chrome, email: str) -> str:
    """Resolve the Google login state after password submission with retries."""
    deadline = time.time() + 15
    last_exc: Exception | None = None

    while time.time() < deadline:
        try:
            current_url = driver.current_url
            parsed = urlparse(current_url)
            hostname = parsed.hostname or ""
            path = parsed.path or ""

            challenge_paths = ("/signin/v2/challenge", "/signin/challenge", "/v2/challenge")
            if hostname == "accounts.google.com" and any(p in path for p in challenge_paths):
                if _is_totp_challenge(driver):
                    logger.info("TOTP 2FA challenge confirmed for %s - awaiting code", email)
                    return "needs_totp"

                switched_to_totp = False
                try:
                    for opt_xpath in (
                        '//*[@data-challengetype="6"]',
                        '//div[@data-challengetype="6"]',
                        '//div[contains(text(), "Authenticator")]',
                        '//div[contains(text(), "authenticator")]',
                        '//div[contains(text(), "Google Authenticator")]',
                        '//div[contains(text(), "verification code")]',
                        '//li[contains(., "Authenticator")]',
                        '//li[contains(., "authenticator")]',
                    ):
                        try:
                            driver.find_element(By.XPATH, opt_xpath).click()
                            time.sleep(2)
                            switched_to_totp = True
                            break
                        except NoSuchElementException:
                            continue

                    if not switched_to_totp:
                        for selector in (
                            '//a[contains(text(), "another way")]',
                            '//button[contains(text(), "another way")]',
                            '//a[contains(text(), "other way")]',
                            '//a[contains(text(), "Try another")]',
                            '//span[contains(text(), "another way")]/ancestor::a',
                            '//span[contains(text(), "another way")]/ancestor::button',
                        ):
                            try:
                                try_another = driver.find_element(By.XPATH, selector)
                                try_another.click()
                                time.sleep(2)
                                break
                            except NoSuchElementException:
                                continue

                        for opt_xpath in (
                            '//*[@data-challengetype="6"]',
                            '//div[@data-challengetype="6"]',
                            '//div[contains(text(), "Authenticator")]',
                            '//div[contains(text(), "authenticator")]',
                            '//div[contains(text(), "Google Authenticator")]',
                            '//div[contains(text(), "verification code")]',
                            '//li[contains(., "Authenticator")]',
                        ):
                            try:
                                driver.find_element(By.XPATH, opt_xpath).click()
                                time.sleep(1)
                                switched_to_totp = True
                                break
                            except NoSuchElementException:
                                continue

                    if switched_to_totp and _is_totp_challenge(driver):
                        return "needs_totp"
                except Exception as exc:
                    logger.warning("Error trying alternative 2FA: %s", exc)

                page_text = driver.page_source.lower()
                if "security key" in page_text or "usb" in page_text:
                    challenge_type = "security key"
                elif "phone" in page_text or "sms" in page_text:
                    challenge_type = "SMS / phone verification"
                elif "tap yes" in page_text or "google prompt" in page_text:
                    challenge_type = "Google prompt (tap Yes on your phone)"
                else:
                    challenge_type = "two-step verification"

                if not _driver_is_headless(driver):
                    setattr(driver, "_autopixel_challenge_type", challenge_type)
                    logger.info(
                        "Manual verification required for %s: %s",
                        email,
                        challenge_type,
                    )
                    return "needs_manual_verification"

                raise GoogleAutomationError(
                    f"Your account requires {challenge_type}. "
                    f"No authenticator option found. "
                    f"Please use an App Password instead."
                )

            if hostname == "myaccount.google.com" or (hostname.endswith(".google.com") and "/u/" in path):
                return "success"

            if get_signin_error_text(driver):
                return "failed"

            if not (hostname == "accounts.google.com" and path.startswith("/signin")):
                return "success"

            time.sleep(0.5)
        except StaleElementReferenceException as exc:
            last_exc = exc
            time.sleep(0.5)
        except WebDriverException as exc:
            last_exc = exc
            time.sleep(0.5)

    if last_exc:
        logger.warning("Transient WebDriver issue while resolving login state: %s", last_exc)
    raise GoogleAutomationError(
        "Timed out while waiting for Google sign-in to continue. "
        "This usually points to a proxy/network issue or an unsupported challenge."
    )


def wait_for(
    driver: webdriver.Chrome,
    by: str,
    value: str,
    timeout: int = config.WEBDRIVER_TIMEOUT,
) -> WebElement:
    """Return element after waiting for it to be clickable."""
    return WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((by, value)))


def wait_for_any(
    driver: webdriver.Chrome,
    selectors: tuple[tuple[str, str], ...],
    timeout: int = config.WEBDRIVER_TIMEOUT,
) -> WebElement:
    """Return the first visible element that matches any selector."""
    deadline = time.time() + timeout
    last_error: Exception | None = None

    while time.time() < deadline:
        for by, value in selectors:
            try:
                element = driver.find_element(by, value)
            except NoSuchElementException as exc:
                last_error = exc
                continue

            if element.is_displayed():
                return element
        time.sleep(0.5)

    raise TimeoutException(str(last_error) if last_error else "No matching visible element found.")


def gmail_login(driver: webdriver.Chrome, email: str, password: str) -> str:
    """Perform Google login and return status: success, failed, or needs_totp."""
    try:
        driver.implicitly_wait(0)
        driver.get(config.GMAIL_LOGIN_URL)
        time.sleep(3)

        email_selectors = (
            (By.CSS_SELECTOR, 'input[type="email"]'),
            (By.CSS_SELECTOR, 'input[name="identifier"]'),
            (By.CSS_SELECTOR, 'input[autocomplete="username"]'),
        )

        for retry in range(3):
            try:
                email_field = wait_for_any(driver, email_selectors)
                email_field.clear()
                email_field.send_keys(email)
                break
            except StaleElementReferenceException:
                logger.warning("Stale element on email field, retrying (%d/3)", retry + 1)
                time.sleep(1)
        else:
            raise GoogleAutomationError("Email field stale after 3 retries")

        wait_for(driver, By.ID, "identifierNext").click()
        time.sleep(1)

        password_field = wait_for_any(
            driver,
            (
                (By.CSS_SELECTOR, 'input[type="password"]'),
                (By.CSS_SELECTOR, 'input[name="Passwd"]'),
                (By.CSS_SELECTOR, 'input[autocomplete="current-password"]'),
            ),
        )
        password_field.clear()
        password_field.send_keys(password)
        wait_for(driver, By.ID, "passwordNext").click()
        time.sleep(2)
        return _resolve_post_password_state(driver, email)

    except TimeoutException as exc:
        snapshot = get_login_debug_snapshot(driver)
        logger.error(
            "Timeout during login: %s | url=%s | title=%s | excerpt=%s",
            exc,
            snapshot["url"] or "-",
            snapshot["title"] or "-",
            snapshot["excerpt"] or "-",
        )
        detail = ""
        if snapshot["title"] or snapshot["excerpt"]:
            detail = (
                f" Current page: {snapshot['title'] or '(untitled)'}"
                f" | URL: {snapshot['url'] or '-'}"
            )
        raise GoogleAutomationError(
            "Timed out while loading the Google sign-in page. "
            "This usually points to a proxy/network issue or an unexpected Google page."
            f"{detail}"
        ) from exc
    except WebDriverException as exc:
        logger.error("WebDriver error during login: %s", exc)
        raise GoogleAutomationError(
            f"Browser/network error during login: {exc.__class__.__name__}"
        ) from exc


def submit_totp_code(driver: webdriver.Chrome, code: str) -> bool:
    """Enter TOTP/authenticator code and return True when accepted."""
    try:
        totp_field = None
        for selector in (
            'input[type="tel"]',
            'input[name="totpPin"]',
            '#totpPin',
            'input[type="text"]',
        ):
            try:
                totp_field = WebDriverWait(driver, 2).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )
                if totp_field:
                    break
            except TimeoutException:
                continue

        if not totp_field:
            return False

        totp_field.clear()
        totp_field.send_keys(code)
        time.sleep(0.5)

        for btn_selector in (
            "#totpNext",
            'button[jsname="LgbsSe"]',
            '[data-action="verify"]',
            'button[type="submit"]',
        ):
            try:
                driver.find_element(By.CSS_SELECTOR, btn_selector).click()
                break
            except NoSuchElementException:
                continue

        # Google can take several seconds to validate the authenticator code.
        # Poll a little longer so slow redirects are not mistaken for rejection.
        deadline = time.time() + 15
        while time.time() < deadline:
            current_url = driver.current_url
            if not _is_google_challenge_url(current_url):
                return True
            if _has_totp_error(driver):
                return False
            time.sleep(0.5)

        return not _is_google_challenge_url(driver.current_url)
    except Exception as exc:
        logger.error("Error submitting TOTP code: %s", exc)
        return False
