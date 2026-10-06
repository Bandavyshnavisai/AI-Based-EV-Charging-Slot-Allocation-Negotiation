"""
Command-Line Simulation Runner for EV Charging Multi-Agent System.

Provides an interactive CLI and automated execution modes to demonstrate
multi-agent interactions, negotiations, search strategies, and metrics.
"""

import sys
import os
import argparse
from typing import Optional, Dict

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from environment.charging_model import ChargingModel
from database.database import DatabaseManager


def run_scenario(scenario_name: str = "ALL", db_path: str = "data/ev_charging.db") -> None:
    """Executes a specific demonstration scenario and prints formatted agent event logs and metrics."""
    print("=" * 80)
    print(f"   AI-BASED EV CHARGING MULTI-AGENT SYSTEM - SCENARIO: {scenario_name}")
    print("=" * 80)

    model = ChargingModel(db_path=db_path)
    payment_overrides: Dict[str, bool] = {}

    if scenario_name == "NORMAL" or scenario_name == "SCENARIO_A":
        # Scenario A: Normal Single EV Allocation
        print("\n[Scenario A]: Normal Slot Allocation (1 Station, 1 Charger, 1 EV)")
        model.add_station("Station_1", "GreenPoint Hub", num_chargers=1, base_price_per_kwh=0.25)
        model.add_ev("EV_Normal", battery_level=20.0, required_battery_level=80.0, preferred_time="10:00", maximum_waiting_time=60, priority="HIGH", charging_duration=45)

    elif scenario_name == "CONFLICT" or scenario_name == "SCENARIO_B":
        # Scenario B: Slot Conflict between 2 EVs for 1 Charger
        print("\n[Scenario B]: Slot Conflict (1 Charger, 2 EVs competing for 10:00)")
        model.add_station("Station_Central", "Metro Central Station", num_chargers=1, base_price_per_kwh=0.25)
        # EV1 has higher priority and lower battery than EV2
        model.add_ev("EV_Primary", battery_level=15.0, required_battery_level=85.0, preferred_time="10:00", maximum_waiting_time=60, priority="HIGH", charging_duration=60)
        model.add_ev("EV_Secondary", battery_level=40.0, required_battery_level=80.0, preferred_time="10:00", maximum_waiting_time=90, priority="MEDIUM", charging_duration=45)

    elif scenario_name == "PRIORITY" or scenario_name == "SCENARIO_C":
        # Scenario C: Low Battery Emergency Priority
        print("\n[Scenario C]: Battery Urgency & Priority Arbitration (1 Charger, Urgent vs Normal)")
        model.add_station("Station_Express", "Express Charging Point", num_chargers=1, base_price_per_kwh=0.25)
        model.add_ev("EV_Urgent", battery_level=8.0, required_battery_level=80.0, preferred_time="10:00", maximum_waiting_time=30, priority="CRITICAL", charging_duration=60)
        model.add_ev("EV_NonUrgent", battery_level=75.0, required_battery_level=90.0, preferred_time="10:00", maximum_waiting_time=60, priority="LOW", charging_duration=30)

    elif scenario_name == "NEGOTIATION" or scenario_name == "SCENARIO_D":
        # Scenario D: Multi-round Negotiation with Alternative Counter-Proposals
        print("\n[Scenario D]: Multi-Round Negotiation with Alternative Counter-Proposals")
        station = model.add_station("Station_Busy", "Downtown Busy Depot", num_chargers=1, base_price_per_kwh=0.25)
        # Pre-seed existing confirmed booking at 10:00 - 10:30 (so requested slot 10:00 is UNAVAILABLE)
        station.current_bookings.append({
            "booking_id": "BK-PREBOOKED",
            "request_id": "REQ-PREV",
            "ev_id": "EV_Existing",
            "station_id": "Station_Busy",
            "charger_id": "Station_Busy_C1",
            "start_time": "10:00",
            "end_time": "10:30",
            "duration_minutes": 30,
            "total_cost": 7.50,
            "payment_status": "APPROVED",
            "status": "CONFIRMED"
        })
        # EV asks for 10:00. 10:00 is unavailable.
        # Round 1: Station proposes 10:30. EV rejects (utility 0.541 < Round 1 threshold 0.550).
        # Round 2: Station searches again & counter-proposes 11:00. EV concedes and accepts (utility 0.458 >= Round 2 threshold 0.358).
        model.add_ev(
            ev_id="EV_Negotiator",
            battery_level=30.0,
            required_battery_level=80.0,
            preferred_time="10:00",
            maximum_waiting_time=90,
            priority="HIGH",
            charging_duration=45,
            initial_utility_threshold=0.55,
            concession_rate=0.35,
            min_acceptable_utility=0.15
        )

    elif scenario_name == "PAYMENT_FAILURE" or scenario_name == "SCENARIO_E":
        # Scenario E: Payment Authorization Failure & Slot Rollback
        print("\n[Scenario E]: Payment Authorization Failure & Reservation Rollback")
        model.add_station("Station_Secured", "Secured Station", num_chargers=1, base_price_per_kwh=0.25)
        model.add_ev("EV_BadPayment", battery_level=25.0, required_battery_level=80.0, preferred_time="10:00", maximum_waiting_time=60, priority="HIGH", charging_duration=60)
        payment_overrides["EV_BadPayment"] = False

    elif scenario_name == "NO_SLOT" or scenario_name == "SCENARIO_F":
        # Scenario F: No Feasible Slot Available (Constraint Violation)
        print("\n[Scenario F]: No Feasible Slot (EV patience tolerance too tight for occupied station)")
        station = model.add_station("Station_Full", "Fully Booked Station", num_chargers=1, base_price_per_kwh=0.25)
        station.current_bookings.append({
            "booking_id": "BK-OCCUPIED",
            "request_id": "REQ-OCC",
            "ev_id": "EV_Occupier",
            "station_id": "Station_Full",
            "charger_id": "Station_Full_C1",
            "start_time": "10:00",
            "end_time": "12:00",
            "duration_minutes": 120,
            "total_cost": 30.0,
            "payment_status": "APPROVED",
            "status": "CONFIRMED"
        })
        # EV asks for 10:00 with 0 max waiting time tolerance
        model.add_ev("EV_Impatient", battery_level=50.0, required_battery_level=80.0, preferred_time="10:00", maximum_waiting_time=0, priority="MEDIUM", charging_duration=60)

    else:
        # Default Multi-EV Multi-Station Setup
        print("\n[Full Multi-Agent Simulation]: 2 Stations (4 Chargers) & 4 Autonomous EVs")
        model.setup_default_agents()

    # Execute simulation cycle
    print("\n>>> Executing Multi-Agent Allocation & Negotiation Cycle...\n")
    results = model.run_allocation_cycle(payment_override_map=payment_overrides)

    # Display Multi-Agent Interaction Event Log
    print("-" * 80)
    print("                      MULTI-AGENT INTERACTION EVENT LOG")
    print("-" * 80)
    for event in model.events:
        print(f"[{event['timestamp']}] [{event['event_type']:<22}] {event['sender']} -> {event['receiver']}: {event['message']}")

    # Display Allocation Summary
    print("\n" + "=" * 80)
    print("                         ALLOCATION OUTCOMES")
    print("=" * 80)
    for res in results:
        ev_id = res["ev_id"]
        outcome = res["outcome"]
        status = outcome["status"]
        rounds = outcome.get("negotiation_rounds", 0)
        bk = outcome.get("booking")
        if status == "CONFIRMED" and bk:
            print(f"[SUCCESS] {ev_id:<14} -> CONFIRMED | Station: {bk['station_id']} | Charger: {bk['charger_id']} | Time: {bk['start_time']} - {bk['end_time']} | Cost: ${bk['total_cost']:.2f} | Rounds: {rounds}")
        else:
            print(f"[REJECTED] {ev_id:<14} -> {status:<9} | Reason: {outcome.get('reason', 'N/A')} | Rounds: {rounds}")

    # Display System Performance Metrics
    metrics = model.get_metrics()
    print("\n" + "=" * 80)
    print("                      SYSTEM PERFORMANCE METRICS")
    print("=" * 80)
    print(f"  * Total Requests Processed       : {metrics['total_requests']}")
    print(f"  * Confirmed Allocations          : {metrics['confirmed_allocations']}")
    print(f"  * Rejected Requests              : {metrics['rejected_requests']}")
    print(f"  * Allocation Success Rate        : {metrics['allocation_success_rate_pct']}%")
    print(f"  * Average EV Waiting Time        : {metrics['average_waiting_time_mins']} minutes")
    print(f"  * Charger Utilization Rate       : {metrics['charger_utilization_pct']}%")
    print(f"  * Negotiation Success Rate       : {metrics['negotiation_success_rate_pct']}%")
    print(f"  * Average Negotiation Rounds     : {metrics['average_negotiation_rounds']}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run AI EV Charging Multi-Agent Simulation")
    parser.add_argument(
        "--scenario",
        type=str,
        default="ALL",
        choices=["ALL", "NORMAL", "CONFLICT", "PRIORITY", "NEGOTIATION", "PAYMENT_FAILURE", "NO_SLOT"],
        help="Select demo scenario to execute"
    )
    parser.add_argument("--db", type=str, default="data/ev_charging.db", help="Path to SQLite database")
    args = parser.parse_args()

    run_scenario(args.scenario, args.db)
