"""
Integration Test Suite for Core AI EV Charging Scenarios (Rubric Tests 1 - 8).

TEST 1: Normal slot allocation (EV requests available slot -> Allocated)
TEST 2: Slot conflict (Two EVs request same slot -> One allocated, other negotiated)
TEST 3: Battery priority (EV1 battery 10% vs EV2 battery 70% -> EV1 prioritized)
TEST 4: Negotiation acceptance (Requested slot busy -> Counter proposal -> Accepted -> Confirmed)
TEST 5: Negotiation rejection (EV rejects first alternative -> Station searches next -> Handled)
TEST 6: Payment failure (Slot selected -> Payment rejected -> Slot freed & Request failed)
TEST 7: No feasible slot (Constraints violated -> Informative rejection explanation)
TEST 8: Multiple EVs (4-5 simultaneous EVs -> Handled gracefully without crash)
"""

import pytest
from environment.charging_model import ChargingModel
from database.database import DatabaseManager


def test_scenario_1_normal_slot_allocation():
    """TEST 1: Normal slot allocation when preferred charger slot is free."""
    model = ChargingModel(db_path=":memory:")
    station = model.add_station("Station_1", "GreenPoint", num_chargers=1, base_price_per_kwh=0.25)
    ev = model.add_ev("EV1", battery_level=20.0, preferred_time="10:00", maximum_waiting_time=60, priority="HIGH", charging_duration=60)

    results = model.run_allocation_cycle()
    assert len(results) == 1
    outcome = results[0]["outcome"]
    
    assert outcome["status"] == "CONFIRMED"
    assert outcome["booking"]["start_time"] == "10:00"
    assert outcome["booking"]["end_time"] == "11:00"
    assert outcome["booking"]["payment_status"] == "APPROVED"
    assert ev.status == "CONFIRMED"


def test_scenario_2_slot_conflict():
    """TEST 2: Slot conflict between two EVs requesting the exact same slot."""
    model = ChargingModel(db_path=":memory:")
    station = model.add_station("Station_1", "Metro Hub", num_chargers=1, base_price_per_kwh=0.25)
    
    # EV1: Higher priority & lower battery -> Gets 10:00
    ev1 = model.add_ev("EV1", battery_level=15.0, preferred_time="10:00", maximum_waiting_time=60, priority="HIGH", charging_duration=60)
    # EV2: Lower priority -> Receives counter-proposal for 11:00
    ev2 = model.add_ev("EV2", battery_level=50.0, preferred_time="10:00", maximum_waiting_time=90, priority="MEDIUM", charging_duration=45)

    results = model.run_allocation_cycle()
    assert len(results) == 2

    res_ev1 = next(r for r in results if r["ev_id"] == "EV1")
    res_ev2 = next(r for r in results if r["ev_id"] == "EV2")

    assert res_ev1["outcome"]["status"] == "CONFIRMED"
    assert res_ev1["outcome"]["booking"]["start_time"] == "10:00"

    assert res_ev2["outcome"]["status"] == "CONFIRMED"
    assert res_ev2["outcome"]["booking"]["start_time"] == "11:00"


def test_scenario_3_battery_priority():
    """TEST 3: Low battery (10%) emergency EV is prioritized over high battery (70%) EV."""
    model = ChargingModel(db_path=":memory:")
    station = model.add_station("Station_1", "Solo Charger Point", num_chargers=1, base_price_per_kwh=0.25)

    ev_urgent = model.add_ev("EV_Urgent", battery_level=10.0, preferred_time="10:00", maximum_waiting_time=30, priority="HIGH", charging_duration=60)
    ev_normal = model.add_ev("EV_Normal", battery_level=70.0, preferred_time="10:00", maximum_waiting_time=60, priority="HIGH", charging_duration=30)

    results = model.run_allocation_cycle()
    res_urgent = next(r for r in results if r["ev_id"] == "EV_Urgent")
    res_normal = next(r for r in results if r["ev_id"] == "EV_Normal")

    # Urgent EV gets the initial 10:00 slot
    assert res_urgent["outcome"]["status"] == "CONFIRMED"
    assert res_urgent["outcome"]["booking"]["start_time"] == "10:00"
    
    # Normal EV gets the subsequent 11:00 slot
    assert res_normal["outcome"]["status"] == "CONFIRMED"
    assert res_normal["outcome"]["booking"]["start_time"] == "11:00"


def test_scenario_4_negotiation_acceptance():
    """TEST 4: Requested slot busy -> Station counter-proposes 10:30 (rejected) -> Station counter-proposes 10:45 (accepted) -> Confirmed in 2 rounds."""
    model = ChargingModel(db_path=":memory:")
    station = model.add_station("Station_1", "Downtown Hub", num_chargers=1, base_price_per_kwh=0.25)
    
    # Pre-book 10:00-10:30
    station.current_bookings.append({
        "booking_id": "BK-EXISTING",
        "request_id": "REQ-PRE",
        "ev_id": "EV_Pre",
        "station_id": "Station_1",
        "charger_id": "Station_1_C1",
        "start_time": "10:00",
        "end_time": "10:30",
        "duration_minutes": 30,
        "total_cost": 7.50,
        "payment_status": "APPROVED",
        "status": "CONFIRMED"
    })

    ev = model.add_ev(
        ev_id="EV_Negotiator",
        battery_level=30.0,
        preferred_time="10:00",
        maximum_waiting_time=90,
        priority="HIGH",
        charging_duration=45,
        initial_utility_threshold=0.55,
        concession_rate=0.35,
        min_acceptable_utility=0.15
    )

    results = model.run_allocation_cycle()
    outcome = results[0]["outcome"]

    assert outcome["status"] == "CONFIRMED"
    assert outcome["booking"]["start_time"] == "10:45"
    assert outcome["negotiation_rounds"] == 2


