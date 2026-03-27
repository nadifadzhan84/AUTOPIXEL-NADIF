"""Google One offer discovery helpers."""

import logging
import time
from typing import Optional

from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.by import By

import config

logger = logging.getLogger(__name__)


def is_correct_offer_url(url: str) -> bool:
    """Return True for expected Pixel Gemini offer claim URL pattern."""
    return bool(url) and "partner-eft-onboard" in url


def extract_payment_link(driver: webdriver.Chrome) -> Optional[str]:
    """Scan current page for Gemini Pro offer activation link."""
    all_links = driver.find_elements(By.TAG_NAME, "a")

    for link in all_links:
        try:
            href = link.get_attribute("href") or ""
            if "LOCKED" in href and "BARD_ADVANCED" in href:
                old_url = driver.current_url
                driver.execute_script("arguments[0].click();", link)
                time.sleep(5)
                current_url = driver.current_url

                if is_correct_offer_url(current_url):
                    return current_url
                if "LOCKED" in current_url:
                    return None

                if current_url != old_url:
                    new_links = driver.find_elements(By.TAG_NAME, "a")
                    for new_link in new_links:
                        try:
                            next_href = new_link.get_attribute("href") or ""
                            if is_correct_offer_url(next_href):
                                return next_href
                        except Exception:
                            continue

                    if is_correct_offer_url(current_url):
                        return current_url

                return None
        except Exception as exc:
            logger.warning("Error clicking LOCKED link: %s", exc)
            return None

    for link in all_links:
        try:
            href = link.get_attribute("href") or ""
            if is_correct_offer_url(href):
                return href
        except Exception:
            continue

    keywords = config.GEMINI_OFFER_KEYWORDS
    for link in all_links:
        try:
            text = (link.text + " " + (link.get_attribute("aria-label") or "")).lower()
            href = link.get_attribute("href") or ""
            if "LOCKED" in href:
                continue
            if any(keyword in text for keyword in keywords) and is_correct_offer_url(href):
                return href
        except Exception:
            continue

    for link in all_links:
        try:
            href = link.get_attribute("href") or ""
            if is_correct_offer_url(href):
                return href
        except Exception:
            continue

    return None


def navigate_google_one(driver: webdriver.Chrome) -> Optional[str]:
    """Navigate Google One pages and attempt to find the offer link."""
    for url in (config.GOOGLE_ONE_URL, config.GOOGLE_ONE_OFFERS_URL):
        try:
            logger.info("Navigating to %s", url)
            driver.get(url)
            time.sleep(3)

            for selector in (
                '[aria-label="Accept all"]',
                'button[jsname="higCR"]',
                '[data-action="accept"]',
            ):
                try:
                    driver.find_element(By.CSS_SELECTOR, selector).click()
                    time.sleep(1)
                    break
                except NoSuchElementException:
                    continue

            link = extract_payment_link(driver)
            if link:
                return link
        except (TimeoutException, WebDriverException) as exc:
            logger.warning("Error accessing %s: %s", url, exc)

    return None
