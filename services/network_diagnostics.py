"""Small network diagnostics helpers for active proxy inspection."""

from __future__ import annotations

import json
import ssl
import time
from collections.abc import Mapping
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import Request
from urllib.request import HTTPSHandler, ProxyHandler, build_opener

import httpx

from core.proxy_manager import mask_proxy_url, normalize_proxy_url, parse_proxy_parts

IP_API_URL = "https://ipwho.is/"
GOOGLE_SIGNIN_PROBE_URL = "https://accounts.google.com/signin/v2/identifier"


def _build_proxy_handler(proxy_url: str | None) -> ProxyHandler:
    if not proxy_url:
        return ProxyHandler({})

    normalized = normalize_proxy_url(proxy_url)
    parsed = urlsplit(normalized)
    if parsed.scheme.startswith("socks"):
        raise RuntimeError("SOCKS proxy probing is not supported by the current /ip command.")

    return ProxyHandler({
        "http": normalized,
        "https": normalized,
    })


def _normalize_http_proxy(proxy_url: str | None) -> str | None:
    if not proxy_url:
        return None

    normalized = normalize_proxy_url(proxy_url)
    parsed = urlsplit(normalized)
    if parsed.scheme.startswith("socks"):
        raise RuntimeError("SOCKS proxy probing is not supported by the current /ip command.")
    return normalized


def _format_probe_error(prefix: str, exc: Exception) -> RuntimeError:
    message = str(exc)
    lowered = message.lower()
    if "407" in lowered or "proxy authentication required" in lowered:
        return RuntimeError(
            f"{prefix}: Proxy authentication failed (407). "
            "Please rotate the proxy or verify the proxy username/password."
        )
    return RuntimeError(f"{prefix}: {exc}")


def _open_json_with_httpx(url: str, proxy_url: str | None, timeout: int = 15) -> dict:
    normalized_proxy = _normalize_http_proxy(proxy_url)
    with httpx.Client(
        proxy=normalized_proxy,
        timeout=timeout,
        follow_redirects=True,
    ) as client:
        response = client.get(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                )
            },
        )
        if response.status_code == 407:
            raise RuntimeError("407 Proxy Authentication Required")
        response.raise_for_status()
        return response.json()


