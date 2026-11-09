"""通用工具：请求 ID、日志脱敏等。"""

from __future__ import annotations

import uuid


def new_request_id() -> str:
    return uuid.uuid4().hex[:16]


def mask_email(email: str) -> str:
    if "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        visible = local[0] + "*"
    else:
        visible = local[0] + "***" + local[-1]
    return f"{visible}@{domain}"


def mask_phone(phone: str) -> str:
    if len(phone) <= 4:
        return "***"
    return phone[:3] + "****" + phone[-4:]


def mask_ip(ip: str) -> str:
    parts = ip.split(".")
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.*.*"
    return "***"