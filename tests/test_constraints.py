"""
Unit tests for Constraint Checking and Rule Verification.
"""

import pytest
from negotiation.constraints import (
    time_to_minutes,
    minutes_to_time,
    intervals_overlap,
    SlotConstraintChecker,
)


def test_time_conversions():
    """Tests time string to minutes and reverse conversions."""
    assert time_to_minutes("00:00") == 0
    assert time_to_minutes("08:30") == 510
    assert time_to_minutes("23:59") == 1439
    assert minutes_to_time(510) == "08:30"
    assert minutes_to_time(0) == "00:00"


def test_intervals_overlap():
    """Tests temporal interval overlap logic."""
    # [10:00 - 11:00] (600 - 660) and [10:30 - 11:30] (630 - 690) overlap
    assert intervals_overlap(600, 660, 630, 690) is True
    # [10:00 - 11:00] and [11:00 - 12:00] do not overlap (boundary touching)
    assert intervals_overlap(600, 660, 660, 720) is False
    # Disjoint intervals
    assert intervals_overlap(600, 660, 700, 760) is False


def test_slot_constraint_checker():
    """Tests SlotConstraintChecker methods for charger status, waiting tolerance, and overlap."""
    checker = SlotConstraintChecker()
    
    # Charger availability
    assert checker.is_charger_available("AVAILABLE") is True
    assert checker.is_charger_available("OFFLINE") is False
    assert checker.is_charger_available("MAINTENANCE") is False

    # Duration satisfaction
    assert checker.is_duration_satisfied(60, 45) is True
    assert checker.is_duration_satisfied(30, 45) is False

    # Waiting tolerance
    assert checker.is_within_max_waiting_time(600, 630, 45) is True
    assert checker.is_within_max_waiting_time(600, 660, 45) is False  # 60m delay > 45m tolerance
    assert checker.is_within_max_waiting_time(600, 580, 45) is False  # Negative delay (earlier than arrival)
