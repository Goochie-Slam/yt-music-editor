"""Upgrade raw project.json dicts to the current schema before validation.

Every incompatible change to models/project.py bumps SCHEMA_VERSION and adds one step here,
so projects saved by older versions keep opening (docs/CODING-GUIDE.md §5.2).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.core.errors import AppError
from app.models.project import SCHEMA_VERSION

Raw = dict[str, Any]

# STEPS[n] upgrades a version-n document to version n + 1.
STEPS: dict[int, Callable[[Raw], Raw]] = {}


def migrate(raw: Raw) -> Raw:
    version = raw.get("schemaVersion", 1)
    if not isinstance(version, int) or version < 1:
        raise AppError(422, "project_corrupt", f"bad schemaVersion {version!r}")
    if version > SCHEMA_VERSION:
        raise AppError(422, "project_too_new", f"schemaVersion {version} > {SCHEMA_VERSION}")
    while version < SCHEMA_VERSION:
        raw = STEPS[version](raw)
        version += 1
        raw["schemaVersion"] = version
    return raw
