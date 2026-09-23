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

from game.missiongenerator.aircraft.modex import (
    MODEX_AIRCRAFT_IDS,
    ModexAllocator,
    board_number_conflict,
)


def _squadron(dcs_id: str) -> Any:
    return SimpleNamespace(
        id=uuid4(),
        aircraft=SimpleNamespace(dcs_unit_type=SimpleNamespace(id=dcs_id)),
    )


def _game(*coalition_squadrons: list[Any], flights: list[Any] | None = None) -> Any:
    """``flights`` are the first coalition's fragged flights, one package."""
    coalitions = [
        SimpleNamespace(
            air_wing=SimpleNamespace(iter_squadrons=lambda sqs=squadrons: iter(sqs)),
            ato=SimpleNamespace(
                packages=[SimpleNamespace(flights=flights or [])] if index == 0 else []
            ),
        )
        for index, squadrons in enumerate(coalition_squadrons)
    ]
    return SimpleNamespace(coalitions=iter(coalitions))


def _flight(squadron: Any, count: int, board_number: int | None) -> Any:
    return SimpleNamespace(squadron=squadron, count=count, board_number=board_number)


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

    def next_onboard_num(self) -> str:
        return "555"


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


def test_pinned_flight_wears_its_numbers_and_the_squadron_skips_them() -> None:
    squadron = _squadron("FA-18C_hornet")
    pinned = _flight(squadron, 2, 101)
    allocator = ModexAllocator(_game([squadron], flights=[pinned]))
    country = _Country()

    pinned_group = _group(2)
    other_group = _group(3)
    allocator.assign(squadron, pinned_group, country, pinned)  # type: ignore[arg-type]
    allocator.assign(squadron, other_group, country)  # type: ignore[arg-type]

    assert _numbers(pinned_group) == ["101", "102"]
    assert _numbers(other_group) == ["100", "103", "104"]


def test_a_pin_off_the_navy_set_is_ignored() -> None:
    viper = _squadron("F-16C_50")
    pinned = _flight(viper, 2, 7)
    allocator = ModexAllocator(_game([viper], flights=[pinned]))

    group = _group(2)
    allocator.assign(viper, group, _Country(), pinned)  # type: ignore[arg-type]

    assert _numbers(group) == ["999", "999"]
    assert board_number_conflict(_flight(viper, 1, None), 7, [pinned]) is None


def test_another_package_never_wears_a_pinned_number() -> None:
    hornets = _squadron("FA-18C_hornet")
    vipers = _squadron("F-16C_50")
    pinned = _flight(hornets, 1, 999)
    allocator = ModexAllocator(_game([hornets, vipers], flights=[pinned]))
    country = _Country()

    # pydcs dealt the Viper the pinned number at random: it is re-rolled.
    viper_group = _group(1)
    allocator.assign(vipers, viper_group, country)  # type: ignore[arg-type]

    assert _numbers(viper_group) == ["555"]
    # And the claim is fenced off from the country's random pool.
    assert "999" in country.reserved


def test_a_clash_left_by_a_resize_falls_back_for_the_later_flight() -> None:
    squadron = _squadron("FA-18C_hornet")
    first = _flight(squadron, 2, 10)
    second = _flight(squadron, 2, 11)  # 11 is first's wingman
    allocator = ModexAllocator(_game([squadron], flights=[first, second]))

    group = _group(2)
    allocator.assign(squadron, group, _Country(), second)  # type: ignore[arg-type]

    # 11 is first's, so that member falls back to the squadron sequence.
    assert _numbers(group) == ["100", "012"]


def test_conflict_names_the_flight_holding_the_number() -> None:
    squadron = _squadron("FA-18C_hornet")
    holder = _flight(squadron, 4, 200)
    flight = _flight(squadron, 2, None)

    assert board_number_conflict(flight, 202, [holder, flight]) == (
        202,
        holder,
    )
    assert board_number_conflict(flight, 204, [holder, flight]) is None


def test_conflict_ignores_the_flight_itself() -> None:
    flight = _flight(_squadron("FA-18C_hornet"), 4, 300)

    assert board_number_conflict(flight, 301, [flight]) is None


def test_a_run_past_999_is_refused() -> None:
    flight = _flight(_squadron("FA-18C_hornet"), 4, None)

    assert board_number_conflict(flight, 998, []) == (1000, None)
