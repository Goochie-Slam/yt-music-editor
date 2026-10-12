from app.models.export_schema import SCHEMA_FILE, render
from app.models.project import Project


def test_committed_schema_is_up_to_date() -> None:
    """If this fails, regenerate:

    uv run python -m app.models.export_schema && cd ../frontend && npm run gen:types
    """
    assert SCHEMA_FILE.read_text(encoding="utf-8") == render()


def test_default_project_serialises_with_camel_case_and_format_keys() -> None:
    data = Project(name="x").model_dump(mode="json")
    assert "schemaVersion" in data and "createdAt" in data
    viz = next(e for e in data["video"]["elements"] if e["kind"] == "visualizer")
    assert viz["pos"] == {"16:9": {"x": 0.83, "y": 0.5}, "9:16": {"x": 0.5, "y": 0.68}}
    assert Project.model_validate(data) == Project.model_validate(data)
