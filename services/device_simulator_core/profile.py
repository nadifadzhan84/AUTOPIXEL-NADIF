"""Device profile model and browser spoof payloads."""

import random
import uuid
from dataclasses import dataclass, field

import config
from services.device_simulator_core.constants import PIXEL_10_PRO_SPECS


@dataclass
class DeviceProfile:
    imei: str
    android_id: str
    device_fingerprint: str
    user_agent: str
    chrome_version: str
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    model: str = config.DEVICE_MODEL
    brand: str = config.DEVICE_BRAND
    manufacturer: str = config.DEVICE_MANUFACTURER
    android_version: str = config.ANDROID_VERSION
    android_sdk: str = config.ANDROID_SDK
    build_id: str = config.BUILD_ID
    accept_language: str = "en-US,en;q=0.9"
    locale: str = "en-US"

    def client_hints_headers(self) -> dict:
        """Return User-Agent Client Hints headers for this device."""
        return {
            "Sec-CH-UA": (
                f'"Chromium";v="{config.CHROME_MAJOR_VERSION}", '
                f'"Google Chrome";v="{config.CHROME_MAJOR_VERSION}", '
                f'"Not:A-Brand";v="24"'
            ),
            "Sec-CH-UA-Mobile": "?1",
            "Sec-CH-UA-Platform": '"Android"',
            "Sec-CH-UA-Platform-Version": f'"{self.android_version}.0.0"',
            "Sec-CH-UA-Model": f'"{self.model}"',
            "Sec-CH-UA-Full-Version": f'"{self.chrome_version}"',
            "Sec-CH-UA-Full-Version-List": (
                f'"Chromium";v="{self.chrome_version}", '
                f'"Google Chrome";v="{self.chrome_version}", '
                f'"Not:A-Brand";v="24.0.0.0"'
            ),
            "Sec-CH-UA-Arch": '""',
            "Sec-CH-UA-Bitness": '"64"',
        }

    def as_headers(self) -> dict:
        """Return HTTP headers that identify this device."""
        headers = {
            "User-Agent": self.user_agent,
            "Accept-Language": self.accept_language,
            "Accept-Encoding": "gzip, deflate, br",
        }
        headers.update(self.client_hints_headers())
        return headers

    def navigator_overrides_js(self) -> str:
        """Return JavaScript to inject navigator/screen spoofs via CDP."""
        specs = PIXEL_10_PRO_SPECS
        return f"""
        Object.defineProperty(navigator, 'platform', {{ get: () => '{specs["platform"]}' }});
        Object.defineProperty(navigator, 'vendor', {{ get: () => '{specs["vendor"]}' }});
        Object.defineProperty(navigator, 'maxTouchPoints', {{ get: () => {specs["max_touch_points"]} }});
        Object.defineProperty(navigator, 'hardwareConcurrency', {{ get: () => {specs["hardware_concurrency"]} }});
        Object.defineProperty(navigator, 'deviceMemory', {{ get: () => {specs["device_memory"]} }});
        Object.defineProperty(navigator, 'language', {{ get: () => '{self.locale}' }});
        Object.defineProperty(navigator, 'languages', {{ get: () => ['{self.locale}', 'en'] }});

        Object.defineProperty(navigator, 'userAgentData', {{
            get: () => ({{
                brands: [
                    {{ brand: "Chromium", version: "{config.CHROME_MAJOR_VERSION}" }},
                    {{ brand: "Google Chrome", version: "{config.CHROME_MAJOR_VERSION}" }},
                    {{ brand: "Not:A-Brand", version: "24" }},
                ],
                mobile: true,
                platform: "Android",
                getHighEntropyValues: () => Promise.resolve({{
                    brands: [
                        {{ brand: "Chromium", version: "{config.CHROME_MAJOR_VERSION}" }},
                        {{ brand: "Google Chrome", version: "{config.CHROME_MAJOR_VERSION}" }},
                        {{ brand: "Not:A-Brand", version: "24" }},
                    ],
                    mobile: true,
                    platform: "Android",
                    platformVersion: "{self.android_version}.0.0",
                    architecture: "",
                    bitness: "64",
                    model: "{self.model}",
                    uaFullVersion: "{self.chrome_version}",
                    fullVersionList: [
                        {{ brand: "Chromium", version: "{self.chrome_version}" }},
                        {{ brand: "Google Chrome", version: "{self.chrome_version}" }},
                        {{ brand: "Not:A-Brand", version: "24.0.0.0" }},
                    ],
                }}),
            }})
        }});

        Object.defineProperty(screen, 'orientation', {{
            get: () => ({{
                type: 'portrait-primary',
                angle: 0,
                addEventListener: () => {{}},
                removeEventListener: () => {{}},
                dispatchEvent: () => true,
                onchange: null,
                lock: () => Promise.resolve(),
                unlock: () => {{}},
            }})
        }});

        navigator.vibrate = () => true;
        if (navigator.connection) {{
            Object.defineProperty(navigator.connection, 'effectiveType', {{ get: () => '{specs["effective_type"]}' }});
            Object.defineProperty(navigator.connection, 'type', {{ get: () => 'cellular' }});
            Object.defineProperty(navigator.connection, 'downlink', {{ get: () => {specs["downlink"]} }});
        }}

        Object.defineProperty(screen, 'width', {{ get: () => {specs["device_width"]} }});
        Object.defineProperty(screen, 'height', {{ get: () => {specs["device_height"]} }});
        Object.defineProperty(screen, 'availWidth', {{ get: () => {specs["device_width"]} }});
        Object.defineProperty(screen, 'availHeight', {{ get: () => {specs["device_height"]} }});
        Object.defineProperty(screen, 'colorDepth', {{ get: () => 24 }});

        const getParameterOrig = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(param) {{
            if (param === 0x9245) return '{specs["webgl_vendor"]}';
            if (param === 0x9246) return '{specs["webgl_renderer"]}';
            return getParameterOrig.call(this, param);
        }};

        Object.defineProperty(navigator, 'webdriver', {{ get: () => undefined }});

        const origToDataURL = HTMLCanvasElement.prototype.toDataURL;
        HTMLCanvasElement.prototype.toDataURL = function(type) {{
            const ctx = this.getContext('2d');
            if (ctx) {{
                const style = ctx.fillStyle;
                ctx.fillStyle = 'rgba(0,0,{random.randint(1,3)},0.01)';
                ctx.fillRect(0, 0, 1, 1);
                ctx.fillStyle = style;
            }}
            return origToDataURL.apply(this, arguments);
        }};
        """

    def summary(self) -> str:
        """Human-readable summary for Telegram messages."""
        return (
            f"📱 <b>Device Profile</b>\n"
            f"Model: {self.model}\n"
            f"Android: {self.android_version}\n"
            f"Build: {self.build_id}\n"
            f"Chrome: {self.chrome_version}\n"
            f"Session: <code>{self.session_id[:8]}…</code>"
        )
