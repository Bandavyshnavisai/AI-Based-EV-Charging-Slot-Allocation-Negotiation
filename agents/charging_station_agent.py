"""
Charging Station Agent Module.

Implements ChargingStationAgent responsible for autonomous charger resource allocation,
slot search, multi-round negotiation, and payment coordination.

PEAS Summary for ChargingStationAgent:
- Performance Measure: Maximized charger utilization, minimized queue waiting delay, high allocation throughput.
- Environment: Dynamic EV request streams, multiple physical chargers, finite operating horizon.
- Actuators: Run slot search engine, generate proposals/counter-proposals, place temporary hold, confirm/cancel bookings, trigger payment verification.
- Sensors: Charger availability status, current booking schedule, incoming EV requests, EV accept/reject replies, payment receipts.
"""

from typing import Dict, Any, List, Optional
import uuid
import mesa
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from negotiation.search import SlotSearchEngine
from negotiation.negotiation import NegotiationAction, NegotiationSession
from agents.payment_agent import PaymentAgent
from config import MAX_NEGOTIATION_ROUNDS, DEFAULT_BASE_PRICE_PER_KWH, DEFAULT_CHARGER_POWER_KW


class ChargingStationAgent(mesa.Agent):
    """
    Autonomous Charging Station Agent managing chargers, handling EV requests,
    performing heuristic search, executing negotiation protocols, and confirming reservations.
    """

    def __init__(
        self,
        model: mesa.Model,
        station_id: str,
        name: str = "Central Fast-Charge Station",
        num_chargers: int = 2,
        base_price_per_kwh: float = DEFAULT_BASE_PRICE_PER_KWH,
        charger_power_kw: float = DEFAULT_CHARGER_POWER_KW
    ):
        super().__init__(model)
        self.station_id = station_id
        self.name = name
        self.num_chargers = num_chargers
        self.base_price_per_kwh = base_price_per_kwh
        self.charger_power_kw = charger_power_kw

        # Initialize physical chargers
        self.chargers: List[Dict[str, Any]] = [
            {
                "charger_id": f"{self.station_id}_C{i+1}",
                "power_kw": charger_power_kw,
                "status": "AVAILABLE"
            }
            for i in range(num_chargers)
        ]

        self.current_bookings: List[Dict[str, Any]] = []
        self.waiting_queue: List[Dict[str, Any]] = []
        self.active_sessions: List[Dict[str, Any]] = []
        self.search_engine = SlotSearchEngine()
        self.active_negotiations: Dict[str, NegotiationSession] = {}

    def receive_request(
        self,
        ev_agent: Any,
        request: Dict[str, Any],
        payment_agent: PaymentAgent,
        force_payment_success: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Processes an incoming EV charging request through search, negotiation, and payment verification.
        Returns the final allocation outcome dictionary.
        """
        req_id = request["request_id"]
        ev_id = request["ev_id"]
        preferred_time = request["preferred_time"]
        duration = request["duration_minutes"]
        max_wait = request["max_waiting_time"]
        priority = request["priority"]
        current_battery = request["current_battery"]

        if hasattr(self.model, "log_event"):
            self.model.log_event(
                sender=ev_id,
                receiver=self.station_id,
                event_type="REQUEST_RECEIVED",
                message=f"{self.station_id} received charging request {req_id} from {ev_id} for {preferred_time}"
            )

        # 1. Search for all feasible candidate slots ranked by multi-attribute utility
        feasible_slots = self.search_engine.search_feasible_slots(
            station_id=self.station_id,
            chargers=self.chargers,
            existing_bookings=self.current_bookings,
            preferred_time_str=preferred_time,
            duration_minutes=duration,
            max_waiting_time_min=max_wait,
            priority=priority,
            current_battery=current_battery,
            base_price_per_kwh=self.base_price_per_kwh
        )

    def _log_negotiation_step(
        self,
        session: NegotiationSession,
        sender: str,
        receiver: str,
        action: NegotiationAction,
        slot_details: Optional[Dict[str, Any]] = None,
        reason: str = ""
    ) -> Dict[str, Any]:
        """Records a negotiation step in memory and persists it to the SQLite database."""
        step_entry = session.record_step(
            sender=sender,
            receiver=receiver,
            action=action,
            slot_details=slot_details,
            reason=reason
        )
        if hasattr(self.model, "db") and self.model.db:
            st_id = slot_details.get("station_id", self.station_id) if slot_details else self.station_id
            ch_id = slot_details.get("charger_id") if slot_details else None
            start_t = slot_details.get("start_time") if slot_details else None
            end_t = slot_details.get("end_time") if slot_details else None
            self.model.db.log_negotiation(
                request_id=session.request_id,
                round_num=session.current_round,
                sender=sender,
                receiver=receiver,
                proposed_station_id=st_id,
                proposed_charger_id=ch_id,
                proposed_slot_start=start_t,
                proposed_slot_end=end_t,
                action=action.value,
                reason=reason
            )
        return step_entry

    def receive_request(
        self,
        ev_agent: Any,
        request: Dict[str, Any],
        payment_agent: PaymentAgent,
        force_payment_success: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Processes an incoming EV charging request through search, negotiation, and payment verification.
        Returns the final allocation outcome dictionary.
        """
        req_id = request["request_id"]
        ev_id = request["ev_id"]
        preferred_time = request["preferred_time"]
        duration = request["duration_minutes"]
        max_wait = request["max_waiting_time"]
        priority = request["priority"]
        current_battery = request["current_battery"]

        if hasattr(self.model, "log_event"):
            self.model.log_event(
                sender=ev_id,
                receiver=self.station_id,
                event_type="REQUEST_RECEIVED",
                message=f"{self.station_id} received charging request {req_id} from {ev_id} for {preferred_time}"
            )

        # 1. Search for all feasible candidate slots ranked by multi-attribute utility
        feasible_slots = self.search_engine.search_feasible_slots(
            station_id=self.station_id,
            chargers=self.chargers,
            existing_bookings=self.current_bookings,
            preferred_time_str=preferred_time,
            duration_minutes=duration,
            max_waiting_time_min=max_wait,
            priority=priority,
            current_battery=current_battery,
            base_price_per_kwh=self.base_price_per_kwh
        )

        # Initialize negotiation session
        session = NegotiationSession(
            request_id=req_id,
            ev_id=ev_id,
            station_id=self.station_id,
            max_rounds=MAX_NEGOTIATION_ROUNDS
        )
        self.active_negotiations[req_id] = session

        if not feasible_slots:
            # No feasible slot satisfies constraints
            reason = f"No available charger slots at {self.station_id} satisfy waiting tolerance of {max_wait} mins for {preferred_time}"
            self._log_negotiation_step(
                session=session,
                sender=self.station_id,
                receiver=ev_id,
                action=NegotiationAction.TERMINATE,
                reason=reason
            )
            ev_agent.notify_rejection(reason)
            
            if hasattr(self.model, "log_event"):
                self.model.log_event(
                    sender=self.station_id,
                    receiver=ev_id,
                    event_type="NO_FEASIBLE_SLOT",
                    message=f"{self.station_id} could not find feasible slots for {ev_id}: {reason}"
                )
            return {
                "request_id": req_id,
                "status": "REJECTED",
                "reason": reason,
                "negotiation_rounds": 0,
                "booking": None
            }

        # Check if requested preferred slot (delay = 0) is available in feasible slots
        has_preferred_slot = any(s.get("waiting_time_minutes", 0) == 0 for s in feasible_slots)
        if not has_preferred_slot:
            if hasattr(self.model, "log_event"):
                self.model.log_event(
                    sender=self.station_id,
                    receiver=ev_id,
                    event_type="SLOT_UNAVAILABLE",
                    message=f"Requested slot {preferred_time} at {self.station_id} is unavailable."
                )

        # 2. Multi-Round Negotiation Loop
        slot_index = 0
        while session.is_active() and slot_index < len(feasible_slots):
            candidate_slot = feasible_slots[slot_index]
            candidate_slot["request_id"] = req_id
            
            is_counter_proposal = not (session.current_round == 0 and has_preferred_slot and candidate_slot.get("waiting_time_minutes", 0) == 0)
            
            if hasattr(self.model, "log_event") and is_counter_proposal:
                self.model.log_event(
                    sender=self.station_id,
                    receiver=ev_id,
                    event_type="ALTERNATIVE_SEARCH",
                    message=f"{self.station_id} searching for alternative charging slots."
                )

            action_type = NegotiationAction.COUNTER_PROPOSE if is_counter_proposal else NegotiationAction.PROPOSE
            event_type = "COUNTER_PROPOSAL" if is_counter_proposal else "SLOT_PROPOSAL"

            self._log_negotiation_step(
                session=session,
                sender=self.station_id,
                receiver=ev_id,
                action=action_type,
                slot_details=candidate_slot,
                reason=f"Offering slot {candidate_slot['start_time']}-{candidate_slot['end_time']} (Utility: {candidate_slot['utility_score']})"
            )

            if hasattr(self.model, "log_event") and is_counter_proposal:
                self.model.log_event(
                    sender=self.station_id,
                    receiver=ev_id,
                    event_type=event_type,
                    message=f"{self.station_id} proposed alternative slot {candidate_slot['start_time']}-{candidate_slot['end_time']} to {ev_id} (Round {session.current_round})"
                )

            # EV evaluates proposal
            ev_response = ev_agent.evaluate_proposal(candidate_slot, round_num=session.current_round)
            self._log_negotiation_step(
                session=session,
                sender=ev_id,
                receiver=self.station_id,
                action=ev_response["action"],
                slot_details=candidate_slot,
                reason=ev_response["reason"]
            )

            if ev_response["action"] == NegotiationAction.ACCEPT:
                # 3. Two-Phase Reservation & Payment Verification
                total_cost = candidate_slot["total_cost"]
                
                if hasattr(self.model, "log_event"):
                    self.model.log_event(
                        sender=self.station_id,
                        receiver=payment_agent.agent_id,
                        event_type="PAYMENT_REQUESTED",
                        message=f"{self.station_id} requesting payment authorization of ${total_cost:.2f} for {ev_id}"
                    )

                payment_receipt = payment_agent.process_payment(
                    request_id=req_id,
                    ev_id=ev_id,
                    station_id=self.station_id,
                    amount=total_cost,
                    override_success=force_payment_success
                )

                if payment_receipt["status"] == "APPROVED":
                    # Payment Success -> Finalize Booking
                    booking_id = f"BK-{uuid.uuid4().hex[:8].upper()}"
                    booking = {
                        "booking_id": booking_id,
                        "request_id": req_id,
                        "ev_id": ev_id,
                        "station_id": self.station_id,
                        "charger_id": candidate_slot["charger_id"],
                        "start_time": candidate_slot["start_time"],
                        "end_time": candidate_slot["end_time"],
                        "duration_minutes": duration,
                        "total_cost": total_cost,
                        "payment_status": "APPROVED",
                        "status": "CONFIRMED"
                    }
                    self.current_bookings.append(booking)
                    ev_agent.notify_confirmation(booking)

                    # Persist booking and negotiation to model database if available
                    if hasattr(self.model, "db") and self.model.db:
                        self.model.db.create_booking(
                            booking_id=booking_id,
                            request_id=req_id,
                            ev_id=ev_id,
                            station_id=self.station_id,
                            charger_id=candidate_slot["charger_id"],
                            start_time=candidate_slot["start_time"],
                            end_time=candidate_slot["end_time"],
                            duration_minutes=duration,
                            total_cost=total_cost,
                            payment_status="APPROVED",
                            status="CONFIRMED"
                        )
                        self.model.db.update_request_status(req_id, "CONFIRMED")

                    if hasattr(self.model, "log_event"):
                        self.model.log_event(
                            sender=self.station_id,
                            receiver=ev_id,
                            event_type="RESERVATION_CONFIRMED",
                            message=f"Reservation {booking_id} confirmed for {ev_id} on {candidate_slot['charger_id']} at {candidate_slot['start_time']}-{candidate_slot['end_time']}"
                        )

                    return {
                        "request_id": req_id,
                        "status": "CONFIRMED",
                        "booking": booking,
                        "negotiation_rounds": session.current_round,
                        "negotiation_history": session.history
                    }
                else:
                    # Payment Failed -> Rollback hold and terminate reservation
                    reason = f"Payment authorization failed: {payment_receipt['reason']}"
                    ev_agent.notify_rejection(reason)
                    
                    if hasattr(self.model, "db") and self.model.db:
                        self.model.db.update_request_status(req_id, "PAYMENT_FAILED")

                    if hasattr(self.model, "log_event"):
                        self.model.log_event(
                            sender=self.station_id,
                            receiver=ev_id,
                            event_type="RESERVATION_FAILED",
                            message=f"Reservation aborted for {ev_id}: {reason}. Slot {candidate_slot['start_time']} released."
                        )

                    return {
                        "request_id": req_id,
                        "status": "PAYMENT_FAILED",
                        "reason": reason,
                        "booking": None,
                        "negotiation_rounds": session.current_round,
                        "negotiation_history": session.history
                    }

            # EV rejected this proposal -> Move to next feasible alternative for counter-proposal
            slot_index += 1

        # Reached max rounds or exhausted all feasible slots without agreement
        fail_reason = "Negotiation reached maximum rounds without agreement" if session.has_exceeded_rounds() else "All alternative slot proposals were rejected"
        self._log_negotiation_step(
            session=session,
            sender=self.station_id,
            receiver=ev_id,
            action=NegotiationAction.TERMINATE,
            reason=fail_reason
        )
        ev_agent.notify_rejection(fail_reason)

        if hasattr(self.model, "db") and self.model.db:
            self.model.db.update_request_status(req_id, "NEGOTIATION_FAILED")

        if hasattr(self.model, "log_event"):
            self.model.log_event(
                sender=self.station_id,
                receiver=ev_id,
                event_type="NEGOTIATION_FAILED",
                message=f"Negotiation between {self.station_id} and {ev_id} concluded with no agreement: {fail_reason}"
            )

        return {
            "request_id": req_id,
            "status": "NEGOTIATION_FAILED",
            "reason": fail_reason,
            "booking": None,
            "negotiation_rounds": session.current_round,
            "negotiation_history": session.history
        }

    def step(self) -> None:
        """Mesa simulation cycle for station operations and queue management."""
        pass
