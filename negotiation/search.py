"""
Search Strategy Module for Feasible Charging Slots.

This module implements constraint-driven, heuristic search algorithms to explore
and rank candidate charging slots for an EV agent request.

Search Flow:
    EV Request
        ↓
    Explore Station Chargers
        ↓
    Generate Time Slot Intervals
        ↓
    Apply Constraints (Filter Invalid)
        ↓
    Calculate Utility for Feasible Slots
        ↓
    Sort by Utility (Best-First Search)
        ↓
    Return Ranked Candidate Proposals
"""

from typing import List, Dict, Any, Optional
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from negotiation.constraints import (
    time_to_minutes,
    minutes_to_time,
    SlotConstraintChecker,
)
from negotiation.utility import UtilityCalculator
from config import DEFAULT_TIME_STEP_MINUTES


class SlotSearchEngine:
    """
    Search engine for finding, filtering, and utility-ranking charging slots.
    Demonstrates Search and Heuristic Optimization in Multi-Agent environments.
    """

    def __init__(self, utility_calculator: Optional[UtilityCalculator] = None, step_size_min: int = DEFAULT_TIME_STEP_MINUTES):
        self.utility_calc = utility_calculator or UtilityCalculator()
        self.step_size = step_size_min
        self.constraint_checker = SlotConstraintChecker()

    def search_feasible_slots(
        self,
        station_id: str,
        chargers: List[Dict[str, Any]],
        existing_bookings: List[Dict[str, Any]],
        preferred_time_str: str,
        duration_minutes: int,
        max_waiting_time_min: int,
        priority: str,
        current_battery: float,
        base_price_per_kwh: float = 0.25
    ) -> List[Dict[str, Any]]:
        """
        Searches all chargers in a station for feasible slots matching EV constraints.
        Returns a list of candidate proposals sorted by utility score (highest first).
        """
        preferred_min = time_to_minutes(preferred_time_str)
        search_window_end_min = preferred_min + max_waiting_time_min
        feasible_slots: List[Dict[str, Any]] = []

        for charger in chargers:
            charger_id = charger["charger_id"]
            charger_status = charger.get("status", "AVAILABLE")
            power_kw = charger.get("power_kw", 50.0)

            # Generate candidate time steps within the allowable waiting window
            current_start_min = preferred_min
            while current_start_min <= search_window_end_min:
                candidate_end_min = current_start_min + duration_minutes
                
                # Check all hard constraints
                is_feasible, reason = self.constraint_checker.validate_slot_feasibility(
                    candidate_start_min=current_start_min,
                    candidate_end_min=candidate_end_min,
                    preferred_time_min=preferred_min,
                    required_duration_min=duration_minutes,
                    max_waiting_time_min=max_waiting_time_min,
                    charger_id=charger_id,
                    charger_status=charger_status,
                    existing_bookings=existing_bookings
                )

                if is_feasible:
                    waiting_time = current_start_min - preferred_min
                    # Energy calculation: duration in hours * charger power in kW
                    energy_kwh = (duration_minutes / 60.0) * power_kw
                    total_cost = round(energy_kwh * base_price_per_kwh, 2)

                    utility = self.utility_calc.evaluate_slot_utility(
                        priority=priority,
                        current_battery=current_battery,
                        waiting_time_min=waiting_time,
                        max_waiting_time_min=max_waiting_time_min,
                        total_cost=total_cost
                    )

                    feasible_slots.append({
                        "station_id": station_id,
                        "charger_id": charger_id,
                        "start_time": minutes_to_time(current_start_min),
                        "end_time": minutes_to_time(candidate_end_min),
                        "start_minutes": current_start_min,
                        "end_minutes": candidate_end_min,
                        "duration_minutes": duration_minutes,
                        "waiting_time_minutes": waiting_time,
                        "total_cost": total_cost,
                        "utility_score": utility,
                        "reason": "Satisfies all constraints"
                    })

                current_start_min += self.step_size

        # Best-First Search ranking: Sort feasible slots in descending order of utility
        feasible_slots.sort(key=lambda s: (s["utility_score"], -s["waiting_time_minutes"]), reverse=True)
        return feasible_slots
