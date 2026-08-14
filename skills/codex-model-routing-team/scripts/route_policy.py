from __future__ import annotations

import re
from typing import Any


KNOWN_SURFACES = frozenset({"native_subagent", "app_thread"})


def version_tuple(value: Any) -> tuple[int, int, int] | None:
    if not isinstance(value, str):
        return None
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", value.strip())
    return tuple(int(part) for part in match.groups()) if match else None


def supported_thinking(entry: dict[str, Any], surface: str) -> set[str]:
    """Return the declared reasoning levels for one model/surface combination."""
    surface_map = entry.get("surface_thinking")
    if isinstance(surface_map, dict):
        surface_levels = surface_map.get(surface)
        if isinstance(surface_levels, list):
            return {item for item in surface_levels if isinstance(item, str)}
        return set()

    fallback = entry.get("thinking")
    if not isinstance(fallback, list):
        return set()
    return {item for item in fallback if isinstance(item, str)}


def runtime_model_id(entry: dict[str, Any], surface: str, speed: str) -> str | None:
    """Resolve the exact model string accepted by one execution Surface."""
    surface_map = entry.get("surface_runtime_models")
    if isinstance(surface_map, dict):
        surface_entry = surface_map.get(surface)
        if isinstance(surface_entry, str) and surface_entry:
            return surface_entry
        if isinstance(surface_entry, dict):
            value = surface_entry.get(speed)
            if isinstance(value, str) and value:
                return value
            return None
    model_id = entry.get("id")
    return model_id if isinstance(model_id, str) and model_id else None
