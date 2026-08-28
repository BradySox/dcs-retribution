"""Build a terrain's country-border file (``resources/borders/<terrain>.yaml``).

Borders are a property of the *map*, not of a campaign: they are identical for
every campaign on a terrain, so they are generated once per terrain and every
campaign on that map gets them. The output carries a country name and a ring of
terrain XY vertices, nothing else.

Per country the tool clips the real boundary to the map, drops sliver pieces,
simplifies, and converts to terrain XY.

**The whole map is simplified as one polygon coverage, not country by country.**
Simplifying each country on its own moves a shared frontier twice, in two
different directions, so neighbours end up overlapping and the seam between them
weaves. Measured before the change, neighbouring outlines coincided only 35-65 %
of the time and left slivers of overlap up to 12.8 % of the smaller country.
``shapely.coverage_simplify`` keeps shared edges identical on both sides, which
is what makes a frontier one line. ``tests/test_country_borders.py`` asserts the
result is still a valid coverage.

**The vertex budget matters most where the coast is complicated.** Norway is the
worst case on the shipped maps -- a thin fjord coast wrapping around Sweden --
and at a 24-vertex budget it was 30.2 % wrong by symmetric difference against
the true clipped country, against Sweden's 9.7 %. The budget is 96.

**Every country on the map is drawn, including the one the map is named after.**
Leaving the host nation out on the theory that a border round the battlefield is
noise deletes Russia from Kola and Iran from the Persian Gulf -- the most
relevant border on each -- and leaves the middle of the map as the one region
with no line on it.

Input is one GeoJSON file per country, named ``<country>.json`` (lowercase,
underscores for spaces) in ``--geojson-dir``. Public-domain national boundary
data is fine; the shipped files were built from a high-resolution set. The data
is not vendored: regenerate only when a boundary or a map changes.

Usage:

    python scripts/build_country_borders.py kola \
        --geojson-dir <dir> \
        --countries Russia Norway Sweden Finland \
        --clip 63 72 12 42
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from country_border_geo import (  # noqa: E402
    TERRAINS,
    country_polygon,
    pieces_of,
    simplify_shared_to_budget,
    to_xy,
)
from shapely.geometry import Polygon, box  # noqa: E402


def border_lines(ring: list[tuple[float, float]]) -> list[str]:
    """The ring as wrapped yaml flow style.

    One vertex per line is 2,573 lines across the eight shipped maps and reviews
    as noise -- nobody reads a coordinate list, and at 96 vertices a country is
    a page of it. Flow style parses to exactly the same thing and costs a tenth
    of the lines.
    """
    out = ["    border: ["]
    row = "      "
    for index, (x, y) in enumerate(ring):
        pair = f"[{x:.0f}, {y:.0f}]"
        if index < len(ring) - 1:
            pair += ","
        if len(row) + len(pair) > 88 and row.strip():
            out.append(row.rstrip())
            row = "      "
        row += pair + " "
    if row.strip():
        out.append(row.rstrip())
    out.append("    ]")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("terrain", choices=sorted(TERRAINS))
    parser.add_argument("--geojson-dir", type=Path, required=True)
    parser.add_argument("--countries", nargs="+", required=True)
    parser.add_argument(
        "--clip",
        nargs=4,
        type=float,
        required=True,
        metavar=("LAT_MIN", "LAT_MAX", "LON_MIN", "LON_MAX"),
    )
    parser.add_argument(
        "--max-vertices",
        type=int,
        default=96,
        help="Ring vertex budget, binding the WORST ring on the map -- the whole "
        "map is simplified as one coverage at a single tolerance, because a "
        "shared frontier has to be simplified once to come out the same on both "
        "sides of it. MEASURED 2026-08-26 on Kola: at 96 the frontier match is "
        "89%% (against 35%% when each country was simplified alone), Norway's "
        "shape error is 7%% (against 14.7%%), and the map carries 219 vertices "
        "against 289 -- better on every axis at once, because Visvalingam on a "
        "coverage spends vertices where the shape needs them. The cost of "
        "raising it is F10 markup count: the fill is drawn triangle by "
        "triangle.",
    )
    parser.add_argument(
        "--min-area-km2",
        type=float,
        default=0.0,
        help="Drop landmasses smaller than this. Each surviving piece becomes a "
        "zone of its own, so an archipelago needs a floor: the "
        "Falklands map otherwise gives Chile five, one of them the 1,439 km² "
        "Cape Horn group. Real territory, but not airspace anyone contests.",
    )
    parser.add_argument("--out", type=Path, default=Path("resources/borders"))
    args = parser.parse_args()

    terrain = TERRAINS[args.terrain]()
    lat_min, lat_max, lon_min, lon_max = args.clip
    clip = box(lon_min, lat_min, lon_max, lat_max)

    lines = [
        f"# Country border geometry for the {args.terrain} map. GENERATED by",
        "# scripts/build_country_borders.py -- edit the tool, not this file.",
        "#",
        "# Real national boundaries, clipped to the map and simplified as one",
        "# polygon coverage so a frontier two countries share is a single line",
        "# rather than two traces of it. Drawn on the F10 map by the",
        "# 'countryborders' plugin.",
        "#",
        f"# Clip: {args.clip[0]} {args.clip[1]} {args.clip[2]} {args.clip[3]}",
        f"terrain: {args.terrain}",
        "zones:",
    ]

    # Pass 1: clip every country to the map and drop slivers. Nothing is
    # simplified yet -- that has to happen across all of them at once, or each
    # shared frontier comes out drawn twice (see simplify_shared).
    import math

    collected: list[tuple[str, Any]] = []
    for name in args.countries:
        path = args.geojson_dir / f"{name.lower().replace(' ', '_')}.json"
        if not path.exists():
            print(f"  !! {name}: no geojson at {path}", file=sys.stderr)
            continue
        geom = country_polygon(json.loads(path.read_text(encoding="utf-8")))
        parts = pieces_of(geom.intersection(clip))
        if not parts:
            print(f"  -- {name}: nothing on this map, skipped", file=sys.stderr)
            continue
        for piece in parts:
            if args.min_area_km2:
                # Rough but sufficient: one degree of latitude is ~111 km, and
                # one of longitude ~111*cos(lat) at the piece's own latitude.
                lat = math.radians(piece.centroid.y)
                km2 = piece.area * 111.0 * (111.0 * math.cos(lat))
                if km2 < args.min_area_km2:
                    print(
                        f"  -- {name}: dropped a {km2:.0f} km² landmass",
                        file=sys.stderr,
                    )
                    continue
            collected.append((name, piece))

    # Pass 2: one shared coverage, one tolerance, so neighbours agree.
    simplified = simplify_shared_to_budget(collected, args.max_vertices)
    if args.min_area_km2:
        # Again, because rebuilding the coverage can shed a country into extra
        # fragments. Dropping one leaves a gap, which a coverage allows; an
        # overlap or a mismatched edge is what it does not.
        kept = []
        for name, piece in simplified:
            lat = math.radians(piece.centroid.y)
            km2 = piece.area * 111.0 * (111.0 * math.cos(lat))
            if km2 >= args.min_area_km2:
                kept.append((name, piece))
            else:
                print(f"  -- {name}: dropped a {km2:.0f} km² fragment", file=sys.stderr)
        simplified = kept

    written = 0
    seen: dict[str, int] = {}
    totals: dict[str, int] = {}
    for name, _ in simplified:
        totals[name] = totals.get(name, 0) + 1
    for name, piece in simplified:
        seen[name] = seen.get(name, 0) + 1
        ring = [(float(x), float(y)) for x, y in list(piece.exterior.coords)[:-1]]
        ring_xy = to_xy(terrain, ring)
        label = name if totals[name] == 1 else f"{name} (part {seen[name]})"
        lines.append(f"  # {label} — {len(ring_xy)} vertices")
        lines.append(f"  - country: {name}")
        lines.extend(border_lines(ring_xy))
        written += 1

    args.out.mkdir(parents=True, exist_ok=True)
    target = args.out / f"{args.terrain}.yaml"
    target.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {target} ({written} zones)")


if __name__ == "__main__":
    main()
