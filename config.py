"""
Configuration Module for AI EV Charging Multi-Agent System.

This module centralizes system configurations, utility function weights,
negotiation limits, priority definitions, and environment defaults.
"""

from typing import Dict

# Simulation Time & Resolution
DEFAULT_TIME_STEP_MINUTES: int = 15  # Each slot quantum is 15 minutes
DEFAULT_SIMULATION_START: str = "08:00"
SIMULATION_TOTAL_MINUTES: int = 12 * 60  # 12-hour simulation horizon

# Negotiation Constraints
MAX_NEGOTIATION_ROUNDS: int = 3
DEFAULT_MAX_WAITING_TIME_MINUTES: int = 60  # Default maximum acceptable delay for EVs

# Priority Score Mappings (Rule-based reasoning input)
PRIORITY_SCORES: Dict[str, float] = {
    "CRITICAL": 1.0,
    "HIGH": 0.8,
    "MEDIUM": 0.5,
    "LOW": 0.2,
}

# Utility Function Weights (Configurable multi-attribute utility)
# Utility = w1*Priority + w2*BatteryUrgency + w3*WaitingTimeScore - w4*CostScore + w5*StationAffinity
DEFAULT_UTILITY_WEIGHTS: Dict[str, float] = {
    "w_priority": 0.25,        # Importance of EV user priority class
    "w_battery_urgency": 0.35, # Urgency based on low state-of-charge (100% - battery%)
    "w_waiting_time": 0.25,    # Penalty/reward for closeness to preferred time
    "w_cost": 0.15,            # Sensitivity to pricing/energy cost
}

# Default Station Configuration
DEFAULT_BASE_PRICE_PER_KWH: float = 0.25  # $ per kWh
DEFAULT_CHARGER_POWER_KW: float = 50.0    # 50 kW fast DC charger

# Database Configuration
DEFAULT_DB_PATH: str = "data/ev_charging.db"
