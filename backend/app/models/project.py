"""project.json — the single source of truth for the data model (docs/CODING-GUIDE.md §5).

shared/schema/project.schema.json and the frontend TypeScript types are GENERATED from this file:
    uv run python -m app.models.export_schema && (cd ../frontend && npm run gen:types)

Units: seconds (float) · positions 0-1 per aspect ratio · sizes in px at a 1080p reference ·
colours "#rrggbb" · loudness LUFS / dB.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from pydantic.alias_generators import to_camel

from app.audio.curves import Curve
from app.core.util import new_id, utcnow

SCHEMA_VERSION: Literal[1] = 1

Color = Annotated[str, StringConstraints(pattern=r"^#[0-9a-fA-F]{6}$")]
Unit = Annotated[float, Field(ge=0, le=1)]
Percent = Annotated[float, Field(ge=0, le=100)]
Seconds = Annotated[float, Field(ge=0)]
AspectRatio = Literal["16:9", "9:16"]


class Model(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
        serialize_by_alias=True,
        json_schema_serialization_defaults_required=True,  # server always sends every field
        validate_assignment=True,
    )


# --------------------------------------------------------------------------- library


class FileSource(Model):
    kind: Literal["file"] = "file"
    path: str


class UrlSource(Model):
    kind: Literal["url"] = "url"
    url: str
    site: str = ""  # youtube / soundcloud / mixcloud / … as reported by yt-dlp


class SegmentSource(Model):
    """A piece cut from another library item by the tracklist splitter (F1.5)."""

    kind: Literal["segment"] = "segment"
    parent_id: str
    start: Seconds
    end: Seconds


Source = Annotated[FileSource | UrlSource | SegmentSource, Field(discriminator="kind")]


class Loudness(Model):
    integrated: float  # LUFS
    true_peak: float  # dBTP
    lra: float


class LibraryItem(Model):
    id: str = Field(default_factory=new_id)
    title: str
    source: Source
    cache_wav: str | None = None  # relative to the project folder; lossless (F1.11)
    duration: Seconds | None = None
    src_bitrate_kbps: int | None = None
    loudness: Loudness | None = None


# --------------------------------------------------------------------------- mix


class Transition(Model):
    preset_id: str | None = "smooth-blend"
    fade_out: Annotated[float, Field(ge=0, le=20)] = 6
    fade_in: Annotated[float, Field(ge=0, le=20)] = 6
    overlap: Annotated[float, Field(ge=-5, le=20)] = 6  # < 0 = silent gap
    curve_out: Curve = Curve.EQUAL_POWER
    curve_in: Curve = Curve.EQUAL_POWER
    edited: bool = False


class MixTrack(Model):
    id: str = Field(default_factory=new_id)
    lib_id: str
    title: str  # display name; never written to file tags
    trim_in: Seconds = 0
    trim_out: Seconds | None = None  # None = end of file
    gain_db: Annotated[float, Field(ge=-6, le=6)] = 0


class Mix(Model):
    target_lufs: Literal[-16, -14, -12] = -14
    auto_trim_silence: bool = True
    fade_in_start: Seconds = 2
    fade_out_end: Seconds = 5
    tracks: list[MixTrack] = Field(default_factory=list)
    # key "<trackIdA>><trackIdB>": a transition follows its pair of tracks when reordering
    transitions: dict[str, Transition] = Field(default_factory=dict)


# --------------------------------------------------------------------------- video


class Pos(Model):
    x: Unit = 0.5
    y: Unit = 0.5


class PosByFormat(Model):
    """Element positions are stored separately per aspect ratio (F3.49)."""

    landscape: Pos = Field(default_factory=Pos, alias="16:9")
    portrait: Pos = Field(default_factory=Pos, alias="9:16")


def _pos(lx: float, ly: float, px: float, py: float) -> PosByFormat:
    return PosByFormat.model_validate({"16:9": {"x": lx, "y": ly}, "9:16": {"x": px, "y": py}})


class Background(Model):
    fit: Literal["blur", "solid", "crop"] = "blur"
    blur: Annotated[float, Field(ge=0, le=60)] = 30
    dim: Annotated[float, Field(ge=0, le=80)] = 35
    solid: Color = "#14121c"


class Artwork(Model):
    type: Literal["image", "carousel", "video"] = "image"
    media: list[str] = Field(default_factory=list)  # relative paths inside the project folder
    carousel_mode: Literal["song", "interval"] = "song"
    carousel_every_sec: Annotated[float, Field(ge=5)] = 60
    loop_crossfade: bool = True
    scale: Annotated[float, Field(ge=40, le=150)] = 100
    radius: Annotated[float, Field(ge=0, le=60)] = 0
    shadow: bool = True
    border: bool = False
    pos: PosByFormat = Field(default_factory=lambda: _pos(0.5, 0.5, 0.5, 0.4))


class EffectSetting(Model):
    on: bool = False
    value: float = 0  # meaning depends on the effect: period (s), opacity (%), density …


class Effects(Model):
    zoom: EffectSetting = Field(default_factory=lambda: EffectSetting(on=True, value=60))
    grain: EffectSetting = Field(default_factory=lambda: EffectSetting(on=True, value=18))
    glow: EffectSetting = Field(default_factory=lambda: EffectSetting(value=40))
    dust: EffectSetting = Field(default_factory=lambda: EffectSetting(on=True, value=40))
    snow: EffectSetting = Field(default_factory=lambda: EffectSetting(value=40))
    bokeh: EffectSetting = Field(default_factory=lambda: EffectSetting(value=20))


Font = Literal["Be Vietnam Pro", "Inter", "Playfair Display", "Montserrat", "Lora", "Quicksand"]


class ElementBase(Model):
    id: str = Field(default_factory=new_id)
    name: str
    visible: bool = True


class Timed(Model):
    start: Seconds = 0
    end: Seconds | None = None  # None = until the end of the video


class TextElement(ElementBase, Timed):
    kind: Literal["text"] = "text"
    text: str
    font: Font = "Be Vietnam Pro"
    weight: Literal[400, 500, 600, 700, 800] = 600
    size: Annotated[float, Field(ge=8, le=200)] = 40
    color: Color = "#ffffff"
    shadow: bool = True
    anim: Literal["fade", "none"] = "fade"
    pos: PosByFormat = Field(default_factory=lambda: _pos(0.35, 0.45, 0.2, 0.5))


class NowPlayingElement(ElementBase):
    kind: Literal["nowPlaying"] = "nowPlaying"
    fmt: Literal["{title}", "{index}. {title}", "Now Playing — {title}"] = "{index}. {title}"
    label: bool = True
    font: Font = "Be Vietnam Pro"
    size: Annotated[float, Field(ge=8, le=200)] = 54
    color: Color = "#ffffff"
    anim: Literal["fade", "slide", "none"] = "fade"
    pos: PosByFormat = Field(default_factory=lambda: _pos(0.05, 0.80, 0.07, 0.82))


class ImageElement(ElementBase, Timed):
    kind: Literal["image"] = "image"
    file: str
    size: Annotated[float, Field(ge=3, le=40)] = 9
    opacity: Percent = 80
    pos: PosByFormat = Field(default_factory=lambda: _pos(0.94, 0.09, 0.88, 0.05))


Blend = Literal["normal", "screen", "add", "overlay", "multiply", "softlight"]


class OverlayElement(ElementBase, Timed):
    kind: Literal["overlay"] = "overlay"
    sub: Literal["video", "image", "color"]
    file: str | None = None  # for video / image
    mode: Literal["solid", "gradient", "vignette"] = "gradient"  # for color
    direction: Literal["bottom", "top", "left", "right"] = "bottom"
    color: Color = "#000000"
    blend: Blend = "screen"
    opacity: Percent = 50
    loop_crossfade: bool = True


class VisualizerElement(ElementBase):
    kind: Literal["visualizer"] = "visualizer"
    type: Literal["bars", "wave", "circular"] = "circular"
    style: Literal[0, 1, 2] = 0
    color1: Color = "#ffffff"
    color2: Color = "#22d3ee"
    size: Annotated[float, Field(ge=10, le=60)] = 26
    sensitivity: Annotated[float, Field(ge=20, le=200)] = 100
    opacity: Percent = 85
    pos: PosByFormat = Field(default_factory=lambda: _pos(0.83, 0.5, 0.5, 0.68))


Element = Annotated[
    TextElement | NowPlayingElement | ImageElement | OverlayElement | VisualizerElement,
    Field(discriminator="kind"),
]


def default_elements() -> list[Element]:
    """Order = stacking order within each group (first is on top)."""
    return [
        NowPlayingElement(name="Now Playing"),
        TextElement(
            name="Tên playlist",
            text="",
            size=64,
            weight=700,
            font="Playfair Display",
            pos=_pos(0.05, 0.07, 0.07, 0.06),
        ),
        VisualizerElement(name="Visualizer"),
    ]


class Video(Model):
    format: AspectRatio = "16:9"
    background: Background = Field(default_factory=Background)
    artwork: Artwork = Field(default_factory=Artwork)
    effects: Effects = Field(default_factory=Effects)
    elements: list[Element] = Field(default_factory=default_elements)


# --------------------------------------------------------------------------- export


class ExportExtras(Model):
    mix_mp3: bool = True
    chapters: bool = False


class ExportSettings(Model):
    formats: list[AspectRatio] = Field(default_factory=lambda: ["16:9"])  # type: ignore[arg-type]
    height: Literal[1080, 1440, 2160] = 1080
    fps: Literal[30, 60] = 30
    quality: Literal["light", "balanced", "high"] = "balanced"
    encoder: Literal["auto", "nvenc", "x264"] = "auto"
    extras: ExportExtras = Field(default_factory=ExportExtras)


# --------------------------------------------------------------------------- project


class Project(Model):
    schema_version: Literal[1] = SCHEMA_VERSION
    id: str = Field(default_factory=new_id)
    name: str
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    library: list[LibraryItem] = Field(default_factory=list)
    mix: Mix = Field(default_factory=Mix)
    video: Video = Field(default_factory=Video)
    export: ExportSettings = Field(default_factory=ExportSettings)


class ProjectSummary(Model):
    id: str
    name: str
    path: str
    updated_at: datetime
