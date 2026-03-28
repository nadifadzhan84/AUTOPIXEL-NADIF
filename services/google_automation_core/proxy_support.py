"""Helpers for applying authenticated proxies to Chrome WebDriver."""

from __future__ import annotations

import base64
import io
import json
import zipfile

from core.proxy_manager import parse_proxy_parts


def proxy_server_argument(proxy_url: str) -> str:
    """Return a Chrome --proxy-server value without credentials."""
    proxy = parse_proxy_parts(proxy_url)
    return f"{proxy['scheme']}://{proxy['host']}:{proxy['port']}"


def build_proxy_auth_extension(proxy_url: str) -> str | None:
    """Return a base64-encoded Chrome extension for proxy authentication."""
    proxy = parse_proxy_parts(proxy_url)
    username = proxy["username"]
    password = proxy["password"]

    if not username:
        return None

    manifest = {
        "version": "1.0.0",
        "manifest_version": 2,
        "name": "AutoPixel Proxy Auth",
        "permissions": [
            "proxy",
            "storage",
            "tabs",
            "webRequest",
            "webRequestBlocking",
            "<all_urls>",
        ],
        "background": {
            "scripts": ["background.js"],
        },
        "minimum_chrome_version": "88.0.0",
    }

    background = f"""
const config = {{
  mode: "fixed_servers",
  rules: {{
    singleProxy: {{
      scheme: "{proxy['scheme']}",
      host: "{proxy['host']}",
      port: parseInt("{proxy['port']}", 10)
    }},
    bypassList: ["localhost", "127.0.0.1"]
  }}
}};

chrome.proxy.settings.set({{ value: config, scope: "regular" }}, function() {{}});

chrome.webRequest.onAuthRequired.addListener(
  function() {{
    return {{
      authCredentials: {{
        username: {json.dumps(username)},
        password: {json.dumps(password or "")}
      }}
    }};
  }},
  {{ urls: ["<all_urls>"] }},
  ["blocking"]
);
""".strip()

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest))
        archive.writestr("background.js", background)

    return base64.b64encode(buffer.getvalue()).decode("ascii")
