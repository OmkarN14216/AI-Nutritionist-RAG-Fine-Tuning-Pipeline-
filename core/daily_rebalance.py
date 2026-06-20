from typing import Any, Dict, List, Tuple


class DailyRebalanceEngine:
    """
    Layer 8.5: Daily Rebalance Engine.
    Performs global portion adjustments after per-meal portion optimization
    to align daily calories and protein with physiological targets.
    Never adds, removes, or swaps foods.
    """

    MEAL_ORDER = ["breakfast", "lunch", "snack", "dinner"]
    CAL_TOLERANCE = 0.05
    PROTEIN_TOLERANCE = 0.05

    def __init__(self, all_foods: List[Dict[str, Any]], portion_constraints: Dict[str, tuple]):
        self.food_db = {f["food_name"]: f for f in all_foods}
        self.constraints = portion_constraints

    def _base_qty(self, food_name: str) -> float:
        food = self.food_db.get(food_name, {})
        serving = str(food.get("serving", "100 g")).strip().split()
        try:
            return float(serving[0]) if serving else 100.0
        except ValueError:
            return 100.0

    def _default_unit(self, food_name: str) -> str:
        food = self.food_db.get(food_name, {})
        serving = str(food.get("serving", "100 g")).lower()
        if any(token in serving for token in ["egg", "idli", "dosa", "medium", "appam", "unit"]):
            return "unit"
        if "ml" in serving:
            return "ml"
        return "g"

    def _constraint_for(self, food_name: str) -> Tuple[float, float, float, str]:
        if food_name in self.constraints:
            return self.constraints[food_name]
        base_qty = self._base_qty(food_name)
        return (base_qty * 0.5, base_qty * 3.0, max(base_qty * 0.25, 1.0), self._default_unit(food_name))

    def _item_macros(self, item: Dict[str, Any]) -> Dict[str, float]:
        food_name = item["food_name"]
        food = self.food_db.get(food_name, {})
        base_cal = float(food.get("calories", 0))
        base_prot = float(food.get("protein", 0))
        qty = float(item.get("quantity", 0))
        base_qty = self._base_qty(food_name)
        scale = qty / (base_qty or 1.0)
        cal_per_unit = base_cal / (base_qty or 1.0)
        prot_per_unit = base_prot / (base_qty or 1.0)
        return {
            "calories": base_cal * scale,
            "protein": base_prot * scale,
            "calorie_density": cal_per_unit,
            "protein_density": prot_per_unit,
            "protein_cal_ratio": prot_per_unit / (cal_per_unit or 0.001),
        }

    def _recalc_meal_totals(self, meal: Dict[str, Any]) -> None:
        items = meal.get("foods_with_portions", [])
        meal["actual_calories"] = round(sum(self._item_macros(i)["calories"] for i in items))
        meal["actual_protein"] = round(sum(self._item_macros(i)["protein"] for i in items), 1)
        for item in items:
            macros = self._item_macros(item)
            item["calories"] = round(macros["calories"])
            item["protein"] = round(macros["protein"], 1)

    def _daily_totals(self, plan: Dict[str, Any]) -> Dict[str, float]:
        total_cal = 0.0
        total_prot = 0.0
        for meal_name in self.MEAL_ORDER:
            meal = plan.get(meal_name, {})
            total_cal += meal.get("actual_calories", 0)
            total_prot += meal.get("actual_protein", 0.0)
        return {"calories": total_cal, "protein": total_prot}

    def _apply_step(self, item: Dict[str, Any], direction: int) -> bool:
        food_name = item["food_name"]
        min_q, max_q, step_q, norm_unit = self._constraint_for(food_name)
        current = float(item["quantity"])
        new_qty = current + direction * step_q
        if new_qty < min_q or new_qty > max_q:
            return False
        display_qty = int(new_qty) if norm_unit in ["g", "ml"] else round(new_qty, 1)
        item["quantity"] = display_qty
        item["display"] = (
            f"{display_qty} units" if norm_unit == "unit" else f"{display_qty} {norm_unit}"
        )
        item["unit"] = norm_unit
        return True

    def _iter_items(self, plan: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
        items = []
        for meal_name in self.MEAL_ORDER:
            for item in plan[meal_name].get("foods_with_portions", []):
                items.append((meal_name, item))
        return items

    def _reduce_calories(self, plan: Dict[str, Any]) -> bool:
        candidates = []
        for meal_name, item in self._iter_items(plan):
            macros = self._item_macros(item)
            candidates.append((macros["protein_cal_ratio"], macros["calories"], meal_name, item))
        candidates.sort(key=lambda x: (x[0], -x[1]))
        for _, _, meal_name, item in candidates:
            if self._apply_step(item, -1):
                self._recalc_meal_totals(plan[meal_name])
                return True
        return False

    def _increase_calories(self, plan: Dict[str, Any]) -> bool:
        candidates = []
        for meal_name, item in self._iter_items(plan):
            macros = self._item_macros(item)
            headroom = self._constraint_for(item["food_name"])[1] - float(item["quantity"])
            if headroom <= 0:
                continue
            candidates.append((macros["protein_cal_ratio"], macros["calorie_density"], meal_name, item))
        candidates.sort(key=lambda x: (x[0], -x[1]))
        for _, _, meal_name, item in candidates:
            if self._apply_step(item, 1):
                self._recalc_meal_totals(plan[meal_name])
                return True
        return False

    def _increase_protein(self, plan: Dict[str, Any]) -> bool:
        candidates = []
        for meal_name, item in self._iter_items(plan):
            macros = self._item_macros(item)
            headroom = self._constraint_for(item["food_name"])[1] - float(item["quantity"])
            if headroom <= 0:
                continue
            candidates.append((macros["protein_cal_ratio"], meal_name, item))
        candidates.sort(key=lambda x: x[0], reverse=True)
        for _, meal_name, item in candidates:
            if self._apply_step(item, 1):
                self._recalc_meal_totals(plan[meal_name])
                return True
        return False

    def _reduce_protein(self, plan: Dict[str, Any]) -> bool:
        candidates = []
        for meal_name, item in self._iter_items(plan):
            macros = self._item_macros(item)
            candidates.append((macros["protein_cal_ratio"], macros["protein_density"], meal_name, item))
        candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
        for _, _, meal_name, item in candidates:
            if self._apply_step(item, -1):
                self._recalc_meal_totals(plan[meal_name])
                return True
        return False

    def rebalance(
        self,
        portion_plan: Dict[str, Any],
        target_calories: float,
        target_protein: float,
        max_passes: int = 300,
    ) -> Dict[str, Any]:
        plan = {
            meal: dict(portion_plan.get(meal, {}))
            for meal in self.MEAL_ORDER
        }
        plan["repetition_counts"] = dict(portion_plan.get("repetition_counts", {}))

        for meal_name in self.MEAL_ORDER:
            meal = plan[meal_name]
            meal["foods_with_portions"] = [
                dict(item) for item in meal.get("foods_with_portions", [])
            ]
            self._recalc_meal_totals(meal)

        for _ in range(max_passes):
            totals = self._daily_totals(plan)
            cal_gap = target_calories - totals["calories"]
            prot_gap = target_protein - totals["protein"]
            cal_ok = abs(cal_gap) / (target_calories or 1.0) <= self.CAL_TOLERANCE
            prot_ok = abs(prot_gap) / (target_protein or 1.0) <= self.PROTEIN_TOLERANCE
            if cal_ok and prot_ok:
                break

            improved = False

            if cal_gap < -1 and not cal_ok:
                improved = self._reduce_calories(plan)
            elif prot_gap > 0.5 and not prot_ok:
                improved = self._increase_protein(plan)
            elif cal_gap > 1 and not cal_ok and prot_gap <= 0:
                improved = self._increase_calories(plan)
            elif prot_gap < -0.5 and not prot_ok and cal_gap >= -1:
                improved = self._reduce_protein(plan)

            if not improved:
                break

        return plan
