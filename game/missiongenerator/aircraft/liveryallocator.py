"""CAG-bird-first livery sequencing for squadrons with a livery set.

No F-14 livery declares a board-number material, so DCS never paints the
mission's ``onboard_num`` on a Tomcat -- the visible modex is whatever the
livery texture carries. (Every airframe that does show one -- Su-27, MiG-29A,
F-15C, Su-25, FA-18C -- names the material in its livery description.lua; no
stock F-14 livery does, and Heatblur ships four VF-32 skins differing only in
the painted number.) On the Tomcat the livery IS the board number, which makes
the ORDER liveries are handed out the modex order.

:class:`LiveryAllocator` gives a squadron's first jet of the mission the first
entry of its ``livery_set`` -- by convention the X00 CAG bird -- then cycles the
line jets behind it, in generation order (tasked flights first, then the ramp).
One CAG bird per squadron per mission, like a real air wing. Squadrons with no
livery set are untouched.

Replaces ``Squadron.random_round_robin_livery_from_set`` for mission
generation, which picked at random and so could put two CAG birds in an
eight-jet squadron.
"""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from game.squadrons import Squadron


class LiveryAllocator:
    """Deterministic CAG-bird-first livery sequence, per squadron, per mission."""

    def __init__(self) -> None:
        self._next_index: dict[UUID, int] = {}

    def next_livery(self, squadron: Squadron) -> Optional[str]:
        """Return the squadron's next livery, or None when it has no set."""
        liveries = squadron.ordered_livery_set
        if not liveries:
            return None
        index = self._next_index.get(squadron.id, 0)
        self._next_index[squadron.id] = index + 1
        # Holding entry 0 back as the CAG bird needs a line pool of at least
        # two. With fewer, reserving one leaves every other jet wearing the
        # single survivor -- a one-number squadron -- so cycle the whole set.
        # DCS ships exactly two F-14B(U) liveries for VF-101, VF-11 and VF-143.
        if len(liveries) < 3:
            return liveries[index % len(liveries)]
        if index == 0:
            return liveries[0]
        line = liveries[1:]
        return line[(index - 1) % len(line)]
