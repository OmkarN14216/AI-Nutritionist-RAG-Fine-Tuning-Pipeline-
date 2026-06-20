from typing import Any, Dict, List


class AuditEngine:
    """
    Layer 9: Audit Engine.
    Verifies the portion-optimized diet plan before it is sent to the LLM.
    """

    MEAL_ORDER = ["breakfast", "lunch", "snack", "dinner"]
    CAL_TOLERANCE = 0.05
    PROTEIN_TOLERANCE = 0.05
    MEAL_CAL_TOLERANCE = 0.15
    MAX_REPETITIONS = 2

    def __init__(
        self,
        user_profile: Dict[str, Any],
        calculation_results: Dict[str, Any],
        rule_constraints: Dict[str, Any],
        verbose: bool = True,
    ):
        self.user_profile = user_profile
        self.calculation_results = calculation_results
        self.rule_constraints = rule_constraints
        self.verbose = verbose

    def _log(self, message: str) -> None:
        if self.verbose:
            print(message)

    def run_audit(self, portion_plan: Dict[str, Any]) -> Dict[str, Any]:
        warnings: List[str] = []
        passed = True

        all_foods: List[str] = []
        total_actual_cal = 0
        total_actual_prot = 0.0
        meal_diagnostics: Dict[str, Any] = {}

        target_cal = self.calculation_results["thermodynamics"]["target_dietary_calories_kcal"]
        target_prot = self.calculation_results["target_macronutrients_absolute"]["protein_grams"]

        for meal_name in self.MEAL_ORDER:
            meal = portion_plan.get(meal_name, {})
            foods = meal.get("foods", [])
            all_foods.extend(foods)
            meal_actual_cal = meal.get("actual_calories", 0)
            meal_actual_prot = meal.get("actual_protein", 0.0)
            meal_target_cal = meal.get("target_calories", 0)
            meal_target_prot = meal.get("target_protein", 0.0)
            total_actual_cal += meal_actual_cal
            total_actual_prot += meal_actual_prot

            cal_dev_pct = (
                abs(meal_actual_cal - meal_target_cal) / meal_target_cal * 100
                if meal_target_cal > 0
                else 0.0
            )
            prot_dev_pct = (
                abs(meal_actual_prot - meal_target_prot) / meal_target_prot * 100
                if meal_target_prot > 0
                else 0.0
            )

            meal_diagnostics[meal_name] = {
                "foods": foods,
                "target_calories": meal_target_cal,
                "actual_calories": meal_actual_cal,
                "target_protein": meal_target_prot,
                "actual_protein": meal_actual_prot,
                "calorie_deviation_pct": round(cal_dev_pct, 1),
                "protein_deviation_pct": round(prot_dev_pct, 1),
                "within_calorie_tolerance": cal_dev_pct <= self.MEAL_CAL_TOLERANCE * 100,
            }

        foods_lower = [f.lower().strip() for f in all_foods]
        forbidden_lower = [
            f.lower().strip() for f in self.rule_constraints.get("forbidden_ingredients", [])
        ]

        forbidden_found = [f for f in all_foods if f.lower().strip() in forbidden_lower]
        if forbidden_found:
            warnings.append(f"Forbidden foods present: {', '.join(forbidden_found)}")
            passed = False
        else:
            self._log("  [PASS] Check 1: Forbidden Foods: 0")

        cal_pct_dev = abs(total_actual_cal - target_cal) / (target_cal or 1.0)
        prot_pct_dev = abs(total_actual_prot - target_prot) / (target_prot or 1.0)

        if cal_pct_dev > self.CAL_TOLERANCE:
            warnings.append(
                f"Daily Calories deviation exceeds 5% "
                f"(Target: {target_cal}, Actual: {total_actual_cal}, "
                f"Dev: {round(cal_pct_dev * 100, 1)}%)"
            )
            if cal_pct_dev > 0.10:
                passed = False
        else:
            self._log(f"  [PASS] Check 2: Calories: Target {target_cal}, Actual {total_actual_cal}")

        if prot_pct_dev > self.PROTEIN_TOLERANCE:
            warnings.append(
                f"Daily Protein deviation exceeds 5% "
                f"(Target: {target_prot}g, Actual: {round(total_actual_prot, 1)}g, "
                f"Dev: {round(prot_pct_dev * 100, 1)}%)"
            )
            if prot_pct_dev > 0.10:
                passed = False
        else:
            self._log(
                f"  [PASS] Check 3: Protein: Target {target_prot}g, "
                f"Actual: {round(total_actual_prot, 1)}g"
            )

        for meal_name in self.MEAL_ORDER:
            diag = meal_diagnostics[meal_name]
            if diag["target_calories"] > 0 and not diag["within_calorie_tolerance"]:
                warnings.append(
                    f"{meal_name.capitalize()} calories deviate from target by "
                    f"{diag['calorie_deviation_pct']}% "
                    f"(Target: {diag['target_calories']}, Actual: {diag['actual_calories']})"
                )

        rep_counts: Dict[str, int] = {}
        for food in all_foods:
            rep_counts[food] = rep_counts.get(food, 0) + 1

        excessive_reps = [
            {"food": food, "count": count}
            for food, count in rep_counts.items()
            if count > self.MAX_REPETITIONS
        ]
        repetition_diagnostics = {
            "counts": rep_counts,
            "excessive": excessive_reps,
            "within_limit": len(excessive_reps) == 0,
        }

        if excessive_reps:
            rep_text = ", ".join(f"{r['food']} (used {r['count']} times)" for r in excessive_reps)
            warnings.append(f"Food repetition excessive: {rep_text}")
            passed = False
        else:
            self._log("  [PASS] Check 4: Food Repetitions within limit")

        soft_violations = []
        soft_restrictions = self.rule_constraints.get("soft_restrictions", [])
        for soft_rule in soft_restrictions:
            item = soft_rule["applies_to"].lower().strip()
            if item in foods_lower:
                soft_violations.append(
                    {
                        "food": soft_rule["applies_to"],
                        "condition": soft_rule.get("condition", ""),
                        "restriction": soft_rule.get("restriction", ""),
                    }
                )

        conflict_diagnostics = {
            "soft_violations": soft_violations,
            "count": len(soft_violations),
        }

        if soft_violations:
            violation_text = ", ".join(
                f"{v['food']} (restricted by {v['condition']})" for v in soft_violations
            )
            warnings.append(f"Soft restrictions present in plan: {violation_text}")
        else:
            self._log("  [PASS] Check 5: Rule Conflicts audited")

        med_conditions = [m.lower().strip() for m in self.user_profile.get("medical_conditions", [])]
        med_violations = []

        if "gerd" in med_conditions:
            gerd_triggers = [
                "tomato", "citrus", "lemon", "onion", "garlic", "mint", "pudina",
                "chilli", "caffeine", "coffee", "chai", "garam masala",
            ]
            for food in all_foods:
                if any(trigger in food.lower() for trigger in gerd_triggers):
                    med_violations.append({"food": food, "condition": "gerd"})

        if "diabetes" in med_conditions:
            diabetes_triggers = ["refined sugar", "maida", "honey", "jaggery", "gur", "white rice"]
            for food in all_foods:
                if any(trigger in food.lower() for trigger in diabetes_triggers):
                    med_violations.append({"food": food, "condition": "diabetes"})

        medical_diagnostics = {
            "violations": med_violations,
            "count": len(med_violations),
        }

        if med_violations:
            violation_text = ", ".join(
                f"{v['food']} for {v['condition']} patient" for v in med_violations
            )
            warnings.append(f"Medical violations detected: {violation_text}")
            passed = False
        else:
            self._log("  [PASS] Check 6: Medical Violations: 0")

        metrics = {
            "target_calories": target_cal,
            "actual_calories": total_actual_cal,
            "calorie_deviation_pct": round(cal_pct_dev * 100, 1),
            "target_protein": target_prot,
            "actual_protein": round(total_actual_prot, 1),
            "protein_deviation_pct": round(prot_pct_dev * 100, 1),
            "calories_within_tolerance": cal_pct_dev <= self.CAL_TOLERANCE,
            "protein_within_tolerance": prot_pct_dev <= self.PROTEIN_TOLERANCE,
        }

        macro_diagnostics = {
            "daily": metrics,
            "meals": meal_diagnostics,
        }

        if self.verbose:
            status_str = "PASS" if passed else "FAIL"
            self._log(f"\nAudit Result: {status_str}")
            if warnings:
                self._log("Warnings/Errors:")
                for warning in warnings:
                    self._log(f"  - {warning}")

        return {
            "passed": passed,
            "warnings": warnings,
            "metrics": metrics,
            "meal_diagnostics": meal_diagnostics,
            "repetition_diagnostics": repetition_diagnostics,
            "macro_diagnostics": macro_diagnostics,
            "conflict_diagnostics": conflict_diagnostics,
            "medical_diagnostics": medical_diagnostics,
        }
