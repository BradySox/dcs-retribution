"""Squadron-sequenced Hornet/Tomcat board numbers.

pydcs hands every aircraft a random three-digit ``onboard_num`` (an unordered
``set.pop()``), so Navy jets spawned with nonsense modexes. The allocator gives
each Hornet/Tomcat squadron a block (100, 200, 300, ... -- Tomcats take the
traditional CVW fighter blocks first) and numbers the squadron's jets
sequentially within it: the first generated jet X00, the second X01, and so on
across every flight of the mission. Other airframes keep the stock number.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from uuid import uuid4

from game.missiongenerator.aircraft.modex import MODEX_AIRCRAFT_IDS, ModexAllocator


def _squadron(dcs_id: str) -> Any:
    return SimpleNamespace(
        id=uuid4(),
        aircraft=SimpleNamespace(dcs_unit_type=SimpleNamespace(id=dcs_id)),
    )


def _game(*coalition_squadrons: list[Any]) -> Any:
    coalitions = [
        SimpleNamespace(
            air_wing=SimpleNamespace(iter_squadrons=lambda sqs=squadrons: iter(sqs))
        )
        for squadrons in coalition_squadrons
    ]
    return SimpleNamespace(coalitions=iter(coalitions))


def _group(size: int) -> Any:
    return SimpleNamespace(
        units=[SimpleNamespace(onboard_num="999") for _ in range(size)]
    )


class _Country:
    def __init__(self) -> None:
        self.reserved: list[str] = []

    def reserve_onboard_num(self, number: str) -> bool:
        taken = number in self.reserved
        self.reserved.append(number)
        return taken


def _numbers(group: Any) -> list[str]:
    return [unit.onboard_num for unit in group.units]


def test_squadron_jets_are_sequenced_from_x00() -> None:
    squadron = _squadron("FA-18C_hornet")
    allocator = ModexAllocator(_game([squadron]))
    country = _Country()

    first_flight = _group(2)
    second_flight = _group(3)
    allocator.assign(squadron, first_flight, country)  # type: ignore[arg-type]
    allocator.assign(squadron, second_flight, country)  # type: ignore[arg-type]

    # The sequence runs across the squadron's flights, not per group.
    assert _numbers(first_flight) == ["100", "101"]
    assert _numbers(second_flight) == ["102", "103", "104"]


def test_squadrons_get_distinct_hundred_blocks() -> None:
    first = _squadron("FA-18C_hornet")
    second = _squadron("FA-18C_hornet")
    allocator = ModexAllocator(_game([first, second]))
    country = _Country()

    first_group = _group(1)
    second_group = _group(1)
    allocator.assign(first, first_group, country)  # type: ignore[arg-type]
    allocator.assign(second, second_group, country)  # type: ignore[arg-type]

    assert _numbers(first_group) == ["100"]
    assert _numbers(second_group) == ["200"]


def test_tomcats_take_the_fighter_blocks_ahead_of_hornets() -> None:
    # Air-wing order lists the Hornets first; the Tomcat squadron still takes
    # the 100 block (the traditional CVW fighter modex), Hornets follow.
    hornets = _squadron("FA-18C_hornet")
    tomcats = _squadron("F-14B")
    allocator = ModexAllocator(_game([hornets, tomcats]))
    country = _Country()

    hornet_group = _group(1)
    tomcat_group = _group(1)
    allocator.assign(hornets, hornet_group, country)  # type: ignore[arg-type]
    allocator.assign(tomcats, tomcat_group, country)  # type: ignore[arg-type]

    assert _numbers(tomcat_group) == ["100"]
    assert _numbers(hornet_group) == ["200"]


def test_each_coalition_blocks_start_at_100() -> None:
    blue = _squadron("FA-18C_hornet")
    red = _squadron("F-14A")  # the Iranian Tomcat case
    allocator = ModexAllocator(_game([blue], [red]))

    blue_group = _group(1)
    red_group = _group(1)
    allocator.assign(blue, blue_group, _Country())  # type: ignore[arg-type]
    allocator.assign(red, red_group, _Country())  # type: ignore[arg-type]

    assert _numbers(blue_group) == ["100"]
    assert _numbers(red_group) == ["100"]


def test_non_modex_aircraft_keep_the_stock_number() -> None:
    viper = _squadron("F-16C_50")
    allocator = ModexAllocator(_game([viper]))
    country = _Country()

    group = _group(2)
    allocator.assign(viper, group, country)  # type: ignore[arg-type]

    assert _numbers(group) == ["999", "999"]
    assert country.reserved == []


def test_block_is_reserved_with_the_country_once() -> None:
    squadron = _squadron("F-14B")
    allocator = ModexAllocator(_game([squadron]))
    country = _Country()

    allocator.assign(squadron, _group(1), country)  # type: ignore[arg-type]
    allocator.assign(squadron, _group(1), country)  # type: ignore[arg-type]

    # The whole 100-199 block is fenced off from pydcs's random pool, once.
    assert country.reserved == [f"{n}" for n in range(100, 200)]


def test_blocks_wrap_after_nine_squadrons() -> None:
    squadrons = [_squadron("FA-18C_hornet") for _ in range(10)]
    allocator = ModexAllocator(_game(squadrons))

    ninth_group = _group(1)
    tenth_group = _group(1)
    allocator.assign(squadrons[8], ninth_group, _Country())  # type: ignore[arg-type]
    allocator.assign(squadrons[9], tenth_group, _Country())  # type: ignore[arg-type]

    assert _numbers(ninth_group) == ["900"]
    assert _numbers(tenth_group) == ["100"]


def test_curated_ids_exist_in_pydcs() -> None:
    # Guard the curated set against pydcs renames -- every id must resolve to
    # a real plane type.
    import dcs.planes

    known = {
        getattr(dcs.planes, name).id
        for name in dir(dcs.planes)
        if isinstance(getattr(getattr(dcs.planes, name), "id", None), str)
    }
    missing = MODEX_AIRCRAFT_IDS - known
    assert not missing, f"unknown pydcs plane id(s): {sorted(missing)}"
