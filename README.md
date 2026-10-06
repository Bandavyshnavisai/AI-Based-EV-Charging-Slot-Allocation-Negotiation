# AI-Based EV Charging Slot Allocation & Negotiation System

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Mesa Multi-Agent](https://img.shields.io/badge/Mesa-Multi--Agent-orange.svg)](https://mesa.readthedocs.io/)
[![Streamlit UI](https://img.shields.io/badge/Streamlit-Dashboard-FF4B4B.svg)](https://streamlit.io/)
[![Pytest Status](https://img.shields.io/badge/pytest-23%20passed-brightgreen.svg)](https://docs.pytest.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

An intelligent Multi-Agent System (MAS) designed to solve the dynamic electric vehicle (EV) charging slot allocation and peer-to-peer negotiation problem without relying on a centralized controller.

---

## 1. Problem Statement

With the rapid adoption of electric vehicles, charging infrastructure faces high peak demand and concurrency conflicts. When multiple EVs request limited physical charging slots simultaneously:
- Uncoordinated bookings lead to severe charger contention, long queuing delays, and grid stress.
- Simple first-come-first-served (FCFS) or centralized database booking systems fail to consider user priority, battery state-of-charge urgency, dynamic price elasticity, and flexible arrival windows.
- Infeasible requests are simply dropped rather than negotiated into alternative viable time slots.

This project implements an **autonomous Multi-Agent EV Charging Slot Allocation and Negotiation System** where EV Agents, Charging Station Agents, and Payment Agents interact autonomously to discover, negotiate, and confirm charging slots.

---

## 2. Why Multi-Agent Systems (MAS)?

In real-world EV charging networks:
1. **Decentralization & Autonomy**: Stations are operated by distinct independent providers with private pricing and hardware constraints. EVs have private battery states, user schedules, and patience thresholds.
2. **Distributed Decision Making**: No single monolithic controller is required to dictate assignments. Each station agent manages its own resource allocation, while each EV agent evaluates proposals against its internal utility function.
3. **Adaptive Negotiation**: When preferred slots are congested, agents engage in multi-round bilateral negotiation (alternating proposals and counter-proposals) to reach optimal agreements.

---

## 3. System Architecture & Flow

```
+-------------------+              +-------------------------+              +----------------------+
|     EV Agent      |              |  Charging Station Agent |              |    Payment Agent     |
+-------------------+              +-------------------------+              +----------------------+
          |                                     |                                       |
          | --- 1. Charging Request ----------->|                                       |
          |    (Pref time, duration, battery)   |                                       |
          |                                     | --- 2. Heuristic Search & Constraints |
          |                                     |     (Filter unavailable slots)        |
          |                                     | --- 3. Multi-Attribute Utility        |
          |                                     |     (Rank best candidate slots)       |
          |                                     |                                       |
          |<--- 4. Slot Proposal / Counter -----|                                       |
          |                                     |                                       |
          | --- 5. Evaluate Utility & Bounds -->|                                       |
          |    (ACCEPT or REJECT)               |                                       |
          |                                     |                                       |
          |                                     | --- 6. Request Authorization -------->|
          |                                     |        (Verify total cost)            |
          |                                     |<--- 7. Payment APPROVED/REJECTED -----|
          |                                     |                                       |
          |                                     | --- 8. Confirm Reservation & DB Write |
          |<--- 9. Reservation Confirmed -------|                                       |
```

---

## 4. PEAS Analysis for Intelligent Agents

| Agent | Performance Measure (P) | Environment (E) | Actuators (A) | Sensors (S) |
|---|---|---|---|---|
| **EV Agent** | Minimized waiting delay, achieving target SOC (%), minimized energy cost, high allocation success. | Charging station network, competing EVs, time horizon, fluctuating prices. | Send charging request, evaluate proposals, transmit `ACCEPT`/`REJECT`, trigger payment. | Current SOC (%), target SOC, preferred time, maximum waiting tolerance, incoming proposals. |
| **Charging Station Agent** | Maximized charger utilization (%), high allocation throughput, balanced load, revenue. | Stream of EV requests, physical chargers, confirmed booking calendar. | Run slot search, apply constraints, calculate multi-attribute utility, send proposal/counter-proposal, lock/free slots. | Charger availability, booking schedule, EV request attributes, EV responses, payment receipts. |
| **Payment Agent** | Transaction authorization accuracy, fraud prevention, zero false confirmations. | Station payment requests, financial balance tokens. | Issue `APPROVED` or `REJECTED` tokens, log financial transactions. | Incoming payment requests with reservation ID, EV ID, and billing amount ($). |

---

## 5. Environment Characteristics

- **Dynamic**: EV requests arrive continuously; station schedules update dynamically with new bookings.
- **Partially Observable**: EV agents do not know internal station booking schedules or competing EV profiles; stations do not know EV true reservation thresholds.
- **Stochastic / Non-Deterministic**: Requests vary in arrival times, charging durations, user patience, and payment authorization outcomes.
- **Multi-Agent**: Contains competitive and cooperative agents negotiating limited resources.
- **Discrete**: Time is discretized into configurable quantum steps (e.g. 15-minute slot intervals).

---

## 6. AI Course Concepts & Implementation Map

| Course Concept | Implementation Location | Description |
|---|---|---|
| **Intelligent Agents** | [`agents/ev_agent.py`](file:///agents/ev_agent.py), [`agents/charging_station_agent.py`](file:///agents/charging_station_agent.py) | Goal-driven autonomous agents with internal state machines and utility decision functions. |
| **Multi-Agent Systems** | [`environment/charging_model.py`](file:///environment/charging_model.py) | Mesa-based simulation coordinating decentralized EV, Station, and Payment agents. |
| **Search Strategy** | [`negotiation/search.py`](file:///negotiation/search.py) | Heuristic best-first search generating candidate time intervals ranked by multi-attribute utility. |
| **Constraint Reasoning** | [`negotiation/constraints.py`](file:///negotiation/constraints.py) | Hard constraint filtering (no booking overlap, charger operational status, duration fit, EV patience tolerance). |
| **Rule-Based Reasoning** | [`environment/charging_model.py`](file:///environment/charging_model.py) | Priority queuing based on emergency rules (Critical Priority + Low SOC < 20% processed first). |
| **Utility-Based Decision** | [`negotiation/utility.py`](file:///negotiation/utility.py) | Multi-attribute utility function weighting Priority, Battery Urgency, Waiting Delay, and Cost. |
| **Negotiation Protocol** | [`negotiation/negotiation.py`](file:///negotiation/negotiation.py) | Rubinstein alternating-offers protocol with counter-proposals and a configurable `MAX_NEGOTIATION_ROUNDS`. |
| **Agent Communication** | [`environment/charging_model.py`](file:///environment/charging_model.py) & `event_logs` | Structured message-passing and real-time interaction event stream with persistent logging. |
| **Two-Phase Confirmation** | [`agents/payment_agent.py`](file:///agents/payment_agent.py) | Payment authorization barrier; slots are only confirmed upon payment approval, else rolled back. |
| **Data Persistence** | [`database/database.py`](file:///database/database.py) | Relational SQLite schema recording stations, chargers, EVs, requests, dialogues, and bookings. |

---

## 7. Multi-Attribute Utility Function

Candidate charging slots $s$ are scored and ranked using the configurable weighted formula:

$$U(s) = w_{p} \cdot \text{PriorityScore} + w_{b} \cdot \text{BatteryUrgency} + w_{w} \cdot \text{WaitingTimeScore}(s) - w_{c} \cdot \text{CostScore}(s)$$

Where:
- $\text{PriorityScore} \in [0.2, 1.0]$: User priority level (`CRITICAL` = 1.0, `HIGH` = 0.8, `MEDIUM` = 0.5, `LOW` = 0.2).
- $\text{BatteryUrgency} = \frac{100 - \text{CurrentSOC}}{100}$: Urgency metric where low battery percentage yields higher priority.
- $\text{WaitingTimeScore}(s) = \max\left(0, 1.0 - \frac{\text{start\_time}(s) - \text{preferred\_time}}{\text{max\_waiting\_time}}\right)$: Closeness to preferred time.
- $\text{CostScore}(s) = \min\left(1.0, \frac{\text{total\_cost}}{\text{reference\_cost}}\right)$: Normalized financial cost penalty.
- $w_p, w_b, w_w, w_c$: Configurable weights defined in [`config.py`](file:///config.py) and adjustable via the Streamlit dashboard.

---

## 8. Technology Stack

- **Language**: Python 3.10+
- **Multi-Agent Framework**: [Mesa 3.3+](https://mesa.readthedocs.io/)
- **Interactive UI Dashboard**: [Streamlit](https://streamlit.io/)
- **Data Persistence**: SQLite 3
- **Unit & Integration Testing**: Pytest
- **Data Manipulation**: Pandas

---

## 9. Project Structure

```
EV_charging_station/
│
├── config.py                 # Centralized configuration, utility weights, and priority scores
├── run_simulation.py         # Command-Line execution runner with formatted ASCII logs
├── requirements.txt          # Project dependencies
├── README.md                 # Complete documentation and demonstration guide
├── .gitignore                # Git ignore rules
│
├── agents/                   # Autonomous Agent Definitions
│   ├── __init__.py
│   ├── ev_agent.py           # EVAgent with state machine and proposal evaluation
│   ├── charging_station_agent.py # ChargingStationAgent with slot search and allocation
│   └── payment_agent.py      # PaymentAgent with financial verification and rollback
│
├── environment/              # Mesa Simulation Environment
│   ├── __init__.py
│   └── charging_model.py     # Mesa ChargingModel, scheduling, event bus, metrics
│
├── negotiation/              # AI Reasoning, Constraints & Search
│   ├── __init__.py
│   ├── constraints.py        # Hard and soft constraint checkers
│   ├── utility.py            # Multi-attribute utility calculator
│   ├── search.py             # Heuristic slot search engine
│   └── negotiation.py        # Negotiation session and alternating-offers protocol
│
├── database/                 # SQLite Persistence Layer
│   ├── __init__.py
│   └── database.py           # Schema initialization, CRUD operations, logging
│
├── ui/                       # Web Dashboard
│   └── app.py                # Streamlit GUI with scenario presets and live event stream
│
├── tests/                    # Automated Test Suite (23 Pytest Cases)
│   ├── __init__.py
│   ├── test_agents.py        # Unit tests for EVAgent & ChargingStationAgent
│   ├── test_constraints.py   # Unit tests for constraint validation
│   ├── test_negotiation.py   # Unit tests for multi-round negotiation
│   ├── test_payment.py       # Unit tests for payment approval & failure
│   ├── test_search.py        # Unit tests for slot search engine
│   └── test_scenarios.py     # End-to-end integration tests (Rubric Tests 1 - 8)
│
└── data/                     # Database & Output Artifacts
    └── .gitkeep
```

---

## 10. Installation & Setup

### 1. Clone the repository
```bash
git clone <your-repository-url>
cd EV_charging_station
```

### 2. Create and activate a virtual environment
**On Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**On Linux / macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install required dependencies
```bash
pip install -r requirements.txt
```

---

## 11. How to Run

### Mode 1: Command-Line Simulation Runner
Run the full multi-agent simulation with rich console logs:
```bash
python run_simulation.py --scenario ALL
```

You can also trigger individual test scenarios via CLI:
```bash
python run_simulation.py --scenario NORMAL
python run_simulation.py --scenario CONFLICT
python run_simulation.py --scenario PRIORITY
python run_simulation.py --scenario NEGOTIATION
python run_simulation.py --scenario PAYMENT_FAILURE
python run_simulation.py --scenario NO_SLOT
```

### Mode 2: Interactive Streamlit Web Dashboard
Launch the web interface:
```bash
streamlit run ui/app.py
```
Open your browser at `http://localhost:8501`.

### Mode 3: Automated Pytest Suite
Run all 23 unit and integration tests:
```bash
pytest -v
```

---

## 12. Demonstration Scenarios

The system includes pre-configured presets specifically designed for faculty evaluation:

| Scenario | Setup & Context | Expected Multi-Agent Behavior |
|---|---|---|
| **Scenario A: Normal Allocation** | 1 Station (1 Charger), 1 EV requesting 10:00. | Immediate slot match at 10:00; payment approved; reservation confirmed in Round 1. |
| **Scenario B: Slot Conflict** | 1 Charger, 2 EVs competing for the exact same 10:00 slot. | Primary EV (higher priority/lower SOC) secures 10:00; Secondary EV negotiates alternative slot (11:00) and confirms. |
| **Scenario C: Battery Urgency** | EV1 (SOC 8%, Critical) vs EV2 (SOC 75%, Low). | Urgency rules prioritize EV1 for immediate slot; EV2 receives later slot. |
| **Scenario D: Multi-Round Negotiation** | Station pre-booked at 10:00; EV requests 10:00 with 75m patience. | Station counter-proposes 11:00; EV evaluates utility and accepts; confirmed. |
| **Scenario E: Payment Failure** | EV requests slot, accepts proposal, but payment is declined. | PaymentAgent returns `REJECTED`; station aborts reservation and releases hold on charger slot. |
| **Scenario F: No Feasible Slot** | Station occupied; EV has 0 minutes max waiting tolerance. | Constraint checker detects patience violation; station terminates cleanly with informative explanation. |

---

## 13. System Performance Metrics

The simulation automatically tracks and reports:
1. **Average Waiting Time**: Mean delay (minutes) between preferred start time and allocated start time for confirmed EVs.
2. **Charger Utilization Rate (%)**: Percentage of physical charger time occupied over the operating horizon.
3. **Allocation Success Rate (%)**: Percentage of submitted EV requests that successfully secured a confirmed charging slot.
4. **Negotiation Success Rate (%)**: Percentage of multi-round negotiation sessions that reached mutual agreement.
5. **Average Negotiation Rounds**: Mean number of proposal/counter-proposal exchanges per EV request.
6. **Rejected Requests**: Total requests that could not be satisfied due to constraint violations, payment failures, or negotiation timeouts.

---

## 14. Sample Multi-Agent Event Log

```
[08:00] [STATION_REGISTERED    ] SYSTEM -> Station_Downtown: Station Station_Downtown (2 chargers) registered.
[08:00] [EV_REGISTERED         ] SYSTEM -> EV_1: EV EV_1 registered (Battery: 15.0%, Priority: HIGH, Pref: 10:00).
[08:00] [EV_REGISTERED         ] SYSTEM -> EV_2: EV EV_2 registered (Battery: 25.0%, Priority: MEDIUM, Pref: 10:00).
[08:00] [REQUEST_GENERATED     ] EV_1 -> SYSTEM: EV_1 created charging request for 10:00 (duration: 60m, battery: 15.0%, priority: HIGH)
[10:00] [REQUEST_RECEIVED      ] EV_1 -> Station_Downtown: Station_Downtown received charging request REQ-EV_1 for 10:00
[10:00] [PROPOSAL_ACCEPT       ] EV_1 -> Station_Downtown: EV_1 ACCEPTED proposal for slot 10:00: Proposed slot 10:00-11:00 accepted (utility: 0.635)
[10:00] [PAYMENT_REQUESTED     ] Station_Downtown -> PaymentAgent_Central: Station_Downtown requesting payment authorization of $15.00 for EV_1
[10:00] [PAYMENT_APPROVED      ] PaymentAgent_Central -> Station_Downtown: Payment of $15.00 for EV_1 was APPROVED (TXN-B5A3DDBC)
[10:00] [RESERVATION_CONFIRMED ] Station_Downtown -> EV_1: Reservation BK-FE056573 confirmed on Charger Station_Downtown_C1 at 10:00-11:00
```

---

## 15. Future Extensions

- Integration of dynamic grid time-of-use (TOU) tariffs and renewable solar availability forecasts into the utility function.
- Vehicle-to-Grid (V2G) discharge negotiation allowing EVs to sell energy back to stations during peak hours.
- Machine-learning-based negotiation strategies (e.g. Q-learning or reinforcement learning for concession curves).
