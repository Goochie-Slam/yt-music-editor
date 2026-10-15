from __future__ import annotations

from fastapi import APIRouter, Request, Response

from app.core.presets import PresetStore
from app.models.preset import TransitionPreset, TransitionPresetIn

router = APIRouter(prefix="/api/presets/transitions", tags=["presets"])


def _store(request: Request) -> PresetStore:
    store: PresetStore = request.app.state.presets
    return store


@router.get("")
def list_presets(request: Request) -> list[TransitionPreset]:
    return _store(request).list()


@router.post("")
def create_preset(body: TransitionPresetIn, request: Request) -> TransitionPreset:
    return _store(request).create(body)


@router.put("/{preset_id}")
def update_preset(preset_id: str, body: TransitionPresetIn, request: Request) -> TransitionPreset:
    return _store(request).update(preset_id, body)


@router.delete("/{preset_id}", status_code=204)
def delete_preset(preset_id: str, request: Request) -> Response:
    _store(request).delete(preset_id)
    return Response(status_code=204)
