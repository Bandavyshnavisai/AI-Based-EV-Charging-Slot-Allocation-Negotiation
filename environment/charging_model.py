"""
Multi-Agent Simulation Environment Model.

Implements the Mesa ChargingModel managing the multi-agent ecosystem of
EV Agents, Charging Station Agents, and the Payment Agent.
"""

from typing import List, Dict, Any, Optional
import datetime
import mesa
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.ev_agent import EVAgent
from agents.charging_station_agent import ChargingStationAgent
from agents.payment_agent import PaymentAgent
from database.database import DatabaseManager
from negotiation.constraints import time_to_minutes
from config import DEFAULT_DB_PATH, PRIORITY_SCORES


class ChargingModel(mesa.Model):
    """
    Mesa Simulation Model for AI-Based EV Charging Slot Allocation & Negotiation.
    Coordinates agents, handles event dispatching, and tracks performance metrics.
    """

    def __init__(
        self,
        db_path: str = DEFAULT_DB_PATH,
        seed: Optional[int] = None,
        auto_init_default_scenario: bool = False
    ):
        super().__init__(seed=seed)
        self.db = DatabaseManager(db_path=db_path)
        self.db.reset_database()
        
        self.simulation_step = 0
        self.current_time_str = "08:00"
        self.events: List[Dict[str, Any]] = []
        
        # Dedicated agent references for rapid lookup
        self.ev_agents: List[EVAgent] = []
        self.station_agents: List[ChargingStationAgent] = []
        self.payment_agent = PaymentAgent(model=self, agent_id="PaymentAgent_Central")

        if auto_init_default_scenario:
            self.setup_default_agents()

    def log_event(self, sender: str, receiver: str, event_type: str, message: str) -> None:
        """Centralized logging system for capturing real-time multi-agent communication."""
        timestamp = self.current_time_str
        event_dict = {
            "step": self.simulation_step,
            "timestamp": timestamp,
            "sender": sender,
            "receiver": receiver,
            "event_type": event_type,
            "message": message
        }
        self.events.append(event_dict)
        
        if self.db:
            self.db.log_event(
                simulation_step=self.simulation_step,
                timestamp=timestamp,
                sender=sender,
                receiver=receiver,
                event_type=event_type,
                message=message
            )

    def add_station(
        self,
        station_id: str,
        name: str = "Station Hub",
        num_chargers: int = 2,
        base_price_per_kwh: float = 0.25,
        charger_power_kw: float = 50.0
    ) -> ChargingStationAgent:
        """Instantiates and registers a new ChargingStationAgent."""
        station = ChargingStationAgent(
            model=self,
            station_id=station_id,
            name=name,
            num_chargers=num_chargers,
            base_price_per_kwh=base_price_per_kwh,
            charger_power_kw=charger_power_kw
        )
        self.station_agents.append(station)
        
        # Persist to database
        if self.db:
            self.db.insert_station(station_id, name, "Grid Area A", num_chargers, base_price_per_kwh)
            for c in station.chargers:
                self.db.insert_charger(c["charger_id"], station_id, charger_power_kw, "AVAILABLE")

        self.log_event("SYSTEM", station_id, "STATION_REGISTERED", f"Station {station_id} ({num_chargers} chargers) registered.")
        return station

    def add_ev(
        self,
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
    ) -> EVAgent:
        """Instantiates and registers a new EVAgent."""
        ev = EVAgent(
            model=self,
            ev_id=ev_id,
            battery_level=battery_level,
            required_battery_level=required_battery_level,
            preferred_time=preferred_time,
            maximum_waiting_time=maximum_waiting_time,
            priority=priority,
            charging_duration=charging_duration,
            battery_capacity_kwh=battery_capacity_kwh,
            min_acceptable_utility=min_acceptable_utility,
            initial_utility_threshold=initial_utility_threshold,
            concession_rate=concession_rate
        )
        self.ev_agents.append(ev)

        # Persist to database
        if self.db:
            self.db.insert_ev(ev_id, battery_capacity_kwh, battery_level, required_battery_level, priority, maximum_waiting_time)

        self.log_event("SYSTEM", ev_id, "EV_REGISTERED", f"EV {ev_id} registered (Battery: {battery_level}%, Priority: {priority}, Pref: {preferred_time}).")
        return ev

    def setup_default_agents(self) -> None:
        """Initializes standard default demo topology with 2 stations and 4 EVs."""
        self.add_station(station_id="Station_Downtown", name="Downtown Fast Hub", num_chargers=2, base_price_per_kwh=0.30)
        self.add_station(station_id="Station_Uptown", name="Uptown Eco Charge", num_chargers=2, base_price_per_kwh=0.22)

        self.add_ev(ev_id="EV_1", battery_level=15.0, required_battery_level=80.0, preferred_time="10:00", maximum_waiting_time=60, priority="HIGH", charging_duration=60)
        self.add_ev(ev_id="EV_2", battery_level=25.0, required_battery_level=85.0, preferred_time="10:00", maximum_waiting_time=45, priority="MEDIUM", charging_duration=45)
        self.add_ev(ev_id="EV_3", battery_level=70.0, required_battery_level=90.0, preferred_time="10:30", maximum_waiting_time=30, priority="LOW", charging_duration=30)
        self.add_ev(ev_id="EV_4", battery_level=10.0, required_battery_level=80.0, preferred_time="11:00", maximum_waiting_time=60, priority="CRITICAL", charging_duration=60)

    def run_allocation_cycle(
        self,
        payment_override_map: Optional[Dict[str, bool]] = None
    ) -> List[Dict[str, Any]]:
        """
        Executes the multi-agent request submission, search, negotiation,
        and payment allocation cycle for all registered EV agents.
        
        Demonstrates Rule-Based Urgency Sorting and Autonomous Peer Negotiations.
        """
        results: List[Dict[str, Any]] = []
        payment_override_map = payment_override_map or {}

        # 1. EV Agents autonomously generate charging requests
        requests_to_process = []
        for ev in self.ev_agents:
            req = ev.generate_request()
            if self.db:
                self.db.insert_request(
                    request_id=req["request_id"],
                    ev_id=req["ev_id"],
                    preferred_time=req["preferred_time"],
                    duration_minutes=req["duration_minutes"],
                    priority=req["priority"],
                    status="PENDING"
                )
            requests_to_process.append((ev, req))

        # 2. Rule-Based Reasoning: Prioritize requests by (Priority Score desc, Battery Urgency desc, Arrival Time asc)
        def request_urgency_key(item):
            ev, req = item
            p_score = PRIORITY_SCORES.get(req["priority"], 0.5)
            urgency = (100.0 - req["current_battery"]) / 100.0
            pref_min = time_to_minutes(req["preferred_time"])
            return (-p_score, -urgency, pref_min)

        requests_to_process.sort(key=request_urgency_key)

        # 3. Process requests autonomously via Charging Station Agents
        for ev, req in requests_to_process:
            self.simulation_step += 1
            self.current_time_str = req["preferred_time"]
            
            # Select target station (or try primary station, fallback to next station if multiple exist)
            outcome = None
            for station in self.station_agents:
                force_pay = payment_override_map.get(ev.ev_id, None)
                outcome = station.receive_request(
                    ev_agent=ev,
                    request=req,
                    payment_agent=self.payment_agent,
                    force_payment_success=force_pay
                )
                
                # If confirmed or payment failed, we stop trying other stations for this request
                if outcome["status"] in ["CONFIRMED", "PAYMENT_FAILED"]:
                    break
            
            results.append({
                "ev_id": ev.ev_id,
                "request_id": req["request_id"],
                "outcome": outcome
            })

        return results

    def get_metrics(self) -> Dict[str, Any]:
        """
        Computes key performance indicators (KPIs) for the Multi-Agent System:
        1. Average Waiting Time
        2. Charger Utilization (%)
        3. Allocation Success Rate (%)
        4. Negotiation Success Rate (%)
        5. Average Negotiation Rounds
        6. Total Rejected Requests
        """
        total_requests = len(self.ev_agents)
        all_bookings = []
        total_chargers = sum(len(s.chargers) for s in self.station_agents)

        for s in self.station_agents:
            all_bookings.extend(s.current_bookings)

        registered_ev_ids = {ev.ev_id for ev in self.ev_agents}
        confirmed_bookings = [b for b in all_bookings if b.get("status") == "CONFIRMED" and b.get("ev_id") in registered_ev_ids]
        num_confirmed = len(confirmed_bookings)
        num_rejected = total_requests - num_confirmed

        # 1. Average Waiting Time
        total_waiting_time = 0
        for b in confirmed_bookings:
            # Find original preferred time
            ev_id = b["ev_id"]
            ev_agent = next((a for a in self.ev_agents if a.ev_id == ev_id), None)
            if ev_agent:
                pref_min = time_to_minutes(ev_agent.preferred_time)
                start_min = time_to_minutes(b["start_time"])
                delay = max(0, start_min - pref_min)
                total_waiting_time += delay

        avg_waiting_time = round(total_waiting_time / num_confirmed, 2) if num_confirmed > 0 else 0.0

        # 2. Charger Utilization (%) over an 8-hour reference day (480 mins per charger)
        total_booked_minutes = sum(b.get("duration_minutes", 0) for b in confirmed_bookings)
        total_capacity_minutes = max(1, total_chargers * 480)
        charger_utilization = round((total_booked_minutes / total_capacity_minutes) * 100.0, 2)

        # 3. Successful Allocation Rate
        allocation_success_rate = round((num_confirmed / max(1, total_requests)) * 100.0, 2)

        # 4 & 5. Negotiation Statistics
        total_rounds = 0
        total_sessions = 0
        agreed_negotiations = 0

        for s in self.station_agents:
            for session in s.active_negotiations.values():
                total_sessions += 1
                total_rounds += session.current_round
                if session.status == "AGREED":
                    agreed_negotiations += 1

        avg_rounds = round(total_rounds / max(1, total_sessions), 2) if total_sessions > 0 else 1.0
        negotiation_success_rate = round((agreed_negotiations / max(1, total_sessions)) * 100.0, 2) if total_sessions > 0 else 0.0

        return {
            "total_requests": total_requests,
            "confirmed_allocations": num_confirmed,
            "rejected_requests": num_rejected,
            "allocation_success_rate_pct": allocation_success_rate,
            "average_waiting_time_mins": avg_waiting_time,
            "charger_utilization_pct": charger_utilization,
            "negotiation_success_rate_pct": negotiation_success_rate,
            "average_negotiation_rounds": avg_rounds,
            "total_bookings": confirmed_bookings
        }
