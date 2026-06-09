from __future__ import annotations

from dataclasses import dataclass

from game.ato.flighttype import FlightType
from game.commander.tasks.packageplanningtask import PackagePlanningTask
from game.commander.theaterstate import TheaterState
from game.theater import ControlPoint


@dataclass
class PlanScramble(PackagePlanningTask[ControlPoint]):
    """Plans a GCI Scramble (FlightType.SCRAMBLE) flight for a vulnerable friendly base.

    The flight launches with WeaponHold and orbits near the base. The
    reactive_scramble.lua plugin monitors RED radar contacts and issues
    EngageTargets / WeaponFree when a Blue aircraft enters range, turning
    the sleepy CAP into a live intercept.

    One round per CP is enough — the Lua script keeps the flight active for
    the entire mission duration.
    """

    def preconditions_met(self, state: TheaterState) -> bool:
        if not state.scrambles_needed.get(self.target, 0):
            return False
        return super().preconditions_met(state)

    def apply_effects(self, state: TheaterState) -> None:
        state.scrambles_needed[self.target] -= 1
        super().apply_effects(state)

    def propose_flights(self) -> None:
        size = self.get_flight_size()
        self.propose_flight(FlightType.SCRAMBLE, size)
