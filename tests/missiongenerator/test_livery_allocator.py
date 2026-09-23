"""CAG-bird-first livery sequencing (see liveryallocator.py).

The Tomcat's visible board number is its livery, so the order liveries are
handed out is the modex order: the squadron's first jet of the mission wears
the X00 CAG bird, every jet after it a line bird.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from uuid import uuid4

from game.missiongenerator.aircraft.liveryallocator import LiveryAllocator
from game.squadrons.squadron import Squadron


def _squadron(*liveries: str, pool: list[str] | None = None) -> Any:
    squadron = SimpleNamespace(
        id=uuid4(),
        livery_set=list(liveries),
        _livery_pool=list(pool or []),
    )
    squadron.ordered_livery_set = list(squadron.livery_set) + list(
        squadron._livery_pool
    )
    return squadron


def _take(allocator: LiveryAllocator, squadron: Any, count: int) -> list[str | None]:
    return [allocator.next_livery(squadron) for _ in range(count)]


def test_cag_bird_flies_once_then_line_jets_cycle() -> None:
    squadron = _squadron("AA100", "AA101", "AA103", "AA105")

    assert _take(LiveryAllocator(), squadron, 8) == [
        "AA100",  # the CAG bird, once for the whole mission
        "AA101",
        "AA103",
        "AA105",
        "AA101",
        "AA103",
        "AA105",
        "AA101",
    ]


def test_sequence_is_per_squadron() -> None:
    allocator = LiveryAllocator()
    first = _squadron("AA100", "AA101")
    second = _squadron("AC100", "AC101")

    assert allocator.next_livery(first) == "AA100"
    assert allocator.next_livery(second) == "AC100"
    assert allocator.next_livery(first) == "AA101"
    assert allocator.next_livery(second) == "AC101"


def test_two_livery_squadron_alternates_instead_of_reserving_a_cag_bird() -> None:
    """Reserving one of two would leave every later jet on the single survivor."""
    squadron = _squadron("AD101", "AD107")

    assert _take(LiveryAllocator(), squadron, 5) == [
        "AD101",
        "AD107",
        "AD101",
        "AD107",
        "AD101",
    ]


def test_single_livery_squadron_repeats_rather_than_returning_none() -> None:
    squadron = _squadron("Only Livery")

    assert _take(LiveryAllocator(), squadron, 3) == [
        "Only Livery",
        "Only Livery",
        "Only Livery",
    ]


def test_squadron_without_a_livery_set_is_left_alone() -> None:
    assert LiveryAllocator().next_livery(_squadron()) is None


def test_a_mid_rotation_save_keeps_every_livery() -> None:
    """The old random round-robin drained the set into ``_livery_pool``."""
    squadron = _squadron("AA105", pool=["AA100", "AA101"])

    assert _take(LiveryAllocator(), squadron, 3) == ["AA105", "AA100", "AA101"]


def test_ordered_livery_set_rejoins_a_drained_pool() -> None:
    """The property the allocator reads, exercised on the real Squadron."""
    squadron = SimpleNamespace(livery_set=["AA105"], _livery_pool=["AA100", "AA101"])

    assert Squadron.ordered_livery_set.fget(squadron) == [  # type: ignore[attr-defined]
        "AA105",
        "AA100",
        "AA101",
    ]
