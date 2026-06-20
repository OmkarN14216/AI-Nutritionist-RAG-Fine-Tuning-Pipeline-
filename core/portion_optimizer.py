from typing import Any, Dict, List


class PortionOptimizer:
    """
    Layer 8: Portion Optimizer.
    Optimizes portion sizes (grams, units, ml) of the selected foods in the meal plan.
    NEVER adds, removes, replaces, or swaps foods.
    """

    CONSTRAINTS = {
        "Egg": (1.0, 4.0, 1.0, "unit"),
        "Egg White": (1.0, 8.0, 1.0, "unit"),
        "Milk": (100.0, 500.0, 50.0, "ml"),
        "Curd": (50.0, 300.0, 50.0, "g"),
        "Paneer": (20.0, 200.0, 10.0, "g"),
        "Tofu": (20.0, 200.0, 10.0, "g"),
        "Soy Chunks": (10.0, 80.0, 10.0, "g"),
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
        "Roasted Chana": (10.0, 80.0, 10.0, "g"),
        "Banana": (50.0, 200.0, 50.0, "g"),
        "Apple": (50.0, 200.0, 50.0, "g"),
    }

    def __init__(self, all_foods: List[Dict[str, Any]], verbose: bool = True):
        self.food_db = {f["food_name"]: f for f in all_foods}
        self.verbose = verbose

    def _log(self, message: str) -> None:
        if self.verbose:
            print(message)

    def _parse_serving_string(self, food_name: str):
        food = self.food_db.get(food_name, {})
        serving_str = food.get("serving", "100 g")

        parts = serving_str.strip().split()
        if not parts:
            return 100.0, "g", "g"

        try:
            qty = float(parts[0])
        except ValueError:
            qty = 1.0

        raw_unit = " ".join(parts[1:])

        if food_name in self.CONSTRAINTS:
            return qty, self.CONSTRAINTS[food_name][3], raw_unit

        if any(w in raw_unit.lower() for w in ["egg", "idli", "dosa", "appam", "medium", "whole", "unit"]):
            norm_unit = "unit"
        elif "ml" in raw_unit.lower():
            norm_unit = "ml"
        else:
            norm_unit = "g"

        return qty, norm_unit, raw_unit

    def _calc_loss(self, calories: float, protein: float, target_cal: float, target_prot: float) -> float:
        cal_err = calories - target_cal
        prot_err = protein - target_prot

        cal_loss = cal_err ** 2
        if prot_err > 0:
            prot_loss = 250.0 * (prot_err ** 2)
        else:
            prot_loss = 80.0 * (prot_err ** 2)

        return cal_loss + prot_loss

    def optimize_portions(self, meal_plan: Dict[str, Any]) -> Dict[str, Any]:
        self._log("\n--- Running Layer 8: Portion Optimizer ---")

        optimized_plan = {
            "breakfast": dict(meal_plan["breakfast"]),
            "lunch": dict(meal_plan["lunch"]),
            "snack": dict(meal_plan["snack"]),
            "dinner": dict(meal_plan["dinner"]),
            "repetition_counts": dict(meal_plan.get("repetition_counts", {})),
        }

        meal_order = ["breakfast", "lunch", "snack", "dinner"]

        for meal_name in meal_order:
            meal = optimized_plan[meal_name]
            foods = meal["foods"]

            if not foods:
                continue

            target_cal = meal["target_calories"]
            target_prot = meal["target_protein"]

            portions = {}
            for food_name in foods:
                food_info = self.food_db.get(food_name, {})
                base_cal = float(food_info.get("calories", 0))
                base_prot = float(food_info.get("protein", 0))

                base_qty, norm_unit, raw_unit = self._parse_serving_string(food_name)

                if food_name in self.CONSTRAINTS:
                    min_q, max_q, step_q, _ = self.CONSTRAINTS[food_name]
                else:
                    min_q = base_qty * 0.5
                    max_q = base_qty * 3.0
                    step_q = base_qty * 0.25

                cal_per_unit = base_cal / (base_qty or 1.0)
                prot_per_unit = base_prot / (base_qty or 1.0)

                portions[food_name] = {
                    "current_qty": base_qty,
                    "min_q": min_q,
                    "max_q": max_q,
                    "step_q": step_q,
                    "norm_unit": norm_unit,
                    "raw_unit": raw_unit,
                    "cal_per_unit": cal_per_unit,
                    "prot_per_unit": prot_per_unit,
                }

            def current_macros():
                calories = sum(
                    portions[f]["current_qty"] * portions[f]["cal_per_unit"] for f in foods
                )
                protein = sum(
                    portions[f]["current_qty"] * portions[f]["prot_per_unit"] for f in foods
                )
                return calories, protein

            best_loss = self._calc_loss(*current_macros(), target_cal, target_prot)

            for _ in range(40):
                improved = False

                for food_name in foods:
                    portion = portions[food_name]
                    original_qty = portion["current_qty"]

                    if original_qty + portion["step_q"] <= portion["max_q"]:
                        portion["current_qty"] = original_qty + portion["step_q"]
                        loss_inc = self._calc_loss(*current_macros(), target_cal, target_prot)
                        if loss_inc < best_loss:
                            best_loss = loss_inc
                            improved = True
                            continue
                        portion["current_qty"] = original_qty

                    if original_qty - portion["step_q"] >= portion["min_q"]:
                        portion["current_qty"] = original_qty - portion["step_q"]
                        loss_dec = self._calc_loss(*current_macros(), target_cal, target_prot)
                        if loss_dec < best_loss:
                            best_loss = loss_dec
                            improved = True
                            continue
                        portion["current_qty"] = original_qty

                if not improved:
                    break

            actual_cal, actual_prot = current_macros()
            meal["actual_calories"] = round(actual_cal)
            meal["actual_protein"] = round(actual_prot, 1)

            meal["foods_with_portions"] = []
            for food_name in foods:
                portion = portions[food_name]
                display_qty = (
                    int(portion["current_qty"])
                    if portion["norm_unit"] in ["g", "ml"]
                    else round(portion["current_qty"], 1)
                )

                if portion["norm_unit"] == "unit":
                    display_str = f"{display_qty} units"
                else:
                    display_str = f"{display_qty} {portion['norm_unit']}"

                meal["foods_with_portions"].append(
                    {
                        "food_name": food_name,
                        "quantity": display_qty,
                        "unit": portion["norm_unit"],
                        "display": display_str,
                        "calories": round(portion["current_qty"] * portion["cal_per_unit"]),
                        "protein": round(portion["current_qty"] * portion["prot_per_unit"], 1),
                    }
                )

            self._log(f"Optimized Portion Plan for {meal_name.upper()}:")
            for item in meal["foods_with_portions"]:
                self._log(
                    f"  - {item['food_name']}: {item['display']} "
                    f"({item['calories']} kcal, {item['protein']}g protein)"
                )

        return optimized_plan
