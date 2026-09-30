from __future__ import annotations

from typing import Any


KNOWN_SURFACES = frozenset(
    {"native_subagent", "app_thread", "ephemeral_codex_cli"}
)


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
