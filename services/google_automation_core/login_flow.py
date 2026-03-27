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


def wait_for(
    driver: webdriver.Chrome,
    by: str,
    value: str,
    timeout: int = config.WEBDRIVER_TIMEOUT,
) -> WebElement:
    """Return element after waiting for it to be clickable."""
    return WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((by, value)))


def gmail_login(driver: webdriver.Chrome, email: str, password: str) -> str:
    """Perform Google login and return status: success, failed, or needs_totp."""
    try:
        driver.implicitly_wait(0)
        driver.get(config.GMAIL_LOGIN_URL)
        time.sleep(3)

        for retry in range(3):
            try:
                email_field = wait_for(driver, By.CSS_SELECTOR, 'input[type="email"]')
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

        password_field = wait_for(driver, By.CSS_SELECTOR, 'input[type="password"]')
        password_field.clear()
        password_field.send_keys(password)
        wait_for(driver, By.ID, "passwordNext").click()
        time.sleep(2)

        current_url = driver.current_url
        parsed = urlparse(current_url)
        hostname = parsed.hostname or ""
        path = parsed.path or ""

        challenge_paths = ("/signin/v2/challenge", "/signin/challenge", "/v2/challenge")
        if hostname == "accounts.google.com" and any(p in path for p in challenge_paths):
            totp_selectors = ('input[type="tel"]', 'input[name="totpPin"]', '#totpPin')
            for selector in totp_selectors:
                try:
                    driver.find_element(By.CSS_SELECTOR, selector)
                    logger.info("TOTP 2FA input field found for %s - awaiting code", email)
                    return "needs_totp"
                except NoSuchElementException:
                    continue

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

                if switched_to_totp:
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

            raise GoogleAutomationError(
                f"Your account requires {challenge_type}. "
                f"No authenticator option found. "
                f"Please use an App Password instead."
            )

        if hostname == "myaccount.google.com" or (hostname.endswith(".google.com") and "/u/" in path):
            return "success"

        try:
            error_el = driver.find_element(
                By.CSS_SELECTOR, '[jsname="B34EJ"], [aria-live="assertive"]'
            )
            if error_el.text:
                return "failed"
        except NoSuchElementException:
            pass

        if not (hostname == "accounts.google.com" and path.startswith("/signin")):
            return "success"

        return "failed"

    except TimeoutException as exc:
        logger.error("Timeout during login: %s", exc)
        return "failed"
    except WebDriverException as exc:
        logger.error("WebDriver error during login: %s", exc)
        return "failed"


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

        time.sleep(2)

        current_url = driver.current_url
        parsed = urlparse(current_url)
        hostname = parsed.hostname or ""
        path = parsed.path or ""
        if hostname == "accounts.google.com" and "challenge" in path:
            return False

        return True
    except Exception as exc:
        logger.error("Error submitting TOTP code: %s", exc)
        return False
