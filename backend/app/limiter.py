"""
Shared slowapi limiter configuration and client IP resolution.
"""
import ipaddress
from fastapi import Request
from slowapi import Limiter
from app.config import get_settings


def get_real_client_ip(request: Request) -> str:
    """Extract the client IP for rate limiting and session tracking."""
    settings = get_settings()

    def parse_ip(value: str | None) -> str | None:
        if not value:
            return None
        candidate = value.split(",", 1)[0].strip()
        if not candidate:
            return None
        if ":" in candidate and not candidate.startswith("[") and candidate.count(":") == 1:
            candidate = candidate.split(":")[0].strip()
        try:
            return str(ipaddress.ip_address(candidate))
        except ValueError:
            return None

    if settings.trust_proxy_headers:
        # Prefer X-Real-IP set explicitly by reverse proxy
        real_ip = parse_ip(request.headers.get("x-real-ip"))
        if real_ip:
            return real_ip
        forwarded_ip = parse_ip(request.headers.get("x-forwarded-for"))
        if forwarded_ip:
            return forwarded_ip

    direct_ip = parse_ip(request.client.host) if request.client and request.client.host else None
    if direct_ip:
        return direct_ip
    return "127.0.0.1"


limiter = Limiter(
    key_func=get_real_client_ip,
    default_limits=["100/minute"],
)
