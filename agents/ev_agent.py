"""
Electric Vehicle (EV) Agent Module.

Implements the EVAgent representing autonomous electric vehicles in the Multi-Agent System.

PEAS Summary for EVAgent:
- Performance Measure: Minimized waiting time, reaching target battery level, minimized energy cost.
- Environment: Dynamic charging network, competing EVs, slot schedules, fluctuating station availability.
- Actuators: Send charging requests, evaluate proposals, send ACCEPT/REJECT messages, proceed to payment.
- Sensors: Current battery level (SOC), target SOC, clock/time, incoming station proposals, payment receipts.
"""

from typing import Dict, Any, Optional, List
import uuid
import mesa
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from negotiation.constraints import time_to_minutes
from negotiation.utility import UtilityCalculator
from negotiation.negotiation import NegotiationAction


class EVAgent(mesa.Agent):
    """
    Intelligent EV Agent that autonomously generates charging requests,
    evaluates station slot proposals, and negotiates terms based on utility.
    """

    def __init__(
        self,
        model: mesa.Model,
        ev_id: str,
        battery_level: float,
        required_battery_level: float = 80.0,
        preferred_time: str = "10:00",
        maximum_waiting_time: int = 60,
        priority: str = "HIGH",
        charging_duration: int = 60,
        battery_capacity_kwh: float = 75.0,
        min_acceptable_utility: float = 0.15,
        initial_utility_threshold: Optional[float] = None,
        concession_rate: float = 0.0
    ):
        super().__init__(model)
        self.ev_id = ev_id
        self.battery_level = max(0.0, min(100.0, float(battery_level)))
        self.required_battery_level = max(self.battery_level, min(100.0, float(required_battery_level)))
        self.preferred_time = preferred_time
        self.maximum_waiting_time = int(maximum_waiting_time)
        self.priority = priority.upper()
        self.charging_duration = int(charging_duration)
        self.battery_capacity_kwh = float(battery_capacity_kwh)
        self.min_acceptable_utility = float(min_acceptable_utility)
        self.initial_utility_threshold = float(initial_utility_threshold) if initial_utility_threshold is not None else None
        self.concession_rate = float(concession_rate)
        
        # State tracking
        self.status = "IDLE"  # IDLE, REQUESTING, NEGOTIATING, CONFIRMED, REJECTED, CHARGING, COMPLETED
        self.current_request_id: Optional[str] = None
        self.active_booking: Optional[Dict[str, Any]] = None
        self.negotiation_history: List[Dict[str, Any]] = []
        self.utility_calculator = UtilityCalculator()

    def generate_request(self) -> Dict[str, Any]:
        """
        Generates an autonomous charging request based on EV state and constraints.
        Does NOT assign a charger directly.
        """
        self.current_request_id = f"REQ-{self.ev_id}-{uuid.uuid4().hex[:6].upper()}"
        self.status = "REQUESTING"

        request = {
            "request_id": self.current_request_id,
            "ev_id": self.ev_id,
            "current_battery": self.battery_level,
            "required_battery": self.required_battery_level,
            "preferred_time": self.preferred_time,
            "duration_minutes": self.charging_duration,
            "max_waiting_time": self.maximum_waiting_time,
            "priority": self.priority,
            "battery_capacity_kwh": self.battery_capacity_kwh
        }

        if hasattr(self.model, "log_event"):
            self.model.log_event(
                sender=self.ev_id,
                receiver="SYSTEM",
                event_type="REQUEST_GENERATED",
                message=f"{self.ev_id} created charging request for {self.preferred_time} (duration: {self.charging_duration}m, battery: {self.battery_level}%, priority: {self.priority})"
            )

        return request

    def get_effective_threshold(self, round_num: int = 1) -> float:
        """
        Calculates the effective reservation threshold for a given negotiation round.
        Implements a generic concession strategy where the EV lowers its threshold in subsequent rounds.
        """
        if self.initial_utility_threshold is not None and self.concession_rate > 0:
            decay = (1.0 - self.concession_rate) ** (round_num - 1)
            return max(self.min_acceptable_utility, round(self.initial_utility_threshold * decay, 4))
        if self.initial_utility_threshold is not None:
            return self.initial_utility_threshold
        return self.min_acceptable_utility

    def evaluate_proposal(self, proposal: Dict[str, Any], round_num: int = 1) -> Dict[str, Any]:
        """
        Evaluates a charging slot proposal received from a Charging Station Agent.
        Applies utility function and concession rules to decide whether to ACCEPT or REJECT.
        """
        self.status = "NEGOTIATING"
        slot_start_str = proposal["start_time"]
        slot_start_min = time_to_minutes(slot_start_str)
        pref_min = time_to_minutes(self.preferred_time)
        
        waiting_time = slot_start_min - pref_min
        cost = proposal.get("total_cost", 15.0)

        # 1. Constraint Check: Is waiting time within acceptable patience limit?
        if waiting_time < 0:
            decision = NegotiationAction.REJECT
            reason = f"Proposed slot start ({slot_start_str}) is earlier than preferred arrival ({self.preferred_time})"
        elif waiting_time > self.maximum_waiting_time:
            decision = NegotiationAction.REJECT
            reason = f"Proposed delay ({waiting_time} min) exceeds maximum acceptable waiting time ({self.maximum_waiting_time} min)"
        else:
            # 2. Utility Evaluation: Does utility meet round effective acceptance threshold?
            utility = self.utility_calculator.evaluate_slot_utility(
                priority=self.priority,
                current_battery=self.battery_level,
                waiting_time_min=waiting_time,
                max_waiting_time_min=self.maximum_waiting_time,
                total_cost=cost
            )
            
            target_threshold = self.get_effective_threshold(round_num)
            
            if utility >= target_threshold:
                decision = NegotiationAction.ACCEPT
                reason = f"Proposed slot {slot_start_str}-{proposal['end_time']} accepted (utility: {utility:.3f} >= threshold: {target_threshold:.3f})"
            else:
                decision = NegotiationAction.REJECT
                reason = f"Utility {utility:.3f} is lower than reservation threshold {target_threshold:.3f} in round {round_num}"

        response = {
            "ev_id": self.ev_id,
            "request_id": proposal.get("request_id", self.current_request_id),
            "action": decision,
            "proposed_slot": proposal,
            "reason": reason
        }

        self.negotiation_history.append(response)

        if hasattr(self.model, "log_event"):
            self.model.log_event(
                sender=self.ev_id,
                receiver=proposal.get("station_id", "STATION"),
                event_type=f"PROPOSAL_{decision.value}",
                message=f"{self.ev_id} {decision.value}ED proposal for slot {slot_start_str}: {reason}"
            )

        return response

    def notify_confirmation(self, booking: Dict[str, Any]) -> None:
        """Called when reservation is confirmed following successful payment."""
        self.status = "CONFIRMED"
        self.active_booking = booking

    def notify_rejection(self, reason: str = "") -> None:
        """Called when request cannot be fulfilled or negotiation terminates without agreement."""
        self.status = "REJECTED"

    def step(self) -> None:
        """Mesa simulation step cycle for EVAgent."""
        # Simulated dynamic battery charge increment if charging
        if self.status == "CHARGING":
            self.battery_level = min(100.0, self.battery_level + 5.0)
            if self.battery_level >= self.required_battery_level:
                self.status = "COMPLETED"
