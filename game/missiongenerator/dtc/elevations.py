"""Field elevations for DTC steerpoints.

The F-16C and FA-18C DTC editors fill a new point's elevation from the terrain
(``getAltitude(x, y)``), and the jet shows whatever the file carries -- the
Viper's loader defaults a missing value to 2000 m -- so the generator has to
write one. Retribution has no terrain height source; the only elevations it
can know are the airfields', so a steerpoint takes the nearest airfield's.
Exact on a flat map, within the field's valley elsewhere, closer than 0
everywhere.

``resources/dcs/airfield_elevations.json`` carries metres AMSL per pydcs
``Airport.id``, keyed by terrain name. Seven terrains were measured inside DCS
(``land.getHeight``); the rest come from OpenStreetMap ``ele`` tags with the
Open-Elevation DEM (NASA SRTM) as the fallback. Attribution is in the file.
"""

from __future__ import annotations

import json
import logging
import math
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from dcs import Point

    from game import Game
    from game.theater import ControlPoint

ELEVATIONS_RESOURCE_PATH = Path("resources/dcs/airfield_elevations.json")


@lru_cache(maxsize=None)
def _tables() -> dict[str, dict[str, float]]:
    try:
        with ELEVATIONS_RESOURCE_PATH.open(encoding="utf-8") as fh:
            terrains = json.load(fh)["terrains"]
    except (OSError, ValueError, KeyError):
        logging.exception("DTC: airfield elevation table unreadable; elevations read 0")
        return {}
    return {
        terrain: {
            str(airport_id): float(elevation) for airport_id, elevation in table.items()
        }
        for terrain, table in terrains.items()
    }


def field_elevation(terrain_name: str, airport_id: Any) -> Optional[float]:
    """Metres AMSL for a pydcs airport, or None when the table has no entry."""
    return _tables().get(terrain_name, {}).get(str(airport_id))


def control_point_elevation(game: Game, control_point: ControlPoint) -> Optional[float]:
    """The elevation of a control point's airfield; None for a boat or a FOB."""
    airport = getattr(control_point, "airport", None)
    if airport is None:
        return None
    return field_elevation(game.theater.terrain.name, airport.id)


def nearest_field_elevation(game: Game, position: Point) -> float:
    """The elevation of the nearest airfield with a known one, metres AMSL.

    Boats and FOBs have no entry and never answer, so a coastal target is not
    pulled to sea level by the carrier. 0 only when no field on the map has one.
    """
    best: Optional[float] = None
    best_distance = math.inf
    for cp in game.theater.controlpoints:
        elevation = control_point_elevation(game, cp)
        if elevation is None:
            continue
        distance = cp.position.distance_to_point(position)
        if distance < best_distance:
            best, best_distance = elevation, distance
    return best if best is not None else 0.0
