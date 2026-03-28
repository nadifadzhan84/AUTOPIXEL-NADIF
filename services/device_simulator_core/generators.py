"""Helpers for generating realistic per-session device identifiers."""

import random
import string

import config


def luhn_checksum(number: str) -> int:
    """Return the Luhn check digit for a numeric string."""
    digits = [int(digit) for digit in number]
    odd_digits = digits[-1::-2]
    even_digits = digits[-2::-2]
    total = sum(odd_digits)
    for digit in even_digits:
        total += sum(divmod(digit * 2, 10))
    return total % 10


def generate_imei() -> str:
    """Generate a syntactically valid IMEI (15 digits, Luhn-valid)."""
    tac = random.choice(["35847631", "35900012", "35250011", "86893003"])
    serial = "".join(random.choices(string.digits, k=15 - len(tac) - 1))
    partial = tac + serial
    check_digit = (10 - luhn_checksum(partial + "0")) % 10
    return partial + str(check_digit)


def generate_android_id() -> str:
    """Generate a 16-character hex Android ID."""
    return "".join(random.choices("0123456789abcdef", k=16))


def generate_device_fingerprint(model: str, build_id: str, android: str) -> str:
    """Return a realistic Android build fingerprint."""
    model_key = model.lower().replace(" ", "_")
    return (
        f"google/{model_key}/{model_key}:{android}/"
        f"{build_id}/eng.{random.randint(10000000, 99999999)}:user/release-keys"
    )


def random_chrome_patch() -> str:
    """Return installed Chrome version with small patch variation."""
    actual = config.CHROME_VERSION
    parts = actual.split(".")
    if len(parts) == 4:
        parts[3] = str(int(parts[3]) + random.randint(-5, 5))
        return ".".join(parts)
    return actual


def random_build_id() -> str:
    """Pick a realistic BUILD_ID from a pool of known Pixel 10 Pro builds."""
    builds = [
        "AP4A.250405.002",
        "AP4A.250305.001",
        "AP4A.250205.004",
        "AP3A.250105.002",
        "AP3A.241205.015",
    ]
    return random.choice(builds)
