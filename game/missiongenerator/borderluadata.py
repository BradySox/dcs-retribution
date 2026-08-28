"""Emit the map's country borders for the ``countryborders`` Lua plugin.

Read straight from the shipped terrain file at generation time. The borders are
a property of the terrain and are never edited in play, so nothing about them
belongs in the campaign model or in a save.

Emits ``dcsRetribution.CountryBorders``; the plugin draws it and does nothing
else. If the node is absent the plugin returns immediately.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from game.theater.terrainborders import load_terrain_borders

if TYPE_CHECKING:
    from game.game import Game
    from game.missiongenerator.luagenerator import LuaData


def label_point(ring: list[tuple[float, float]]) -> Optional[tuple[float, float]]:
    """Where to write the country's name, in terrain XY.

    The polygon's representative point rather than its centroid: a national
    border is usually concave -- Norway spectacularly so -- and a centroid
    lands in the sea or inside the neighbour. shapely guarantees this one is
    inside the polygon it came from.
    """
    from shapely.geometry import Polygon

    if len(ring) < 3:
        return None
    try:
        point = Polygon(ring).buffer(0).representative_point()
    except Exception:
        return None
    return (float(point.x), float(point.y))


def populate_border_lua(lua_data: "LuaData", game: "Game") -> None:
    entries = load_terrain_borders(game.theater.terrain.name)
    if not entries:
        return
    node = lua_data.get_or_create_item("CountryBorders")
    zones = node.get_or_create_item("zones")
    drawn = 0
    for entry in entries:
        record = zones.add_item()
        record.add_key_value("country", entry["country"])
        label = label_point(entry["border"])
        if label is not None:
            record.add_key_value("labelX", f"{label[0]:.1f}")
            record.add_key_value("labelZ", f"{label[1]:.1f}")
        verts = record.get_or_create_item("verts")
        for x, y in entry["border"]:
            vertex = verts.add_item()
            vertex.add_key_value("x", f"{x:.1f}")
            vertex.add_key_value("z", f"{y:.1f}")
        drawn += 1
    logging.info("Country borders: %d drawn on the F10 map.", drawn)
