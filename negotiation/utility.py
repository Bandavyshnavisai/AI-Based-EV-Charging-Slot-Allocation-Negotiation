"""
Utility Calculation Module for Multi-Agent Decision Making.

This module implements multi-attribute utility theory (MAUT) to evaluate
candidate charging slots based on:
1. EV User Priority
2. Battery Urgency (State of Charge deficit)
3. Waiting Time / Closeness to Preferred Time
4. Charging Cost

Utility Formula:
    Utility = w_priority * PriorityScore
            + w_battery_urgency * BatteryUrgencyScore
            + w_waiting_time * WaitingTimeScore
            - w_cost * CostScore
"""

from typing import Dict, Optional
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import DEFAULT_UTILITY_WEIGHTS, PRIORITY_SCORES


class UtilityCalculator:
    """
    Computes normalized utility scores for candidate charging slots.
    Supports dynamic, user-configurable attribute weighting.
    """

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = weights or DEFAULT_UTILITY_WEIGHTS.copy()

    def calculate_priority_score(self, priority: str) -> float:
        """Translates priority level string into a normalized score [0.0, 1.0]."""
        return PRIORITY_SCORES.get(priority.upper(), 0.5)

    def calculate_battery_urgency_score(self, current_battery: float) -> float:
        """
        Computes urgency score from EV's current battery percentage.
        Lower battery = higher urgency.
        Example: 10% battery -> 0.90 urgency; 80% battery -> 0.20 urgency.
        """
        clamped_battery = max(0.0, min(100.0, current_battery))
        return (100.0 - clamped_battery) / 100.0

    def calculate_waiting_time_score(self, waiting_time_min: int, max_waiting_time_min: int) -> float:
        """
        Computes waiting time satisfaction score [0.0, 1.0].
        0 delay = 1.0 score; max_waiting_time delay = 0.0 score.
        """
        if max_waiting_time_min <= 0:
            return 1.0 if waiting_time_min == 0 else 0.0
        
        ratio = waiting_time_min / max_waiting_time_min
        return max(0.0, min(1.0, 1.0 - ratio))

    def calculate_cost_score(self, total_cost: float, reference_cost: float = 20.0) -> float:
        """
        Normalizes total charging cost to a penalty score [0.0, 1.0].
        """
        if reference_cost <= 0:
            return 0.0
        return min(1.0, total_cost / reference_cost)

    def evaluate_slot_utility(
        self,
        priority: str,
        current_battery: float,
        waiting_time_min: int,
        max_waiting_time_min: int,
        total_cost: float,
        reference_cost: float = 20.0
    ) -> float:
        """
        Calculates the comprehensive utility score for a feasible candidate slot.
        Higher score indicates a better, more attractive allocation.
        """
        w_p = self.weights.get("w_priority", 0.25)
        w_b = self.weights.get("w_battery_urgency", 0.35)
        w_w = self.weights.get("w_waiting_time", 0.25)
        w_c = self.weights.get("w_cost", 0.15)

        p_score = self.calculate_priority_score(priority)
        b_score = self.calculate_battery_urgency_score(current_battery)
        w_score = self.calculate_waiting_time_score(waiting_time_min, max_waiting_time_min)
        c_score = self.calculate_cost_score(total_cost, reference_cost)

        utility = (w_p * p_score) + (w_b * b_score) + (w_w * w_score) - (w_c * c_score)
        return round(utility, 4)
