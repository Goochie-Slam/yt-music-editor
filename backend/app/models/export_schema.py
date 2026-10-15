"""Write shared/schema/project.schema.json (consumed by `npm run gen:types`). Never edit by hand."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.core.config import REPO_DIR
from app.models.project import Project, ProjectSummary

SCHEMA_FILE = REPO_DIR / "shared" / "schema" / "project.schema.json"


def _strip_field_titles(node: Any) -> None:
    """Pydantic titles every field; json2ts would turn each into its own type alias."""
    if isinstance(node, dict):
        for prop in node.get("properties", {}).values():
            prop.pop("title", None)
        for value in node.values():
            _strip_field_titles(value)
    elif isinstance(node, list):
        for item in node:
            _strip_field_titles(item)


def build_schema() -> dict[str, Any]:
    schema = Project.model_json_schema(by_alias=True, mode="serialization")
    summary = ProjectSummary.model_json_schema(by_alias=True, mode="serialization")
    schema.setdefault("$defs", {})["ProjectSummary"] = summary
    _strip_field_titles(schema)
    return schema


def render() -> str:
    return json.dumps(build_schema(), indent=2, ensure_ascii=False) + "\n"


def main(path: Path = SCHEMA_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render(), encoding="utf-8", newline="\n")  # same bytes on Windows
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
