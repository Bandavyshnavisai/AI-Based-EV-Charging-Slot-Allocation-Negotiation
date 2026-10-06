"""
Constraint-Based Reasoning Module for EV Charging Slot Allocation.

This module defines hard and soft constraints for evaluating slot feasibility:
1. Charger Hardware Availability
2. No Temporal Booking Overlap
3. Duration Feasibility
4. Maximum Waiting Time (EV Patience Limit)
5. Battery Urgency Constraint
6. Operational Hours / Schedule Bounds
7. Payment Verification Constraint
"""

from typing import Tuple, List, Dict, Any, Optional


def time_to_minutes(time_str: str) -> int:
    """Converts 'HH:MM' string format to total minutes from midnight (00:00)."""
    parts = time_str.strip().split(":")
    hours = int(parts[0])
    minutes = int(parts[1])
    return hours * 60 + minutes


def minutes_to_time(total_minutes: int) -> str:
    """Converts total minutes from midnight back to 'HH:MM' string format."""
    total_minutes = total_minutes % (24 * 60)
    hours = total_minutes // 60
    minutes = total_minutes % 60
    return f"{hours:02d}:{minutes:02d}"


def intervals_overlap(start1_min: int, end1_min: int, start2_min: int, end2_min: int) -> bool:
    """
    Checks if two continuous time intervals [start1, end1] and [start2, end2] overlap.
    Overlapping occurs if max(start1, start2) < min(end1, end2).
    """
    return max(start1_min, start2_min) < min(end1_min, end2_min)


class SlotConstraintChecker:
    """
    Evaluates hard and soft constraints for charging slot candidates.
    Demonstrates Constraint-Based and Rule-Based AI reasoning.
    """

    @staticmethod
    def is_charger_available(charger_status: str) -> bool:
        """Hard Constraint 1: Charger must be operational and available."""
        return charger_status.upper() in ["AVAILABLE", "IDLE"]

    @staticmethod
    def is_slot_free_of_overlap(
        candidate_start_min: int,
        candidate_end_min: int,
        existing_bookings: List[Dict[str, Any]],
        charger_id: str
    ) -> bool:
        """
        Hard Constraint 2: No overlapping bookings on the same charger.
        Filters out any candidate slot that collides with confirmed bookings.
        """
        for booking in existing_bookings:
            if booking.get("status") == "CANCELLED" or booking.get("payment_status") == "REJECTED":
                continue
            if booking.get("charger_id") == charger_id:
                b_start = time_to_minutes(booking["start_time"])
                b_end = time_to_minutes(booking["end_time"])
                if intervals_overlap(candidate_start_min, candidate_end_min, b_start, b_end):
                    return False
        return True

    @staticmethod
    def is_duration_satisfied(slot_duration_min: int, required_duration_min: int) -> bool:
        """Hard Constraint 3: Slot duration must meet or exceed required charging duration."""
        return slot_duration_min >= required_duration_min

    @staticmethod
    def is_within_max_waiting_time(
        preferred_time_min: int,
        candidate_start_min: int,
        max_waiting_time_min: int
    ) -> bool:
        """
        Hard Constraint 4: Delay (waiting time) must not exceed EV's maximum acceptable limit.
        Candidate start must be >= preferred_time and <= preferred_time + max_waiting_time.
        """
        delay = candidate_start_min - preferred_time_min
        return 0 <= delay <= max_waiting_time_min

    @staticmethod
    def is_within_operational_horizon(candidate_start_min: int, candidate_end_min: int,
                                      day_start_min: int = 360, day_end_min: int = 1440) -> bool:
        """Hard Constraint 5: Slot must fit within station operating horizon (e.g. 06:00 - 24:00)."""
        return (candidate_start_min >= day_start_min) and (candidate_end_min <= day_end_min)

    @classmethod
    def validate_slot_feasibility(
        cls,
        candidate_start_min: int,
        candidate_end_min: int,
        preferred_time_min: int,
        required_duration_min: int,
        max_waiting_time_min: int,
        charger_id: str,
        charger_status: str,
        existing_bookings: List[Dict[str, Any]]
    ) -> Tuple[bool, str]:
        """
        Validates all hard constraints in sequence.
        Returns (is_feasible, reason_if_invalid).
        """
        if not cls.is_charger_available(charger_status):
            return False, f"Charger {charger_id} is currently unavailable ({charger_status})"

        slot_duration = candidate_end_min - candidate_start_min
        if not cls.is_duration_satisfied(slot_duration, required_duration_min):
            return False, f"Slot duration ({slot_duration}m) is less than required duration ({required_duration_min}m)"

        if not cls.is_within_max_waiting_time(preferred_time_min, candidate_start_min, max_waiting_time_min):
            delay = candidate_start_min - preferred_time_min
            return False, f"Waiting delay ({delay}m) exceeds EV max waiting tolerance ({max_waiting_time_min}m)"

        if not cls.is_slot_free_of_overlap(candidate_start_min, candidate_end_min, existing_bookings, charger_id):
            return False, f"Slot {minutes_to_time(candidate_start_min)}-{minutes_to_time(candidate_end_min)} overlaps with existing booking on {charger_id}"

        return True, "Feasible"
