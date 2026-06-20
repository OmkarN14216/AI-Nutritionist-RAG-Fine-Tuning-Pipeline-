from collections import Counter
from typing import Any, Dict, List


class WeeklyAuditEngine:
    """
    Weekly audit layer.
    Verifies seven daily plans plus cross-week diversity and repetition limits.
    """

    MEAL_ORDER = ["breakfast", "lunch", "snack", "dinner"]
    CAL_TOLERANCE = 0.10
    PROTEIN_TOLERANCE = 0.10

    def __init__(
        self,
        calculation_results: Dict[str, Any],
        weekly_repetition_limits: Dict[str, int],
        food_lookup: Dict[str, Dict[str, Any]],
        verbose: bool = True,
    ):
        self.calculation_results = calculation_results
        self.weekly_repetition_limits = weekly_repetition_limits
        self.food_lookup = food_lookup
        self.verbose = verbose

    @staticmethod
    def _normalize(value: str) -> str:
        return (value or "").strip().lower()

    def _weekly_key(self, food_name: str) -> str:
        normalized_food = self._normalize(food_name)
        for key in self.weekly_repetition_limits:
            if self._normalize(key) in normalized_food:
                return key
        return food_name

    def _food_category(self, food_name: str) -> str:
        return self._normalize(self.food_lookup.get(food_name, {}).get("category", ""))

    def _food_diet_type(self, food_name: str) -> str:
        return self._normalize(self.food_lookup.get(food_name, {}).get("diet_type", ""))

    def run_weekly_audit(self, weekly_plan: Dict[str, Any]) -> Dict[str, Any]:
        warnings: List[str] = []
        daily_diagnostics = []
        weekly_counts: Counter = Counter()
        protein_sources = set()
        fruits = set()
        vegetables = set()
        regional_foods = set()

        target_cal = self.calculation_results["thermodynamics"]["target_dietary_calories_kcal"]
        target_prot = self.calculation_results["target_macronutrients_absolute"]["protein_grams"]

        for day_plan in weekly_plan.get("days", []):
            portion_plan = day_plan["portion_plan"]
            day_cal = 0
            day_prot = 0.0
            day_foods = []

            for meal_name in self.MEAL_ORDER:
                meal = portion_plan.get(meal_name, {})
                day_cal += meal.get("actual_calories", 0)
                day_prot += meal.get("actual_protein", 0.0)
                day_foods.extend(meal.get("foods", []))

            cal_dev = abs(day_cal - target_cal) / (target_cal or 1.0)
            prot_dev = abs(day_prot - target_prot) / (target_prot or 1.0)
            day_ok = cal_dev <= self.CAL_TOLERANCE and prot_dev <= self.PROTEIN_TOLERANCE

            if not day_ok:
                warnings.append(
                    f"Day {day_plan['day']} macro deviation exceeds weekly audit tolerance"
                )

            daily_diagnostics.append({
                "day": day_plan["day"],
                "actual_calories": day_cal,
                "actual_protein": round(day_prot, 1),
                "calorie_deviation_pct": round(cal_dev * 100, 1),
                "protein_deviation_pct": round(prot_dev * 100, 1),
                "passed": day_ok,
            })

            for food_name in day_foods:
                weekly_counts[self._weekly_key(food_name)] += 1
                category = self._food_category(food_name)
                if category in {"protein", "pulse", "dairy"}:
                    protein_sources.add(food_name)
                if category == "fruit":
                    fruits.add(food_name)
                if category == "vegetable":
                    vegetables.add(food_name)
                if category == "regional":
                    regional_foods.add(food_name)

        repetition_violations = [
            {"food_group": food_group, "count": weekly_counts[food_group], "limit": limit}
            for food_group, limit in self.weekly_repetition_limits.items()
            if weekly_counts[food_group] > limit
        ]
        for violation in repetition_violations:
            warnings.append(
                f"{violation['food_group']} used {violation['count']} times "
                f"(limit {violation['limit']})"
            )

        diversity = {
            "protein_sources": len(protein_sources),
            "fruit_variety": len(fruits),
            "vegetable_variety": len(vegetables),
            "regional_variety": len(regional_foods),
            "diet_types_used": sorted({
                self._food_diet_type(food_name)
                for food_name in weekly_counts
                if self._food_diet_type(food_name)
            }),
        }
        diversity_checks = {
            "protein_diversity": diversity["protein_sources"] >= 4,
            "fruit_diversity": diversity["fruit_variety"] >= 3,
            "vegetable_diversity": diversity["vegetable_variety"] >= 4,
            "regional_diversity": diversity["regional_variety"] >= 3,
        }

        for check_name, passed in diversity_checks.items():
            if not passed:
                warnings.append(f"{check_name} below weekly target")

        passed = (
            len(weekly_plan.get("days", [])) == 7
            and not repetition_violations
            and all(day["passed"] for day in daily_diagnostics)
            and all(diversity_checks.values())
        )

        return {
            "passed": passed,
            "warnings": warnings,
            "daily_diagnostics": daily_diagnostics,
            "weekly_repetition_diagnostics": {
                "counts": dict(weekly_counts),
                "violations": repetition_violations,
                "within_limits": not repetition_violations,
            },
            "diversity_diagnostics": {
                "metrics": diversity,
                "checks": diversity_checks,
            },
        }
