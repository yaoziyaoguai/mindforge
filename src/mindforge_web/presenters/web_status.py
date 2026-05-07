"""Small status mapping helpers for Web schemas."""

from __future__ import annotations

from mindforge_web.schemas import StatusLevel


def bool_status(value: bool, *, missing_is: StatusLevel = "warn") -> StatusLevel:
    return "ok" if value else missing_is
