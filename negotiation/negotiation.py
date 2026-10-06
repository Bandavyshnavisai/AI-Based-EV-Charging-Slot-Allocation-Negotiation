"""
Negotiation Protocol and Dialogue Management Module.

This module implements the multi-round alternating-offers negotiation protocol
between EV Agents and Charging Station Agents.
"""

from typing import Dict, Any, List, Optional
from enum import Enum


class NegotiationAction(str, Enum):
    PROPOSE = "PROPOSE"
    COUNTER_PROPOSE = "COUNTER_PROPOSE"
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    CONFIRM = "CONFIRM"
    TERMINATE = "TERMINATE"


class NegotiationSession:
    """
    Maintains dialogue state, offer rounds, and message exchanges for a negotiation session.
    """

    def __init__(self, request_id: str, ev_id: str, station_id: str, max_rounds: int = 3):
        self.request_id = request_id
        self.ev_id = ev_id
        self.station_id = station_id
        self.max_rounds = max_rounds
        self.current_round = 0
        self.history: List[Dict[str, Any]] = []
        self.status = "ACTIVE"  # ACTIVE, AGREED, REJECTED, TERMINATED
        self.agreed_slot: Optional[Dict[str, Any]] = None

    def record_step(
        self,
        sender: str,
        receiver: str,
        action: NegotiationAction,
        slot_details: Optional[Dict[str, Any]] = None,
        reason: str = ""
    ) -> Dict[str, Any]:
        """Records a dialogue exchange in the session history."""
        if action in [NegotiationAction.PROPOSE, NegotiationAction.COUNTER_PROPOSE]:
            self.current_round += 1

        entry = {
            "request_id": self.request_id,
            "round": self.current_round,
            "sender": sender,
            "receiver": receiver,
            "action": action.value,
            "slot": slot_details,
            "reason": reason
        }
        self.history.append(entry)

        if action == NegotiationAction.ACCEPT:
            self.status = "AGREED"
            self.agreed_slot = slot_details
        elif action == NegotiationAction.TERMINATE or (self.current_round >= self.max_rounds and action == NegotiationAction.REJECT):
            self.status = "TERMINATED"

        return entry

    def is_active(self) -> bool:
        """Returns True if negotiation is still open for proposals."""
        return self.status == "ACTIVE" and self.current_round <= self.max_rounds

    def has_exceeded_rounds(self) -> bool:
        """Returns True if round limit has been reached."""
        return self.current_round >= self.max_rounds
