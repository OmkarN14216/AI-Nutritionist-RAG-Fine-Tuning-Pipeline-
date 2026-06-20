import json
from collections import Counter
from typing import Any, Dict, List, Optional

from core.audit_engine import AuditEngine
from core.daily_rebalance import DailyRebalanceEngine
from core.meal_optimizer import MealOptimizer
from core.meal_planner import MealPlanner
from core.portion_optimizer import PortionOptimizer
from core.weekly_audit import WeeklyAuditEngine


class WeeklyPlanner:
    """
    Generates a deterministic seven-day plan using the existing daily planner,
    while enforcing week-level repetition limits and rotation.
    """

    MEAL_ORDER = ["breakfast", "lunch", "snack", "dinner"]

    def __init__(
        self,
        filtered_foods: List[Dict[str, Any]],
        calculation_results: Dict[str, Any],
        rule_results: Dict[str, Any],
        active_conditions: Optional[List[str]] = None,
        rag_food_bonuses: Any = None,
        repetition_limits_path: str = "config/weekly_repetition_limits.json",
        enable_rag_scoring: bool = True,
        verbose: bool = False,
    ):
        self.filtered_foods = filtered_foods
        self.calculation_results = calculation_results
        self.rule_results = rule_results
        self.active_conditions = active_conditions or []
        self.rag_food_bonuses = rag_food_bonuses
        self.enable_rag_scoring = enable_rag_scoring
        self.verbose = verbose
        self.weekly_repetition_limits = self._load_limits(repetition_limits_path)
        self.food_lookup = {food["food_name"]: food for food in filtered_foods}

    @staticmethod
    def _load_limits(path: str) -> Dict[str, int]:
        with open(path, "r", encoding="utf-8") as file_handle:
            return json.load(file_handle)

    @staticmethod
    def _normalize(value: str) -> str:
        return (value or "").strip().lower()

    def _weekly_key(self, food_name: str) -> str:
        normalized_food = self._normalize(food_name)
        for key in self.weekly_repetition_limits:
            if self._normalize(key) in normalized_food:
                return key
        return food_name

    def _food_available_for_week(self, food: Dict[str, Any], weekly_counts: Counter) -> bool:
        food_name = food["food_name"]
        weekly_key = self._weekly_key(food_name)
        limit = self.weekly_repetition_limits.get(weekly_key)
        if limit is None:
            return True
        planning_buffer = 1 if limit > 1 else 0
        return weekly_counts[weekly_key] < limit - planning_buffer

    def _available_foods(self, weekly_counts: Counter) -> List[Dict[str, Any]]:
        return [
            food
            for food in self.filtered_foods
            if self._food_available_for_week(food, weekly_counts)
        ]

    def _update_weekly_counts(self, portion_plan: Dict[str, Any], weekly_counts: Counter) -> None:
        for meal_name in self.MEAL_ORDER:
            for food_name in portion_plan.get(meal_name, {}).get("foods", []):
                weekly_counts[self._weekly_key(food_name)] += 1

    def generate_weekly_plan(self) -> Dict[str, Any]:
        target_calories = self.calculation_results["thermodynamics"]["target_dietary_calories_kcal"]
        target_protein = self.calculation_results["target_macronutrients_absolute"]["protein_grams"]
        allocation = MealPlanner.allocate_calories(target_calories)

        weekly_counts: Counter = Counter()
        days = []

        for day_number in range(1, 8):
            available_foods = self._available_foods(weekly_counts)

            meal_plan = MealPlanner.generate_meal_plan(
                available_foods,
                allocation,
                target_protein,
                active_conditions=self.active_conditions,
                rag_food_bonuses=self.rag_food_bonuses,
                enable_rag_scoring=self.enable_rag_scoring,
                weekly_usage_counts=weekly_counts,
                weekly_repetition_limits=self.weekly_repetition_limits,
                rotation_offset=day_number - 1,
            )

            meal_optimizer = MealOptimizer(available_foods, verbose=self.verbose)
            optimized_plan = meal_optimizer.optimize_meal_plan(meal_plan)

            portion_optimizer = PortionOptimizer(available_foods, verbose=self.verbose)
            portion_plan = portion_optimizer.optimize_portions(optimized_plan)

            rebalancer = DailyRebalanceEngine(available_foods, PortionOptimizer.CONSTRAINTS)
            portion_plan = rebalancer.rebalance(
                portion_plan,
                target_calories=target_calories,
                target_protein=target_protein,
            )

            audit_engine = AuditEngine(
                user_profile={},
                calculation_results=self.calculation_results,
                rule_constraints=self.rule_results,
                verbose=self.verbose,
            )
            audit_report = audit_engine.run_audit(portion_plan)

            self._update_weekly_counts(portion_plan, weekly_counts)

            days.append({
                "day": day_number,
                "meal_plan": meal_plan,
                "optimized_plan": optimized_plan,
                "portion_plan": portion_plan,
                "audit_report": audit_report,
            })

        weekly_plan = {
            "days": days,
            "weekly_repetition_limits": self.weekly_repetition_limits,
            "weekly_repetition_counts": dict(weekly_counts),
        }

        weekly_audit = WeeklyAuditEngine(
            calculation_results=self.calculation_results,
            weekly_repetition_limits=self.weekly_repetition_limits,
            food_lookup=self.food_lookup,
            verbose=self.verbose,
        )
        weekly_plan["weekly_audit_report"] = weekly_audit.run_weekly_audit(weekly_plan)

        return weekly_plan
