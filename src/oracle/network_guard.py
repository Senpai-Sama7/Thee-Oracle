from __future__ import annotations

import ipaddress
import os
import socket
from urllib.parse import SplitResult, urlsplit

IPAddress = ipaddress.IPv4Address | ipaddress.IPv6Address

ABSOLUTE_HTTP_URL_ERROR = "Only absolute http(s) URLs are allowed"
PRIVATE_HTTP_HOST_ERROR = "Private, loopback, link-local, localhost, and metadata targets are not allowed"
HTTP_REDIRECT_BLOCKED_ERROR = "Redirect responses are not allowed"
_LOCAL_HOSTS = {"localhost", "localhost.localdomain"}
_METADATA_IPS = {
    ipaddress.ip_address("169.254.169.254"),
    ipaddress.ip_address("100.100.100.200"),
}


def allow_private_http() -> bool:
    return os.environ.get("ORACLE_ALLOW_PRIVATE_HTTP", "").strip().lower() in {"1", "true", "yes", "on"}


def validate_outbound_http_url(url: str, *, allow_private: bool | None = None) -> str | None:
    allowed, error = validate_public_http_url(url, allow_private=allow_private)
    return None if allowed else error


def validate_public_http_url(url: str, *, allow_private: bool | None = None) -> tuple[bool, str]:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or not parsed.hostname:
        return False, ABSOLUTE_HTTP_URL_ERROR

    if allow_private is None:
        allow_private = allow_private_http()
    if allow_private:
        return True, ""

    if _is_local_hostname(parsed.hostname):
        return False, PRIVATE_HTTP_HOST_ERROR

    try:
        addresses = _resolve_host_addresses(parsed)
    except socket.gaierror:
        return False, PRIVATE_HTTP_HOST_ERROR

    if any(_ip_is_blocked(address) for address in addresses):
        return False, PRIVATE_HTTP_HOST_ERROR

    return True, ""


def _is_local_hostname(hostname: str) -> bool:
    normalized = hostname.rstrip(".").lower()
    return normalized in _LOCAL_HOSTS or normalized.endswith(".localhost")


def _resolve_host_addresses(parsed: SplitResult) -> set[IPAddress]:
    hostname = parsed.hostname
    if hostname is None:
        return set()

    try:
        return {ipaddress.ip_address(hostname)}
    except ValueError:
        pass

    addresses: set[IPAddress] = set()
    for entry in socket.getaddrinfo(hostname, parsed.port or None, type=socket.SOCK_STREAM):
        sockaddr = entry[4]
        if not sockaddr:
            continue
        raw_address = sockaddr[0]
        if not isinstance(raw_address, str):
            continue
        addresses.add(ipaddress.ip_address(raw_address.split("%", 1)[0]))
    return addresses


def _ip_is_blocked(address: IPAddress) -> bool:
    if address in _METADATA_IPS:
        return True
    if address.is_loopback or address.is_link_local or address.is_multicast or address.is_reserved:
        return True
    if address.is_private or address.is_unspecified:
        return True
    return False
