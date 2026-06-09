from collections.abc import Iterator

from game.commander.tasks.primitive.scramble import PlanScramble
from game.commander.theaterstate import TheaterState
from game.htn import CompoundTask, Method


class ProvideGciCoverage(CompoundTask[TheaterState]):
    """Assigns a GCI Scramble intercept flight to each vulnerable friendly base.

    Mirrors ProtectAirSpace (BARCAP) but uses FlightType.SCRAMBLE so the
    reactive_scramble.lua plugin can pick up and control these flights at
    runtime. Any fighter-capable squadron can fulfill the task regardless of
    its primary mission type.
    """

    def each_valid_method(self, state: TheaterState) -> Iterator[Method[TheaterState]]:
        for cp, needed in state.scrambles_needed.items():
            if needed > 0:
                yield [PlanScramble(cp)]
