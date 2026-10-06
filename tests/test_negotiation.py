"""
Unit tests for Negotiation Protocol, Sessions, and Utility Evaluation.
"""

import pytest
from negotiation.negotiation import NegotiationSession, NegotiationAction
from negotiation.utility import UtilityCalculator


def test_negotiation_session_tracking():
    """Tests negotiation state transitions across multiple rounds."""
    session = NegotiationSession(request_id="REQ-TEST", ev_id="EV1", station_id="Station1", max_rounds=3)
    assert session.is_active() is True
    assert session.current_round == 0

    # Round 1: Propose
    session.record_step("Station1", "EV1", NegotiationAction.PROPOSE, {"start_time": "10:00"}, "Initial offer")
    assert session.current_round == 1

    # EV rejects round 1
    session.record_step("EV1", "Station1", NegotiationAction.REJECT, reason="Delay too high")
    assert session.is_active() is True

    # Round 2: Counter Propose
    session.record_step("Station1", "EV1", NegotiationAction.COUNTER_PROPOSE, {"start_time": "10:30"}, "Alternative slot")
    assert session.current_round == 2

    # EV accepts round 2
    session.record_step("EV1", "Station1", NegotiationAction.ACCEPT, {"start_time": "10:30"}, "Accepted")
    assert session.status == "AGREED"
    assert session.agreed_slot["start_time"] == "10:30"


def test_negotiation_max_rounds_termination():
    """Tests that negotiation terminates once max rounds is exceeded."""
    session = NegotiationSession(request_id="REQ-MAX", ev_id="EV2", station_id="Station1", max_rounds=2)

    # Round 1
    session.record_step("Station1", "EV2", NegotiationAction.PROPOSE, {"start_time": "10:00"})
    session.record_step("EV2", "Station1", NegotiationAction.REJECT, reason="Reject 1")
    assert session.is_active() is True

    # Round 2
    session.record_step("Station1", "EV2", NegotiationAction.COUNTER_PROPOSE, {"start_time": "10:30"})
    session.record_step("EV2", "Station1", NegotiationAction.REJECT, reason="Reject 2")
    
    assert session.status == "TERMINATED"
    assert session.is_active() is False


def test_utility_calculator():
    """Tests multi-attribute utility calculation with different urgency and priorities."""
    calc = UtilityCalculator()

    # High priority + low battery + zero delay
    u_high = calc.evaluate_slot_utility(
        priority="HIGH",
        current_battery=10.0,
        waiting_time_min=0,
        max_waiting_time_min=60,
        total_cost=15.0
    )

    # Low priority + high battery + high delay
    u_low = calc.evaluate_slot_utility(
        priority="LOW",
        current_battery=80.0,
        waiting_time_min=60,
        max_waiting_time_min=60,
        total_cost=15.0
    )

    assert u_high > u_low
