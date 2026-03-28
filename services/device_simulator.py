"""Public facade for Android device simulation service."""

from services.device_simulator_core.constants import PIXEL_10_PRO_SPECS
from services.device_simulator_core.factory import create_device_profile
from services.device_simulator_core.profile import DeviceProfile

__all__ = ["DeviceProfile", "PIXEL_10_PRO_SPECS", "create_device_profile"]
