from __future__ import annotations

import secrets
import string
from datetime import UTC, datetime

_ALPHABET = string.ascii_letters + string.digits


def new_id(length: int = 10) -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(length))


def utcnow() -> datetime:
    return datetime.now(UTC)