def test_scenario_5_negotiation_rejection():
    """TEST 5: EV rejects first alternative that violates patience; station terminates cleanly."""
    model = ChargingModel(db_path=":memory:")
    station = model.add_station("Station_1", "Depot", num_chargers=1, base_price_per_kwh=0.25)
    
    # Pre-book 10:00-12:00
    station.current_bookings.append({
        "booking_id": "BK-EXISTING",
        "request_id": "REQ-PRE",
        "ev_id": "EV_Pre",
        "station_id": "Station_1",
        "charger_id": "Station_1_C1",
        "start_time": "10:00",
        "end_time": "12:00",
        "duration_minutes": 120,
        "total_cost": 30.0,
        "payment_status": "APPROVED",
        "status": "CONFIRMED"
    })

    # EV has only 30 mins max wait tolerance (cannot take 12:00 slot)
    ev = model.add_ev("EV_Strict", battery_level=40.0, preferred_time="10:00", maximum_waiting_time=30, priority="LOW", charging_duration=45)

    results = model.run_allocation_cycle()
    outcome = results[0]["outcome"]

    assert outcome["status"] in ["REJECTED", "NEGOTIATION_FAILED"]
    assert ev.status == "REJECTED"


def test_scenario_6_payment_failure():
    """TEST 6: Payment failure rollbacks reservation and frees charger slot."""
    model = ChargingModel(db_path=":memory:")
    station = model.add_station("Station_1", "Secure Hub", num_chargers=1, base_price_per_kwh=0.25)
    ev = model.add_ev("EV_FailedPay", battery_level=20.0, preferred_time="10:00", maximum_waiting_time=60, priority="HIGH", charging_duration=60)

    # Force payment failure
    results = model.run_allocation_cycle(payment_override_map={"EV_FailedPay": False})
    outcome = results[0]["outcome"]

    assert outcome["status"] == "PAYMENT_FAILED"
    assert len(station.current_bookings) == 0  # Slot was not booked
    assert ev.status == "REJECTED"


def test_scenario_7_no_feasible_slot():
    """TEST 7: No feasible slot satisfies constraints -> Informative rejection explanation."""
    model = ChargingModel(db_path=":memory:")
    station = model.add_station("Station_1", "Busy Station", num_chargers=1, base_price_per_kwh=0.25)
    
    # Pre-book whole morning
    station.current_bookings.append({
        "booking_id": "BK-ALLDAY",
        "request_id": "REQ-ALL",
        "ev_id": "EV_AllDay",
        "station_id": "Station_1",
        "charger_id": "Station_1_C1",
        "start_time": "08:00",
        "end_time": "14:00",
        "duration_minutes": 360,
        "total_cost": 90.0,
        "payment_status": "APPROVED",
        "status": "CONFIRMED"
    })

    # EV wants 10:00 with 0 max wait tolerance
    ev = model.add_ev("EV_Impatient", battery_level=50.0, preferred_time="10:00", maximum_waiting_time=0, priority="MEDIUM", charging_duration=60)

    results = model.run_allocation_cycle()
    outcome = results[0]["outcome"]

    assert outcome["status"] in ["REJECTED", "NEGOTIATION_FAILED"]
    assert "no available charger slots" in outcome["reason"].lower() or "tolerance" in outcome["reason"].lower()


def test_scenario_8_multiple_evs_concurrency():
    """TEST 8: 5 simultaneous EV agents requesting slots across 2 stations (4 chargers)."""
    model = ChargingModel(db_path=":memory:")
    model.add_station("Station_A", "Alpha Hub", num_chargers=2, base_price_per_kwh=0.28)
    model.add_station("Station_B", "Beta Hub", num_chargers=2, base_price_per_kwh=0.22)

    ev_list = [
        model.add_ev("EV_1", battery_level=12.0, preferred_time="09:00", maximum_waiting_time=60, priority="CRITICAL", charging_duration=60),
        model.add_ev("EV_2", battery_level=30.0, preferred_time="09:00", maximum_waiting_time=45, priority="HIGH", charging_duration=45),
        model.add_ev("EV_3", battery_level=60.0, preferred_time="09:30", maximum_waiting_time=30, priority="MEDIUM", charging_duration=30),
        model.add_ev("EV_4", battery_level=45.0, preferred_time="10:00", maximum_waiting_time=60, priority="MEDIUM", charging_duration=60),
        model.add_ev("EV_5", battery_level=15.0, preferred_time="10:00", maximum_waiting_time=90, priority="HIGH", charging_duration=45),
    ]

    results = model.run_allocation_cycle()
    assert len(results) == 5

    metrics = model.get_metrics()
    assert metrics["total_requests"] == 5
    assert metrics["confirmed_allocations"] >= 4
    assert metrics["allocation_success_rate_pct"] > 70.0
