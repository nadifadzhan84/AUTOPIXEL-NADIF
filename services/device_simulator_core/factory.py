"""Factory for creating per-session device profiles."""

import random

import config
from services.device_simulator_core.generators import (
    generate_android_id,
    generate_device_fingerprint,
    generate_imei,
    random_build_id,
    random_chrome_patch,
)
from services.device_simulator_core.profile import DeviceProfile


def create_device_profile() -> DeviceProfile:
    """Create a fresh Pixel 10 Pro device profile with unique identifiers."""
    build_id = random_build_id()
    chrome_version = random_chrome_patch()
    template = random.choice(config.USER_AGENT_TEMPLATES)
    user_agent = template.format(
        android=config.ANDROID_VERSION,
        model=config.DEVICE_MODEL,
        build=build_id,
        chrome=chrome_version,
    )
    fingerprint = generate_device_fingerprint(
        config.DEVICE_MODEL,
        build_id,
        config.ANDROID_VERSION,
    )
    return DeviceProfile(
        imei=generate_imei(),
        android_id=generate_android_id(),
        device_fingerprint=fingerprint,
        user_agent=user_agent,
        chrome_version=chrome_version,
        build_id=build_id,
    )
