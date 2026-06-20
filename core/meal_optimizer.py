from typing import Any, Dict, List


class MealOptimizer:
    """
    Layer 7: Meal Optimization Engine.
    Performs food correction (adds, removes, or replaces foods) to match target calories
    and protein at the meal level. Run up to 5 iterative optimization passes.
    """

    PROTEIN_BOOSTERS = ["Egg White", "Paneer", "Tofu", "Moong Dal", "Soy Chunks"]
    SNACK_PROTEIN_BOOSTERS = ["Curd", "Milk", "Roasted Chana", "Egg White"]
    SNACK_ENERGY_FOODS = ["Apple", "Banana", "Roasted Chana"]
    CALORIE_DENSE_GRAINS = ["White Rice", "Peanuts", "Poha", "Upma", "Dosa"]
    HIGH_DENSITY_PROTEIN = {"Soy Chunks", "Paneer", "Tofu"}

    CONSTRAINTS = {
        "Egg": (1.0, 4.0, 1.0, "unit"),
        "Egg White": (1.0, 8.0, 1.0, "unit"),
        "Milk": (100.0, 500.0, 50.0, "ml"),
        "Curd": (50.0, 300.0, 50.0, "g"),
        "Paneer": (20.0, 200.0, 10.0, "g"),
        "Tofu": (20.0, 200.0, 10.0, "g"),
        "Soy Chunks": (10.0, 100.0, 10.0, "g"),
        "Moong Dal": (50.0, 300.0, 50.0, "g"),
        "Masoor Dal": (50.0, 300.0, 50.0, "g"),
        "Chana Dal": (50.0, 300.0, 50.0, "g"),
        "Rajma": (50.0, 300.0, 50.0, "g"),
        "Chole": (50.0, 300.0, 50.0, "g"),
        "Roti": (1.0, 4.0, 1.0, "unit"),
        "Brown Rice": (50.0, 300.0, 50.0, "g"),
        "White Rice": (50.0, 300.0, 50.0, "g"),
        "Oats": (30.0, 150.0, 10.0, "g"),
        "Poha": (50.0, 250.0, 50.0, "g"),
        "Upma": (50.0, 250.0, 50.0, "g"),
        "Idli": (1.0, 4.0, 1.0, "unit"),
        "Dosa": (1.0, 3.0, 1.0, "unit"),
        "Peanuts": (10.0, 50.0, 5.0, "g"),
        "Roasted Chana": (10.0, 100.0, 10.0, "g"),
        "Banana": (50.0, 200.0, 50.0, "g"),
        "Apple": (50.0, 200.0, 50.0, "g"),
    }

    def __init__(self, filtered_foods: List[Dict[str, Any]], verbose: bool = True):
        self.filtered_foods = filtered_foods
        self.food_db = {f["food_name"]: f for f in filtered_foods}
        self.verbose = verbose

    def _log(self, message: str) -> None:
        if self.verbose:
            print(message)

    def _get_food_macro(self, food_name: str, macro: str) -> float:
        food = self.food_db.get(food_name)
        if food:
            try:
                return float(food.get(macro, 0.0))
            except (TypeError, ValueError):
                return 0.0
        return 0.0

    def _parse_serving_string(self, food_name: str):
        food = self.food_db.get(food_name, {})
        serving_str = food.get("serving", "100 g")
        parts = serving_str.strip().split()
        if not parts:
            return 100.0, "g"
        try:
            qty = float(parts[0])
        except ValueError:
            qty = 1.0
        raw_unit = " ".join(parts[1:])
        if food_name in self.CONSTRAINTS:
            return qty, self.CONSTRAINTS[food_name][3]
        if any(w in raw_unit.lower() for w in ["egg", "idli", "dosa", "appam", "medium", "whole", "unit"]):
            return qty, "unit"
        if "ml" in raw_unit.lower():
            return qty, "ml"
        return qty, "g"

    def _protein_boosters_for_meal(self, meal_name: str) -> List[str]:
        if meal_name == "snack":
            return [
                booster
                for booster in self.SNACK_PROTEIN_BOOSTERS
                if booster in self.food_db
            ]
        return [booster for booster in self.PROTEIN_BOOSTERS if booster in self.food_db]

    def check_capacity(self, foods: List[str], target_cal: float, target_prot: float) -> bool:
        if not foods:
            return False

        total_max_cal = 0.0
        total_max_prot = 0.0
        total_min_cal = 0.0
        max_food_ratio = 0.0

        for food_name in foods:
            if food_name not in self.food_db:
                continue
            base_cal = self._get_food_macro(food_name, "calories")
            base_prot = self._get_food_macro(food_name, "protein")
            base_qty, _ = self._parse_serving_string(food_name)

            if food_name in self.CONSTRAINTS:
                min_q, max_q, _, _ = self.CONSTRAINTS[food_name]
            else:
                min_q = base_qty * 0.5
                max_q = base_qty * 3.0

            cal_per_unit = base_cal / (base_qty or 1.0)
            prot_per_unit = base_prot / (base_qty or 1.0)

            total_max_cal += max_q * cal_per_unit
            total_max_prot += max_q * prot_per_unit
            total_min_cal += min_q * cal_per_unit

            ratio = prot_per_unit / (cal_per_unit or 0.001)
            max_food_ratio = max(max_food_ratio, ratio)

        target_ratio = target_prot / (target_cal or 1.0)
        cal_ok = total_max_cal >= target_cal * 0.95 and total_min_cal <= target_cal * 1.05
        prot_ok = total_max_prot >= target_prot * 0.95
        ratio_ok = max_food_ratio >= target_ratio * 0.90

        return cal_ok and prot_ok and ratio_ok

    def _should_add_protein_booster(
        self,
        meal_name: str,
        foods: List[str],
        target_cal: float,
        target_prot: float,
    ) -> bool:
        if target_prot <= 0:
            return False

        actual_prot = sum(self._get_food_macro(f, "protein") for f in foods)
        if actual_prot >= target_prot * 0.85:
            return False

        total_max_prot = 0.0
        max_food_ratio = 0.0
        for food_name in foods:
            base_cal = self._get_food_macro(food_name, "calories")
            base_prot = self._get_food_macro(food_name, "protein")
            base_qty, _ = self._parse_serving_string(food_name)
            max_q = self.CONSTRAINTS[food_name][1] if food_name in self.CONSTRAINTS else base_qty * 3.0
            total_max_prot += max_q * (base_prot / (base_qty or 1.0))
            max_food_ratio = max(max_food_ratio, base_prot / (base_cal or 0.001))

        target_ratio = target_prot / (target_cal or 1.0)
        if meal_name == "snack":
            return total_max_prot < target_prot * 0.90 and max_food_ratio < target_ratio * 0.85
        return total_max_prot < target_prot * 0.95 or max_food_ratio < target_ratio * 0.95

    def optimize_meal_plan(self, meal_plan: Dict[str, Any]) -> Dict[str, Any]:
        self._log("\n--- Running Layer 7: Meal Optimization Engine ---")

        meal_order = ["breakfast", "lunch", "snack", "dinner"]
        optimized_plan = {
            "breakfast": dict(meal_plan["breakfast"]),
            "lunch": dict(meal_plan["lunch"]),
            "snack": dict(meal_plan["snack"]),
            "dinner": dict(meal_plan["dinner"]),
            "repetition_counts": dict(meal_plan.get("repetition_counts", {})),
        }

        for meal_name in meal_order:
            meal = optimized_plan[meal_name]
            target_cal = meal["target_calories"]
            target_prot = meal["target_protein"]

            self._log(
                f"\nOptimizing {meal_name.upper()} "
                f"(Target Cal: {target_cal}, Target Prot: {target_prot}g)"
            )

            for pass_idx in range(1, 6):
                foods = list(meal["foods"])

                if self.check_capacity(foods, target_cal, target_prot):
                    self._log(
                        f"  [OK] Capacity check passed on Pass {pass_idx}. "
                        "Portion Optimizer will handle formatting."
                    )
                    break

                actual_cal = sum(self._get_food_macro(f, "calories") for f in foods)
                actual_prot = sum(self._get_food_macro(f, "protein") for f in foods)
                self._log(
                    f"  Pass {pass_idx}: Foods: {foods} | "
                    f"Est Cal: {round(actual_cal)} | Est Prot: {round(actual_prot, 1)}g"
                )

                modified = False

                if self._should_add_protein_booster(meal_name, foods, target_cal, target_prot):
                    for booster in self._protein_boosters_for_meal(meal_name):
                        if booster in self.food_db and booster not in foods:
                            if meal_name == "snack" and len(foods) >= 2:
                                break
                            foods.append(booster)
                            self._log(f"    [+] Added protein booster: {booster}")
                            modified = True
                            break

                    if not modified and foods and meal_name != "snack":
                        lowest_prot_food = min(
                            foods,
                            key=lambda f: self._get_food_macro(f, "protein"),
                        )
                        for booster in self._protein_boosters_for_meal(meal_name):
                            if booster in self.food_db and booster not in foods:
                                foods.remove(lowest_prot_food)
                                foods.append(booster)
                                self._log(
                                    f"    [REPLACE] Replaced {lowest_prot_food} with {booster}"
                                )
                                modified = True
                                break
                else:
                    total_min_cal = 0.0
                    for food_name in foods:
                        base_cal = self._get_food_macro(food_name, "calories")
                        base_qty, _ = self._parse_serving_string(food_name)
                        min_q = (
                            self.CONSTRAINTS[food_name][0]
                            if food_name in self.CONSTRAINTS
                            else base_qty * 0.5
                        )
                        total_min_cal += min_q * (base_cal / (base_qty or 1.0))

                    cal_gap = target_cal - actual_cal

                    if total_min_cal > target_cal * 1.05:
                        non_boosters = [
                            f
                            for f in foods
                            if f not in self._protein_boosters_for_meal(meal_name)
                        ]
                        food_to_remove = None
                        if non_boosters:
                            food_to_remove = max(
                                non_boosters,
                                key=lambda f: self._get_food_macro(f, "calories"),
                            )
                        elif len(foods) > 1:
                            food_to_remove = max(
                                foods,
                                key=lambda f: self._get_food_macro(f, "calories"),
                            )
                        if food_to_remove:
                            foods.remove(food_to_remove)
                            self._log(f"    [-] Removed high-calorie food: {food_to_remove}")
                            modified = True
                    elif cal_gap > 0.05 * target_cal:
                        if meal_name == "snack":
                            candidates = self.SNACK_ENERGY_FOODS
                        elif meal_name == "breakfast":
                            candidates = ["Oats", "Poha", "Roti"]
                        elif meal_name in ["lunch", "dinner"]:
                            candidates = ["Brown Rice", "Roti"]
                        else:
                            candidates = []

                        for candidate in candidates:
                            if candidate in self.food_db and candidate not in foods:
                                if meal_name == "snack" and len(foods) >= 2:
                                    break
                                foods.append(candidate)
                                self._log(f"    [+] Added energy food: {candidate}")
                                modified = True
                                break

                if not modified:
                    self._log("    [!] No further food corrections possible.")
                    break

                meal["foods"] = foods
                meal["actual_calories"] = round(
                    sum(self._get_food_macro(f, "calories") for f in foods)
                )
                meal["actual_protein"] = round(
                    sum(self._get_food_macro(f, "protein") for f in foods), 1
                )

            meal["food_details"] = []
            for food_name in meal["foods"]:
                meal["food_details"].append(
                    {
                        "food_name": food_name,
                        "protein_score": self._get_food_macro(food_name, "protein"),
                        "fiber_score": self._get_food_macro(food_name, "fiber"),
                        "condition_bonus": 0.0,
                        "rag_bonus": 0.0,
                        "final_score": self._get_food_macro(food_name, "protein"),
                    }
                )

        all_foods = []
        for meal_name in meal_order:
            all_foods.extend(optimized_plan[meal_name]["foods"])
        rep_counts = {}
        for food in all_foods:
            rep_counts[food] = rep_counts.get(food, 0) + 1
        optimized_plan["repetition_counts"] = rep_counts

        return optimized_plan
