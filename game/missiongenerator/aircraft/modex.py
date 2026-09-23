"""Squadron-sequenced board numbers (modex) for Hornets and Tomcats.

pydcs assigns every aircraft's ``onboard_num`` by popping from an *unordered*
set (``Country.next_onboard_num`` -> ``set.pop()``), so board numbers come out
as random three-digit values. Navy jets don't wear random numbers: the air
wing gives each squadron a modex block (100, 200, 300, ...) and numbers the
squadron's jets sequentially inside it -- the first jet X00, the second X01,
the third X02.

:class:`ModexAllocator` pre-assigns one block per Hornet/Tomcat squadron at
construction (per coalition, in air-wing order, Tomcats ahead of Hornets --
the traditional CVW fighter blocks) and re-stamps every generated unit of
those squadrons with the next number in its squadron's sequence, in
generation order: tasked flights first, then the untasked ramp aircraft. The
campaign does not model individual airframes, so numbering is per-mission
(deterministic within a mission, not sticky to a pilot across turns). Every
other airframe keeps the stock pydcs number.
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING
from uuid import UUID

from dcs.country import Country
from dcs.unitgroup import FlyingGroup

if TYPE_CHECKING:
    from game import Game
    from game.squadrons import Squadron

#: DCS unit type ids that wear squadron-sequenced modex numbers.
MODEX_AIRCRAFT_IDS: frozenset[str] = frozenset(
    {
        # Hornets (player module + AI variants).
        "FA-18C_hornet",
        "F/A-18A",
        "F/A-18C",
        # Tomcats (Heatblur player variants + the AI F-14A). No F-14 livery
        # declares a board-number material, so DCS never paints these on the
        # airframe -- the Tomcat's visible modex is its livery, sequenced by
        # liveryallocator.py instead.
        "F-14A",
        "F-14A-135-GR",
        "F-14A-135-GR-Early",
        "F-14A-95-GR",
        "F-14B",
        "F-14BU",
    }
)

#: Blocks run 100, 200, ... 900 and wrap after nine squadrons -- a coalition
#: fielding a tenth Hornet/Tomcat squadron reuses blocks rather than growing a
#: fourth digit (DCS board numbers are three digits).
_FIRST_BLOCK = 100
_MAX_BLOCKS = 9
#: One squadron's numbers span X00-X99.
_BLOCK_SIZE = 100


def _tomcats_first(squadron: Squadron) -> int:
    """Sort key: F-14 squadrons take the 100/200 fighter blocks like a real CVW."""
    return 0 if squadron.aircraft.dcs_unit_type.id.startswith("F-14") else 1


class ModexAllocator:
    """Deterministic per-squadron modex blocks + a per-squadron jet sequence."""

    def __init__(self, game: Game) -> None:
        self._blocks: dict[UUID, int] = {}
        self._next_index: dict[UUID, int] = {}
        self._reserved: set[UUID] = set()
        for coalition in game.coalitions:
            squadrons = [
                squadron
                for squadron in coalition.air_wing.iter_squadrons()
                if squadron.aircraft.dcs_unit_type.id in MODEX_AIRCRAFT_IDS
            ]
            # Stable sort: Tomcats first, air-wing order preserved within a
            # type -- so a squadron keeps the same block mission after mission.
            squadrons.sort(key=_tomcats_first)
            for index, squadron in enumerate(squadrons):
                self._blocks[squadron.id] = (
                    _FIRST_BLOCK + (index % _MAX_BLOCKS) * _BLOCK_SIZE
                )

    def assign(
        self, squadron: Squadron, group: FlyingGroup[Any], country: Country
    ) -> None:
        """Stamp the group's units with the squadron's next modex numbers.

        A no-op for squadrons outside the Hornet/Tomcat set. The squadron's
        whole block is reserved with the country on first use so pydcs's
        random allocator can't hand a later same-country aircraft a number
        inside it.
        """
        block = self._blocks.get(squadron.id)
        if block is None:
            return
        if squadron.id not in self._reserved:
            self._reserved.add(squadron.id)
            for number in range(block, block + _BLOCK_SIZE):
                country.reserve_onboard_num(f"{number:03}")
        for unit in group.units:
            index = self._next_index.get(squadron.id, 0)
            self._next_index[squadron.id] = index + 1
            # More than 100 airframes of one squadron in one mission cannot
            # happen with real squadron sizes; wrap within the block rather
            # than bleed into the next squadron's.
            unit.onboard_num = f"{block + index % _BLOCK_SIZE:03}"