def _open_json_with_urllib(url: str, proxy_url: str | None, timeout: int = 15) -> dict:
    handler = _build_proxy_handler(proxy_url)
    context = ssl.create_default_context()
    opener = build_opener(handler, HTTPSHandler(context=context))
    with opener.open(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


def _probe_url_with_httpx(
    url: str,
    proxy_url: str | None,
    timeout: int,
    headers: dict[str, str] | None = None,
) -> tuple[int, str, float]:
    normalized_proxy = _normalize_http_proxy(proxy_url)
    started = time.perf_counter()
    with httpx.Client(
        proxy=normalized_proxy,
        timeout=timeout,
        follow_redirects=True,
    ) as client:
        response = client.get(url, headers=headers)
        if response.status_code == 407:
            raise RuntimeError("407 Proxy Authentication Required")
        response.raise_for_status()
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        return response.status_code, str(response.url), latency_ms


def _probe_url_with_urllib(
    url: str,
    proxy_url: str | None,
    timeout: int,
    headers: dict[str, str] | None = None,
) -> tuple[int, str, float]:
    handler = _build_proxy_handler(proxy_url)
    context = ssl.create_default_context()
    opener = build_opener(handler, HTTPSHandler(context=context))
    request = Request(url, headers=headers or {})
    started = time.perf_counter()
    with opener.open(request, timeout=timeout) as response:
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        final_url = response.geturl()
        status_code = getattr(response, "status", None) or response.getcode()
        return int(status_code), final_url, latency_ms


def inspect_connection(proxy_url: str | None) -> dict[str, str]:
    """Return masked proxy info plus public IP and geo summary."""
    try:
        payload = _open_json_with_httpx(IP_API_URL, proxy_url, timeout=15)
    except Exception as exc:
        try:
            payload = _open_json_with_urllib(IP_API_URL, proxy_url, timeout=15)
        except URLError as fallback_exc:
            raise _format_probe_error(
                "Failed to probe public IP",
                fallback_exc.reason if getattr(fallback_exc, "reason", None) else fallback_exc,
            ) from fallback_exc
        except Exception as fallback_exc:
            raise _format_probe_error("Failed to probe public IP", fallback_exc) from fallback_exc

    if payload.get("success") is False:
        raise RuntimeError("The IP geo service returned an unsuccessful response.")

    ip_address = str(payload.get("ip") or payload.get("query") or "-")
    country = str(payload.get("country") or "-")
    country_code = str(payload.get("country_code") or payload.get("countryCode") or "-")
    continent = str(payload.get("continent") or "-")
    region = str(payload.get("region") or payload.get("regionName") or "-")
    city = str(payload.get("city") or "-")
    postal = str(payload.get("postal") or "-")
    latitude = str(payload.get("latitude") or "-")
    longitude = str(payload.get("longitude") or "-")
    connection = payload.get("connection", {}) or {}
    timezone = payload.get("timezone", {}) or {}
    isp = str(connection.get("isp") or payload.get("isp") or "-")
    org = str(connection.get("org") or "-")
    asn = str(connection.get("asn") or "-")
    domain = str(connection.get("domain") or "-")
    timezone_id = str(timezone.get("id") or "-")
    timezone_utc = str(timezone.get("utc") or "-")
    timezone_abbr = str(timezone.get("abbr") or "-")

    result = {
        "proxy": mask_proxy_url(proxy_url),
        "ip": ip_address,
        "continent": continent,
        "country": country,
        "country_code": country_code,
        "region": region,
        "city": city,
        "postal": postal,
        "latitude": latitude,
        "longitude": longitude,
        "org": org,
        "isp": isp,
        "asn": asn,
        "domain": domain,
        "timezone": timezone_id,
        "timezone_utc": timezone_utc,
        "timezone_abbr": timezone_abbr,
    }

    proxy_parts = parse_proxy_parts(proxy_url) if proxy_url else None
    if proxy_parts:
        result["proxy_host"] = f"{proxy_parts['host']}:{proxy_parts['port']}"

    return result


def format_connection_identity(
    result: Mapping[str, str],
    title: str = "🌍 Connection Identity",
) -> str:
    """Return a readable multi-line connection/proxy summary."""
    lines = [
        title,
        f"🌐 Proxy: {result.get('proxy', '-')}",
    ]

    proxy_host = result.get("proxy_host")
    if proxy_host:
        lines.append(f"🔌 Proxy host: {proxy_host}")

    lines.extend(
        [
            f"🧷 Public IP: {result.get('ip', '-')}",
            f"🏳️ Country: {result.get('country', '-')} ({result.get('country_code', '-')})",
            f"🗺️ Continent: {result.get('continent', '-')}",
            f"📍 Region: {result.get('region', '-')}",
            f"🏙️ City: {result.get('city', '-')}",
        ]
    )

    postal = result.get("postal")
    if postal and postal != "-":
        lines.append(f"📮 ZIP: {postal}")

    timezone_id = result.get("timezone", "-")
    timezone_utc = result.get("timezone_utc", "-")
    timezone_abbr = result.get("timezone_abbr", "-")
    timezone_bits = [part for part in (timezone_id, timezone_abbr, timezone_utc) if part and part != "-"]
    if timezone_bits:
        lines.append(f"🕒 Timezone: {' | '.join(timezone_bits)}")

    latitude = result.get("latitude", "-")
    longitude = result.get("longitude", "-")
    if latitude != "-" and longitude != "-":
        lines.append(f"🧭 Coordinates: {latitude}, {longitude}")

    org = result.get("org")
    if org and org != "-":
        lines.append(f"🏢 Brand/Org: {org}")

    isp = result.get("isp")
    if isp and isp != "-" and isp != org:
        lines.append(f"🛰️ ISP: {isp}")

    asn = result.get("asn")
    if asn and asn != "-":
        lines.append(f"🔢 ASN: {asn}")

    domain = result.get("domain")
    if domain and domain != "-":
        lines.append(f"🌐 Domain: {domain}")

    return "\n".join(lines)


def probe_google_signin(
    proxy_url: str | None,
    timeout: int = 12,
) -> dict[str, str | float | int]:
    """Return a quick reachability check for the Google sign-in page."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    }
    try:
        status_code, final_url, latency_ms = _probe_url_with_httpx(
            GOOGLE_SIGNIN_PROBE_URL,
            proxy_url,
            timeout,
            headers=headers,
        )
    except Exception as exc:
        try:
            status_code, final_url, latency_ms = _probe_url_with_urllib(
                GOOGLE_SIGNIN_PROBE_URL,
                proxy_url,
                timeout,
                headers=headers,
            )
        except URLError as fallback_exc:
            raise _format_probe_error(
                "Failed to reach Google sign-in",
                fallback_exc.reason if getattr(fallback_exc, "reason", None) else fallback_exc,
            ) from fallback_exc
        except Exception as fallback_exc:
            raise _format_probe_error("Failed to reach Google sign-in", fallback_exc) from fallback_exc

    hostname = (urlsplit(final_url).hostname or "").lower()
    if not (hostname == "accounts.google.com" or hostname.endswith(".google.com")):
        raise RuntimeError(
            f"Unexpected response while probing Google sign-in: {hostname or final_url}"
        )

    return {
        "proxy": mask_proxy_url(proxy_url),
        "status_code": int(status_code),
        "final_url": final_url,
        "latency_ms": latency_ms,
    }
