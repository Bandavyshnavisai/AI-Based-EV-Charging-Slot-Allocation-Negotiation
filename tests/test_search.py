"""
Unit tests for Search Strategy and Heuristic Ranking.
"""

import pytest
from negotiation.search import SlotSearchEngine
from negotiation.utility import UtilityCalculator


def test_search_feasible_slots_empty_schedule():
    """Verifies that search returns multiple ordered candidate slots when charger is completely free."""
    engine = SlotSearchEngine()
    chargers = [{"charger_id": "C1", "power_kw": 50.0, "status": "AVAILABLE"}]
    existing_bookings = []

    results = engine.search_feasible_slots(
        station_id="Station_1",
        chargers=chargers,
        existing_bookings=existing_bookings,
        preferred_time_str="10:00",
        duration_minutes=60,
        max_waiting_time_min=60,
        priority="HIGH",
        current_battery=20.0,
        base_price_per_kwh=0.25
    )

    assert len(results) > 0
    # First slot should start at 10:00 with 0 waiting time
    assert results[0]["start_time"] == "10:00"
    assert results[0]["waiting_time_minutes"] == 0
    assert results[0]["utility_score"] >= results[-1]["utility_score"]


def test_search_skips_occupied_slots():
    """Verifies that search skips booked intervals and returns the next free slot."""
    engine = SlotSearchEngine()
    chargers = [{"charger_id": "C1", "power_kw": 50.0, "status": "AVAILABLE"}]
    existing_bookings = [{
        "charger_id": "C1",
        "start_time": "10:00",
        "end_time": "11:00",
        "status": "CONFIRMED",
        "payment_status": "APPROVED"
    }]

    results = engine.search_feasible_slots(
        station_id="Station_1",
        chargers=chargers,
        existing_bookings=existing_bookings,
        preferred_time_str="10:00",
        duration_minutes=30,
        max_waiting_time_min=90,
        priority="MEDIUM",
        current_battery=40.0
    )

    # First feasible slot should start at 11:00
    assert len(results) > 0
    assert results[0]["start_time"] == "11:00"
    assert results[0]["waiting_time_minutes"] == 60


def test_search_no_slots_if_waiting_time_exceeded():
    """Verifies that search returns empty list when no slot is available within max waiting tolerance."""
    engine = SlotSearchEngine()
    chargers = [{"charger_id": "C1", "power_kw": 50.0, "status": "AVAILABLE"}]
    existing_bookings = [{
        "charger_id": "C1",
        "start_time": "10:00",
        "end_time": "12:00",
        "status": "CONFIRMED",
        "payment_status": "APPROVED"
    }]

    results = engine.search_feasible_slots(
        station_id="Station_1",
        chargers=chargers,
        existing_bookings=existing_bookings,
        preferred_time_str="10:00",
        duration_minutes=60,
        max_waiting_time_min=30,  # Max wait is 30 mins, but next slot is at 12:00 (120 mins delay)
        priority="LOW",
        current_battery=60.0
    )

    assert len(results) == 0
