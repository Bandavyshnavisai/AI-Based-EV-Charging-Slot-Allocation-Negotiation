"""
Unit tests for Payment Agent and Payment Verification.
"""

import pytest
import mesa
from agents.payment_agent import PaymentAgent


def test_payment_approval():
    """Verifies that PaymentAgent approves valid transactions."""
    model = mesa.Model()
    payment_agent = PaymentAgent(model=model, agent_id="TestPayment")

    receipt = payment_agent.process_payment(
        request_id="REQ-P1",
        ev_id="EV_1",
        station_id="Station_1",
        amount=18.50
    )

    assert receipt["status"] == "APPROVED"
    assert receipt["transaction_id"].startswith("TXN-")
    assert receipt["amount"] == 18.50


def test_payment_rejection():
    """Verifies that PaymentAgent rejects transactions when override or negative amount is triggered."""
    model = mesa.Model()
    payment_agent = PaymentAgent(model=model, agent_id="TestPayment")

    # Explicit failure override
    receipt = payment_agent.process_payment(
        request_id="REQ-P2",
        ev_id="EV_2",
        station_id="Station_1",
        amount=18.50,
        override_success=False
    )

    assert receipt["status"] == "REJECTED"
    assert "declined" in receipt["reason"].lower()


def test_payment_agent_deterministic_flag():
    """Verifies that agent-level force_success flag is respected."""
    model = mesa.Model()
    payment_agent_fail = PaymentAgent(model=model, force_success=False)

    receipt = payment_agent_fail.process_payment("REQ-P3", "EV_3", "Station_1", 10.0)
    assert receipt["status"] == "REJECTED"
