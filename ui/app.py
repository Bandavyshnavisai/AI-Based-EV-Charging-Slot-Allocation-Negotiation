"""
Streamlit Web Dashboard for AI EV Charging Multi-Agent System.

Provides an interactive GUI for college AI demonstration:
- Scenario Presets & Custom Configuration
- Multi-Agent Communication Event Stream
- Live Charger Occupancy Timeline / Schedule
- Negotiation Round Analytics
- Performance Metrics & SQLite Records
"""

import streamlit as st
import pandas as pd
import sys
import os
from typing import List, Dict, Any

# Ensure project root is on Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from environment.charging_model import ChargingModel
from negotiation.utility import UtilityCalculator
from config import DEFAULT_UTILITY_WEIGHTS, PRIORITY_SCORES


st.set_page_config(
    page_title="AI EV Charging Multi-Agent System",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #4B5563;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #F9FAFB 0%, #F3F4F6 100%);
        border: 1px solid #E5E7EB;
        border-radius: 8px;
        padding: 16px;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .badge-confirmed {
        background-color: #D1FAE5;
        color: #065F46;
        padding: 3px 8px;
        border-radius: 4px;
        font-weight: 600;
    }
    .badge-rejected {
        background-color: #FEE2E2;
        color: #991B1B;
        padding: 3px 8px;
        border-radius: 4px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


# --- SIDEBAR: SIMULATION CONFIGURATION & SCENARIOS ---
st.sidebar.title("⚡ Simulation Setup")

scenario_choice = st.sidebar.selectbox(
    "Choose Demonstration Scenario",
    [
        "Scenario A: Normal Allocation",
        "Scenario B: Slot Conflict (Competing EVs)",
        "Scenario C: Priority & Battery Urgency",
        "Scenario D: Multi-Round Negotiation",
        "Scenario E: Payment Failure & Rollback",
        "Scenario F: No Feasible Slot Available",
        "Custom Multi-Agent Setup"
    ]
)

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Multi-Attribute Utility Weights")
w_priority = st.sidebar.slider("w1: EV Priority Weight", 0.0, 1.0, DEFAULT_UTILITY_WEIGHTS["w_priority"], 0.05)
w_battery = st.sidebar.slider("w2: Battery Urgency Weight", 0.0, 1.0, DEFAULT_UTILITY_WEIGHTS["w_battery_urgency"], 0.05)
w_waiting = st.sidebar.slider("w3: Waiting Time Weight", 0.0, 1.0, DEFAULT_UTILITY_WEIGHTS["w_waiting_time"], 0.05)
w_cost = st.sidebar.slider("w4: Cost Sensitivity Weight", 0.0, 1.0, DEFAULT_UTILITY_WEIGHTS["w_cost"], 0.05)

custom_weights = {
    "w_priority": w_priority,
    "w_battery_urgency": w_battery,
    "w_waiting_time": w_waiting,
    "w_cost": w_cost
}

# --- MAIN HEADER ---
st.markdown('<div class="main-title">⚡ AI-Based EV Charging Slot Allocation & Negotiation</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Multi-Agent Systems Case Study | Autonomous Decentralized Negotiation & Constraint Satisfaction</div>', unsafe_allow_html=True)

# Define scenarios dataset
def get_scenario_data(scenario: str):
    if "Scenario A" in scenario:
        stations = [{"id": "Station_1", "name": "GreenPoint Hub", "chargers": 1, "price": 0.25}]
        evs = [{"id": "EV_Normal", "battery": 20.0, "req_battery": 80.0, "pref_time": "10:00", "wait": 60, "priority": "HIGH", "duration": 45, "pay_ok": True}]
        pre_bookings = []
    elif "Scenario B" in scenario:
        stations = [{"id": "Station_Central", "name": "Metro Central Station", "chargers": 1, "price": 0.25}]
        evs = [
            {"id": "EV_Primary", "battery": 15.0, "req_battery": 85.0, "pref_time": "10:00", "wait": 60, "priority": "HIGH", "duration": 60, "pay_ok": True},
            {"id": "EV_Secondary", "battery": 40.0, "req_battery": 80.0, "pref_time": "10:00", "wait": 90, "priority": "MEDIUM", "duration": 45, "pay_ok": True}
        ]
        pre_bookings = []
    elif "Scenario C" in scenario:
        stations = [{"id": "Station_Express", "name": "Express Charging Depot", "chargers": 1, "price": 0.25}]
        evs = [
            {"id": "EV_Urgent", "battery": 8.0, "req_battery": 80.0, "pref_time": "10:00", "wait": 30, "priority": "CRITICAL", "duration": 60, "pay_ok": True},
            {"id": "EV_NonUrgent", "battery": 75.0, "req_battery": 90.0, "pref_time": "10:00", "wait": 60, "priority": "LOW", "duration": 30, "pay_ok": True}
        ]
        pre_bookings = []
    elif "Scenario D" in scenario:
        stations = [{"id": "Station_Busy", "name": "Downtown Busy Depot", "chargers": 1, "price": 0.25}]
        pre_bookings = [{
            "booking_id": "BK-OCCUPIED",
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
        }]
        evs = [{
            "id": "EV_Negotiator",
            "battery": 30.0,
            "req_battery": 80.0,
            "pref_time": "10:00",
            "wait": 90,
            "priority": "HIGH",
            "duration": 45,
            "pay_ok": True,
            "initial_threshold": 0.55,
            "concession": 0.35
        }]
    elif "Scenario E" in scenario:
        stations = [{"id": "Station_Secured", "name": "Secured Station", "chargers": 1, "price": 0.25}]
        evs = [{"id": "EV_BadPayment", "battery": 25.0, "req_battery": 80.0, "pref_time": "10:00", "wait": 60, "priority": "HIGH", "duration": 60, "pay_ok": False}]
        pre_bookings = []
    elif "Scenario F" in scenario:
        stations = [{"id": "Station_Full", "name": "Fully Booked Station", "chargers": 1, "price": 0.25}]
        pre_bookings = [{
            "booking_id": "BK-ALLDAY",
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
        }]
        evs = [{"id": "EV_Impatient", "battery": 50.0, "req_battery": 80.0, "pref_time": "10:00", "wait": 0, "priority": "MEDIUM", "duration": 60, "pay_ok": True}]
    else:
        # Default Multi-Agent Configuration
        stations = [
            {"id": "Station_Downtown", "name": "Downtown Fast Hub", "chargers": 2, "price": 0.30},
            {"id": "Station_Uptown", "name": "Uptown Eco Charge", "chargers": 2, "price": 0.22}
        ]
        evs = [
            {"id": "EV_1", "battery": 15.0, "req_battery": 80.0, "pref_time": "10:00", "wait": 60, "priority": "HIGH", "duration": 60, "pay_ok": True},
            {"id": "EV_2", "battery": 25.0, "req_battery": 85.0, "pref_time": "10:00", "wait": 45, "priority": "MEDIUM", "duration": 45, "pay_ok": True},
            {"id": "EV_3", "battery": 70.0, "req_battery": 90.0, "pref_time": "10:30", "wait": 30, "priority": "LOW", "duration": 30, "pay_ok": True},
            {"id": "EV_4", "battery": 10.0, "req_battery": 80.0, "pref_time": "11:00", "wait": 60, "priority": "CRITICAL", "duration": 60, "pay_ok": True}
        ]
        pre_bookings = []
    return stations, evs, pre_bookings

stations_data, evs_data, pre_bookings_data = get_scenario_data(scenario_choice)

# --- SCENARIO INFORMATION DISPLAY ---
with st.expander("📋 Current Scenario Setup & Agent Request Data", expanded=True):
    col_st, col_ev = st.columns([1, 2])
    with col_st:
        st.markdown("**Registered Charging Stations**")
        df_stations = pd.DataFrame(stations_data)
        st.dataframe(df_stations, use_container_width=True, hide_index=True)
    with col_ev:
        st.markdown("**Autonomous EV Agents & Request Constraints**")
        df_evs = pd.DataFrame(evs_data)
        st.dataframe(df_evs, use_container_width=True, hide_index=True)

# Run Button
start_sim = st.button("🚀 Start Multi-Agent Simulation", type="primary", use_container_width=True)

if start_sim:
    # Initialize Mesa Simulation Model
    model = ChargingModel(db_path=":memory:")
    
    # Configure custom weights
    utility_calc = UtilityCalculator(weights=custom_weights)

    # Register Stations
    for s_info in stations_data:
        st_agent = model.add_station(
            station_id=s_info["id"],
            name=s_info["name"],
            num_chargers=s_info["chargers"],
            base_price_per_kwh=s_info["price"]
        )
        st_agent.search_engine.utility_calc = utility_calc

    # Pre-seed existing bookings if applicable
    for pb in pre_bookings_data:
        target_st = next((s for s in model.station_agents if s.station_id == pb["station_id"]), None)
        if target_st:
            target_st.current_bookings.append(pb)

    # Register EVs
    payment_map = {}
    for ev_info in evs_data:
        ev_agent = model.add_ev(
            ev_id=ev_info["id"],
            battery_level=ev_info["battery"],
            required_battery_level=ev_info["req_battery"],
            preferred_time=ev_info["pref_time"],
            maximum_waiting_time=ev_info["wait"],
            priority=ev_info["priority"],
            charging_duration=ev_info["duration"],
            initial_utility_threshold=ev_info.get("initial_threshold"),
            concession_rate=ev_info.get("concession", 0.0)
        )
        ev_agent.utility_calculator = utility_calc
        payment_map[ev_info["id"]] = ev_info["pay_ok"]

    # Execute Allocation Cycle
    with st.spinner("Autonomous Agents negotiating and allocating slots..."):
        results = model.run_allocation_cycle(payment_override_map=payment_map)
        metrics = model.get_metrics()

    st.success("✔ Multi-Agent Allocation & Negotiation Completed Successfully!")

    # --- KPI METRICS ROW ---
    st.markdown("### 📊 System Performance Metrics")
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    with m1:
        st.metric("Total Requests", metrics["total_requests"])
    with m2:
        st.metric("Confirmed Allocations", metrics["confirmed_allocations"])
    with m3:
        st.metric("Success Rate", f"{metrics['allocation_success_rate_pct']}%")
    with m4:
        st.metric("Avg Waiting Time", f"{metrics['average_waiting_time_mins']} min")
    with m5:
        st.metric("Charger Utilization", f"{metrics['charger_utilization_pct']}%")
    with m6:
        st.metric("Avg Negotiation Rounds", f"{metrics['average_negotiation_rounds']}")

    # --- TABS: LOGS, NEGOTIATION, BOOKINGS, TIMELINE ---
    tab_logs, tab_timeline, tab_negotiation, tab_bookings = st.tabs([
        "💬 Multi-Agent Event Stream",
        "🕒 Charger Schedule & Timeline",
        "🤝 Negotiation Dialogue History",
        "📑 Confirmed Reservations Table"
    ])

    with tab_logs:
        st.markdown("#### Real-Time Autonomous Multi-Agent Communications")
        event_filter = st.selectbox("Filter Events", ["ALL", "REQUEST", "PROPOSAL", "PAYMENT", "RESERVATION"])
        
        filtered_events = model.events
        if event_filter != "ALL":
            filtered_events = [e for e in model.events if event_filter in e["event_type"]]

        for ev_log in filtered_events:
            e_type = ev_log["event_type"]
            badge_color = "🔵"
            if "CONFIRMED" in e_type or "APPROVED" in e_type:
                badge_color = "🟢"
            elif "FAILED" in e_type or "REJECT" in e_type or "NO_FEASIBLE" in e_type:
                badge_color = "🔴"
            elif "PROPOSAL" in e_type:
                badge_color = "🟡"

            st.write(f"**[{ev_log['timestamp']}]** {badge_color} `{ev_log['sender']}` ➔ `{ev_log['receiver']}` | **{e_type}**: {ev_log['message']}")

    with tab_timeline:
        st.markdown("#### Physical Charger Occupancy Schedule")
        schedule_rows = []
        for s in model.station_agents:
            for b in s.current_bookings:
                schedule_rows.append({
                    "Station": s.name,
                    "Charger": b["charger_id"],
                    "Assigned EV": b["ev_id"],
                    "Start Time": b["start_time"],
                    "End Time": b["end_time"],
                    "Duration (min)": b["duration_minutes"],
                    "Total Cost ($)": f"${b['total_cost']:.2f}",
                    "Status": b["status"]
                })
        
        if schedule_rows:
            st.dataframe(pd.DataFrame(schedule_rows), use_container_width=True, hide_index=True)
        else:
            st.info("No active reservations booked on physical chargers.")

    with tab_negotiation:
        st.markdown("#### Detailed Multi-Round Negotiation Outcomes")
        outcome_rows = []
        for r in results:
            ev_id = r["ev_id"]
            outcome = r["outcome"]
            status = outcome["status"]
            rounds = outcome.get("negotiation_rounds", 0)
            bk = outcome.get("booking")
            allocated_slot = f"{bk['start_time']} - {bk['end_time']}" if bk else "None"
            reason = outcome.get("reason", "Allocated successfully")
            
            outcome_rows.append({
                "EV ID": ev_id,
                "Status": status,
                "Negotiation Rounds": rounds,
                "Allocated Slot": allocated_slot,
                "Outcome Details": reason
            })
        st.dataframe(pd.DataFrame(outcome_rows), use_container_width=True, hide_index=True)

    with tab_bookings:
        st.markdown("#### Confirmed Reservations (Persistent Storage)")
        all_confirmed = metrics["total_bookings"]
        if all_confirmed:
            st.dataframe(pd.DataFrame(all_confirmed), use_container_width=True, hide_index=True)
        else:
            st.info("No reservations were confirmed in this cycle.")
