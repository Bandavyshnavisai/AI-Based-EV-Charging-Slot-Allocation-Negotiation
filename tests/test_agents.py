"""
Unit tests for EVAgent and ChargingStationAgent.
"""

import pytest
import mesa
from agents.ev_agent import EVAgent
from agents.charging_station_agent import ChargingStationAgent
from agents.payment_agent import PaymentAgent
from negotiation.negotiation import NegotiationAction


def test_ev_agent_generate_request():
    """Verifies that EVAgent constructs a well-formed charging request."""
    model = mesa.Model()
    ev = EVAgent(
        model=model,
        ev_id="EV_Test",
        battery_level=20.0,
        required_battery_level=80.0,
        preferred_time="10:00",
        maximum_waiting_time=45,
        priority="HIGH",
        charging_duration=60
    )

    req = ev.generate_request()
    assert req["ev_id"] == "EV_Test"
    assert req["current_battery"] == 20.0
    assert req["preferred_time"] == "10:00"
    assert req["duration_minutes"] == 60
    assert req["priority"] == "HIGH"
    assert ev.status == "REQUESTING"


def test_ev_agent_evaluate_acceptable_proposal():
    """Verifies that EVAgent accepts a proposal that satisfies patience and utility."""
    model = mesa.Model()
    ev = EVAgent(
        model=model,
        ev_id="EV_Test",
        battery_level=15.0,
        preferred_time="10:00",
        maximum_waiting_time=60,
        priority="HIGH"
    )
    ev.generate_request()

    proposal = {
        "start_time": "10:15",
        "end_time": "11:15",
        "total_cost": 15.0,
        "station_id": "Station_1"
    }

    response = ev.evaluate_proposal(proposal)
    assert response["action"] == NegotiationAction.ACCEPT
    assert "accepted" in response["reason"].lower()


def test_ev_agent_evaluate_unacceptable_proposal():
    """Verifies that EVAgent rejects a proposal that exceeds max waiting tolerance."""
    model = mesa.Model()
    ev = EVAgent(
        model=model,
        ev_id="EV_Test",
        battery_level=50.0,
        preferred_time="10:00",
        maximum_waiting_time=30,  # 30 min max wait
        priority="LOW"
    )
    ev.generate_request()

    # Proposal with 60 min delay
    proposal = {
        "start_time": "11:00",
        "end_time": "12:00",
        "total_cost": 15.0,
        "station_id": "Station_1"
    }

    response = ev.evaluate_proposal(proposal)
    assert response["action"] == NegotiationAction.REJECT
    assert "exceeds maximum acceptable waiting time" in response["reason"]
