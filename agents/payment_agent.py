"""
Payment Agent Module.

Implements the PaymentAgent responsible for financial authorization and
transaction verification for EV charging reservations.

PEAS Summary for PaymentAgent:
- Performance Measure: Transaction accuracy, validation speed, fraud/failure handling
- Environment: Charging station payment requests, simulated banking ledger
- Actuators: Return APPROVED/REJECTED tokens, record transaction ledger
- Sensors: Incoming payment verification requests with amount and booking ID
"""

from typing import Dict, Any, Optional
import uuid
import mesa


class PaymentAgent(mesa.Agent):
    """
    Autonomous Payment Agent responsible for verifying and approving/rejecting
    charging slot payments before reservations are confirmed.
    """

    def __init__(self, model: mesa.Model, agent_id: str = "PaymentAgent_1", force_success: Optional[bool] = None):
        super().__init__(model)
        self.agent_id = agent_id
        self.force_success = force_success  # Used for deterministic testing of failure scenarios
        self.transaction_history: Dict[str, Dict[str, Any]] = {}

    def process_payment(
        self,
        request_id: str,
        ev_id: str,
        station_id: str,
        amount: float,
        override_success: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Evaluates and processes a payment request.
        Returns an approval or rejection receipt.
        """
        # Determine approval: use override if specified, else agent default, else succeed for valid amount > 0
        should_succeed = True
        if override_success is not None:
            should_succeed = override_success
        elif self.force_success is not None:
            should_succeed = self.force_success
        else:
            should_succeed = amount > 0

        transaction_id = f"TXN-{uuid.uuid4().hex[:8].upper()}"
        status = "APPROVED" if should_succeed else "REJECTED"
        reason = "Payment verified successfully" if should_succeed else "Payment authorization declined by issuer"

        receipt = {
            "transaction_id": transaction_id,
            "request_id": request_id,
            "ev_id": ev_id,
            "station_id": station_id,
            "amount": amount,
            "status": status,
            "reason": reason
        }

        self.transaction_history[transaction_id] = receipt
        
        # Log to event bus if model supports it
        if hasattr(self.model, "log_event"):
            self.model.log_event(
                sender=self.agent_id,
                receiver=station_id,
                event_type=f"PAYMENT_{status}",
                message=f"Payment of ${amount:.2f} for {ev_id} was {status} ({transaction_id})"
            )

        return receipt

    def step(self) -> None:
        """Periodic maintenance / ledger synchronization step for Mesa cycle."""
        pass
