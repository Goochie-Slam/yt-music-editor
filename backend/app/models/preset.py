from __future__ import annotations

from typing import Annotated

from pydantic import Field

from app.audio.curves import Curve
from app.models.project import Model


class TransitionParams(Model):
    fade_out: Annotated[float, Field(ge=0, le=20)]
    fade_in: Annotated[float, Field(ge=0, le=20)]
    overlap: Annotated[float, Field(ge=-5, le=20)]
    curve_out: Curve
    curve_in: Curve


class TransitionPresetIn(TransitionParams):
    name: Annotated[str, Field(min_length=1, max_length=60)]
    hint: str = ""


class TransitionPreset(TransitionPresetIn):
    id: str
    builtin: bool = False
