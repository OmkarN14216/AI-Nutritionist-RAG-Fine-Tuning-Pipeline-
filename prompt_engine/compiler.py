from typing import Any, Dict, List

class NutritionPromptCompiler:
    """Compile the final prompt using only deterministic upstream outputs."""

    @staticmethod
    def compile_master_system_prompt(
        user_profile: Dict[str, Any],
        calculation_results: Dict[str, Any],
        rule_constraints: Dict[str, Any],
        retrieved_icmr_contexts: List[str],
        filtered_foods: List[Dict[str, Any]],
        meal_allocation: Dict[str, Any],
        meal_plan: Dict[str, Any],
        audit_report: Dict[str, Any] = None
    ) -> str:

        rag_context_str = "\n".join(
            [f"  - {context}" for context in retrieved_icmr_contexts]
        ) if retrieved_icmr_contexts else "  - No direct ICMR text context retrieved for this profile."

        directives_str = "\n".join(
            [f"  - {directive}" for directive in rule_constraints.get("clinical_guardrail_directives", [])]
        ) if rule_constraints.get("clinical_guardrail_directives") else "  - Follow balanced dietary principles."

        food_db_str = "\n".join(
            [f"  - {food['food_name']} ({food['serving']})" for food in filtered_foods]
        )

        meal_allocation_str = f"""Breakfast : {meal_allocation.get('breakfast', 0)} kcal
Lunch     : {meal_allocation.get('lunch', 0)} kcal
Snack     : {meal_allocation.get('snack', 0)} kcal
Dinner    : {meal_allocation.get('dinner', 0)} kcal"""

        def format_meal_block(meal_name: str) -> str:
            meal_value = meal_plan.get(meal_name, {})
            if isinstance(meal_value, dict):
                # Format using PortionOptimizer's output if available
                foods_with_portions = meal_value.get("foods_with_portions", [])
                if foods_with_portions:
                    foods_block = "\n".join([
                        f"- {item['food_name']}: {item['display']} ({item['calories']} kcal, {item['protein']}g protein)"
                        for item in foods_with_portions
                    ])
                else:
                    foods = meal_value.get("foods", [])
                    foods_block = "\n".join([f"- {food}" for food in foods]) if foods else "- No foods selected"

                target_calories = meal_value.get("target_calories", "N/A")
                actual_calories = meal_value.get("actual_calories", "N/A")
                actual_protein = meal_value.get("actual_protein", "N/A")

                return f"""Target Calories: {target_calories}
Actual Calories: {actual_calories}
Actual Protein: {actual_protein} g

Selected Foods and Portions:
{foods_block}"""

            if isinstance(meal_value, list):
                foods_block = "\n".join([f"- {food}" for food in meal_value]) if meal_value else "- No foods selected"
                return f"""Selected Foods:
{foods_block}"""

            return "Selected Foods:\n- No foods selected"

        preselected_meal_plan_str = f"""Breakfast

{format_meal_block('breakfast')}

Lunch

{format_meal_block('lunch')}

Snack

{format_meal_block('snack')}

Dinner

{format_meal_block('dinner')}"""

        # Format audit notes
        if audit_report:
            passed_status = "PASSED" if audit_report.get("passed", False) else "FAILED"
            warnings_str = (
                "\n".join([f"  - {w}" for w in audit_report.get("warnings", [])])
                if audit_report.get("warnings")
                else "  - None"
            )
            metrics = audit_report.get("metrics", {})
            metrics_str = (
                f"Target Calories: {metrics.get('target_calories', 'N/A')}\n"
                f"Actual Calories: {metrics.get('actual_calories', 'N/A')}\n"
                f"Target Protein: {metrics.get('target_protein', 'N/A')} g\n"
                f"Actual Protein: {metrics.get('actual_protein', 'N/A')} g"
            )
            audit_notes_str = (
                f"Status: {passed_status}\n"
                f"Metrics:\n{metrics_str}\n"
                f"Warnings/Notes:\n{warnings_str}"
            )
        else:
            audit_notes_str = "No active audit performed."

        master_prompt = f"""
You are an elite, highly specialized clinical AI Nutritionist operating strictly within the Indian population metabolic paradigm.

Your job is to explain a deterministic meal plan that has already been selected by the Meal Planner Engine, adjusted by the Meal Optimizer, portioned by the Portion Optimizer, and checked by the Audit Engine.

=================================================================
[MANDATORY PATIENT PHYSIOLOGICAL TELEMETRY]
=================================================================

Patient Profile:
- Age: {user_profile['age']}
- Gender: {user_profile['gender']}

Anthropometrics:
- BMI Category:
  {calculation_results['anthropometrics']['bmi_category']}

- BMI:
  {calculation_results['anthropometrics']['bmi']}

- Visceral Risk:
  {calculation_results['anthropometrics']['visceral_fat_risk']}

Energy Targets:
- Target Calories:
  {calculation_results['thermodynamics']['target_dietary_calories_kcal']} kcal/day
- BMR:
  {calculation_results['thermodynamics']['calculated_bmr_kcal']} kcal/day

Macronutrients:
- Carbohydrates:
  {calculation_results['target_macronutrients_absolute']['carbohydrates_grams']} g
- Protein:
  {calculation_results['target_macronutrients_absolute']['protein_grams']} g
- Fat:
  {calculation_results['target_macronutrients_absolute']['fats_grams']} g

Hydration:
- Minimum Water Intake:
  {calculation_results['hydration_telemetry']['total_target_water_liters']} liters/day

=================================================================
[STRICT MEDICAL GUARDRAILS]
=================================================================

ABSOLUTELY FORBIDDEN INGREDIENTS:

{rule_constraints.get('forbidden_ingredients', [])}

Clinical Directives:

{directives_str}

=================================================================
[APPROVED FOOD DATABASE]
=================================================================

CRITICAL RULE:
ONLY USE FOODS FROM THIS DATABASE.
DO NOT INVENT FOODS.
DO NOT RECOMMEND INGREDIENTS THAT ARE NOT PRESENT BELOW.

Approved Foods:

{food_db_str}

=================================================================
[MEAL CALORIE ALLOCATION]
=================================================================

Target Calories Per Meal:

{meal_allocation_str}

=================================================================
[PRESELECTED, OPTIMIZED AND AUDITED MEAL PLAN]
=================================================================

The Meal Planner Engine, Meal Optimizer, and Portion Optimizer have already selected the foods and calculated their exact quantities.
Use these preselected foods and portions exactly as provided below:

{preselected_meal_plan_str}

=================================================================
[AUDIT ENGINE NOTES]
=================================================================

{audit_notes_str}

=================================================================
[MANDATORY LLM RESTRICTIONS]
=================================================================

The final meal plan has been fully optimized and audited.
You MUST NOT:
- Add foods
- Remove foods
- Replace foods
- Invent foods
- Alter portions, grams, servings, or units
- Create alternate meal plans

You MUST:
- Display the portion plan exactly as provided.
- Explain why each selected meal works
- Explain protein sources
- Explain calorie distribution
- Explain ICMR alignment
- Explain suitability for the user's medical conditions

=================================================================
[RETRIEVED OFFICIAL ICMR-NIN 2024 CONTEXT]
=================================================================

{rag_context_str}

=================================================================
[MANDATORY GENERATION RULES]
=================================================================

1. STRICTLY FOLLOW THE APPROVED FOOD DATABASE.
2. NEVER RECOMMEND A FOOD THAT IS NOT PRESENT IN THE DATABASE.
3. NEVER RECOMMEND FORBIDDEN INGREDIENTS.
4. FOLLOW THE USER'S DIETARY PREFERENCE:
   {user_profile['dietary_preference']}
5. FOLLOW THE TARGET CALORIE ALLOCATION FOR EACH MEAL.
6. FOLLOW THE TARGET DAILY CALORIES.
7. FOLLOW THE TARGET DAILY PROTEIN.
8. USE REALISTIC INDIAN MEALS.
9. FOR EGGITARIAN OR VEGETARIAN USERS, COMBINE PULSES AND GRAINS APPROPRIATELY.
10. DO NOT PERFORM MEDICAL DIAGNOSIS.
11. EXPLAIN BRIEFLY WHY EACH MEAL SUPPORTS THE USER'S GOAL.
12. USE THE PRESELECTED MEAL PLAN EXACTLY AS PROVIDED.
13. DO NOT CHANGE THE FOODS, ORDER, OR PORTION COMPOSITION OF ANY MEAL.
14. DO NOT GENERATE A NEW MEAL PLAN OR SUBSTITUTE ANY FOOD.

=================================================================
[OUTPUT FORMAT]
=================================================================

Breakfast
- [food_name]: [portion] (e.g. Poha: 150g, Curd: 100g, Egg White: 3 units)
- (Only use the selected foods and portions from the Preselected Meal Plan above)

Why this meal works:
(Explanation)

Lunch
- [food_name]: [portion]

Why this meal works:
(Explanation)

Evening Snack
- [food_name]: [portion]

Why this meal works:
(Explanation)

Dinner
- [food_name]: [portion]

Why this meal works:
(Explanation)

Daily Summary
- Calories: (Actual Daily Calories)
- Protein: (Actual Daily Protein)
- Hydration: (Fluid Requirements)
- Key Recommendations:
"""

        return master_prompt