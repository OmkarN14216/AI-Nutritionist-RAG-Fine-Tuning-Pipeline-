"""
Deterministic nutrition pipeline orchestrator.
Layers 2-9 wired in sequence; Layer 1 intake is passed in as user_payload.
"""
from typing import Any, Dict, List, Optional

from core.patient_intake import validate_patient_intake
from core.audit_engine import AuditEngine
from core.calculator import EliteNutritionEngine
from core.daily_rebalance import DailyRebalanceEngine
from core.food_filter import FoodFilter
from core.food_loader import FoodDatabase
from core.guideline_interpreter import GuidelineInterpreter
from core.meal_optimizer import MealOptimizer
from core.meal_planner import MealPlanner
from core.portion_optimizer import PortionOptimizer
from core.rule_engine import GuardrailRuleEngine
from core.weekly_planner import WeeklyPlanner


DEFAULT_MOCK_CONTEXTS = [
    "[ICMR Manual - Page 12]: Patients should consume whole grains, cereals, and millets for fiber.",
    "[ICMR Manual - Page 45]: Increase protein sources like tofu, egg white, paneer, and pulses.",
]


PROFILES = [
    {
        "name": "GERD + Weight Loss (eggitarian)",
        "age": 24, "gender": "male", "weight_kg": 84.0, "height_cm": 174.0,
        "goal": "weight_loss", "dietary_preference": "eggitarian",
        "medical_conditions": ["gerd"], "target_weight_kg": 72.0,
    },
    {
        "name": "Diabetes + Weight Loss (vegetarian)",
        "age": 45, "gender": "female", "weight_kg": 78.0, "height_cm": 160.0,
        "hip_cm": 98.0,
        "goal": "weight_loss", "dietary_preference": "veg",
        "medical_conditions": ["diabetes"], "target_weight_kg": 65.0,
    },
    {
        "name": "Standard Vegetarian Maintenance",
        "age": 30, "gender": "male", "weight_kg": 70.0, "height_cm": 175.0,
        "goal": "maintenance", "dietary_preference": "veg",
        "medical_conditions": [], "target_weight_kg": 70.0,
    },
    {
        "name": "Standard Eggitarian Weight Loss",
        "age": 28, "gender": "female", "weight_kg": 65.0, "height_cm": 165.0,
        "hip_cm": 92.0,
        "goal": "weight_loss", "dietary_preference": "eggitarian",
        "medical_conditions": [], "target_weight_kg": 58.0,
    },
    {
        "name": "Strict Vegan Weight Loss",
        "age": 32, "gender": "male", "weight_kg": 82.0, "height_cm": 180.0,
        "goal": "weight_loss", "dietary_preference": "vegan",
        "medical_conditions": [], "target_weight_kg": 74.0,
    },
    {
        "name": "Muscle Gain (eggitarian)",
        "age": 25, "gender": "male", "weight_kg": 70.0, "height_cm": 178.0,
        "goal": "weight_gain", "dietary_preference": "eggitarian",
        "medical_conditions": [], "target_weight_kg": 75.0,
    },
    {
        "name": "Senior Citizen Weight Maintenance",
        "age": 70, "gender": "female", "weight_kg": 62.0, "height_cm": 158.0,
        "hip_cm": 95.0,
        "goal": "maintenance", "dietary_preference": "veg",
        "medical_conditions": [], "target_weight_kg": 62.0,
    },
    {
        "name": "Hypertension (vegetarian)",
        "age": 50, "gender": "male", "weight_kg": 85.0, "height_cm": 172.0,
        "goal": "weight_loss", "dietary_preference": "veg",
        "medical_conditions": ["hypertension"], "target_weight_kg": 75.0,
    },
    {
        "name": "Obese Male Weight Loss",
        "age": 35, "gender": "male", "weight_kg": 115.0, "height_cm": 176.0,
        "waist_cm": 112.0, "neck_cm": 42.0,
        "goal": "weight_loss", "dietary_preference": "eggitarian",
        "medical_conditions": [], "target_weight_kg": 85.0,
    },
    {
        "name": "Obese Female Weight Loss",
        "age": 33, "gender": "female", "weight_kg": 98.0, "height_cm": 162.0,
        "waist_cm": 105.0, "neck_cm": 38.0, "hip_cm": 112.0,
        "goal": "weight_loss", "dietary_preference": "veg",
        "medical_conditions": [], "target_weight_kg": 70.0,
    },
    {
        "name": "Normal BMI Maintenance (Jain)",
        "age": 27, "gender": "female", "weight_kg": 54.0, "height_cm": 162.0,
        "hip_cm": 90.0,
        "goal": "maintenance", "dietary_preference": "jain",
        "medical_conditions": [], "target_weight_kg": 54.0,
    },
]


def _build_user_payload(profile: Dict[str, Any]) -> Dict[str, Any]:
    payload = {
        "age": profile.get("age", 30),
        "gender": profile.get("gender", "male"),
        "weight_kg": profile.get("weight_kg", 75.0),
        "height_cm": profile.get("height_cm", 175.0),
        "waist_cm": profile.get("waist_cm", 85.0),
        "neck_cm": profile.get("neck_cm", 38.0),
        "hip_cm": profile.get("hip_cm", None),
        "activity_level": profile.get("activity_level", "sedentary"),
        "goal": profile.get("goal", "weight_loss"),
        "target_weight_kg": profile.get("target_weight_kg", 68.0),
        "target_weeks": profile.get("target_weeks", 12),
        "dietary_preference": profile.get("dietary_preference", "veg"),
        "medical_conditions": profile.get("medical_conditions", []),
        "allergies": profile.get("allergies", []),
        "climate_hot": profile.get("climate_hot", True),
    }
    return validate_patient_intake(payload)


def run_planning_pipeline(
    user_payload: Dict[str, Any],
    retrieved_contexts: Optional[List[str]] = None,
    enable_rag_scoring: bool = True,
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Execute Layers 2-9 for a patient profile.
    Returns structured artifacts for audit, explanation, and testing.
    """
    contexts = retrieved_contexts if retrieved_contexts is not None else DEFAULT_MOCK_CONTEXTS

    calc_results = EliteNutritionEngine.generate_comprehensive_profile(user_payload)

    rule_engine = GuardrailRuleEngine(config_path="config/rules.json")
    rule_results = rule_engine.compile_user_constraints(
        medical_flags=user_payload.get("medical_conditions", []),
        allergy_flags=user_payload.get("allergies", []),
        dietary_pref=user_payload.get("dietary_preference", "veg"),
    )

    food_db = FoodDatabase()
    foods = food_db.get_all_foods()
    filtered_foods = FoodFilter.filter_foods(foods, rule_results["forbidden_ingredients"])

    planner_signals = GuidelineInterpreter.extract_planner_signals(contexts)

    allocation = MealPlanner.allocate_calories(
        calc_results["thermodynamics"]["target_dietary_calories_kcal"]
    )
    target_protein = calc_results["target_macronutrients_absolute"]["protein_grams"]
    active_conditions = list(
        dict.fromkeys(user_payload.get("medical_conditions", []) + [user_payload.get("goal", "")])
    )

    meal_plan = MealPlanner.generate_meal_plan(
        filtered_foods,
        allocation,
        target_protein,
        active_conditions=active_conditions,
        rag_food_bonuses=planner_signals,
        enable_rag_scoring=enable_rag_scoring,
    )

    meal_optimizer = MealOptimizer(filtered_foods, verbose=verbose)
    optimized_plan = meal_optimizer.optimize_meal_plan(meal_plan)

    portion_optimizer = PortionOptimizer(filtered_foods, verbose=verbose)
    portion_plan = portion_optimizer.optimize_portions(optimized_plan)

    rebalancer = DailyRebalanceEngine(filtered_foods, PortionOptimizer.CONSTRAINTS)
    portion_plan = rebalancer.rebalance(
        portion_plan,
        target_calories=calc_results["thermodynamics"]["target_dietary_calories_kcal"],
        target_protein=target_protein,
    )

    audit_engine = AuditEngine(
        user_profile=user_payload,
        calculation_results=calc_results,
        rule_constraints=rule_results,
        verbose=verbose,
    )
    audit_report = audit_engine.run_audit(portion_plan)

    return {
        "user_payload": user_payload,
        "calc_results": calc_results,
        "rule_results": rule_results,
        "filtered_foods": filtered_foods,
        "planner_signals": planner_signals,
        "allocation": allocation,
        "meal_plan": meal_plan,
        "optimized_plan": optimized_plan,
        "portion_plan": portion_plan,
        "audit_report": audit_report,
        "retrieved_contexts": contexts,
    }


def run_weekly_planning_pipeline(
    user_payload: Dict[str, Any],
    retrieved_contexts: Optional[List[str]] = None,
    enable_rag_scoring: bool = True,
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Execute deterministic Layers 2-9 for a seven-day plan.
    The LLM remains outside this function and cannot mutate foods or portions.
    """
    contexts = retrieved_contexts if retrieved_contexts is not None else DEFAULT_MOCK_CONTEXTS

    calc_results = EliteNutritionEngine.generate_comprehensive_profile(user_payload)

    rule_engine = GuardrailRuleEngine(config_path="config/rules.json")
    rule_results = rule_engine.compile_user_constraints(
        medical_flags=user_payload.get("medical_conditions", []),
        allergy_flags=user_payload.get("allergies", []),
        dietary_pref=user_payload.get("dietary_preference", "veg"),
    )

    food_db = FoodDatabase()
    foods = food_db.get_all_foods()
    filtered_foods = FoodFilter.filter_foods(foods, rule_results["forbidden_ingredients"])

    planner_signals = GuidelineInterpreter.extract_planner_signals(contexts)
    active_conditions = list(
        dict.fromkeys(user_payload.get("medical_conditions", []) + [user_payload.get("goal", "")])
    )

    weekly_planner = WeeklyPlanner(
        filtered_foods=filtered_foods,
        calculation_results=calc_results,
        rule_results=rule_results,
        active_conditions=active_conditions,
        rag_food_bonuses=planner_signals,
        enable_rag_scoring=enable_rag_scoring,
        verbose=verbose,
    )
    weekly_plan = weekly_planner.generate_weekly_plan()

    return {
        "user_payload": user_payload,
        "calc_results": calc_results,
        "rule_results": rule_results,
        "filtered_foods": filtered_foods,
        "planner_signals": planner_signals,
        "weekly_plan": weekly_plan,
        "weekly_audit_report": weekly_plan["weekly_audit_report"],
        "retrieved_contexts": contexts,
    }


def evaluate_profile_success(result: Dict[str, Any], tolerance: float = 0.10) -> Dict[str, Any]:
    """Profile-level PASS/FAIL diagnostics used by the profile suite."""
    calc_results = result["calc_results"]
    portion_plan = result["portion_plan"]
    rule_results = result["rule_results"]
    audit_report = result["audit_report"]

    target_cal = calc_results["thermodynamics"]["target_dietary_calories_kcal"]
    target_prot = calc_results["target_macronutrients_absolute"]["protein_grams"]

    actual_cal = sum(portion_plan[m]["actual_calories"] for m in ["breakfast", "lunch", "snack", "dinner"])
    actual_prot = sum(portion_plan[m]["actual_protein"] for m in ["breakfast", "lunch", "snack", "dinner"])

    cal_err = abs(actual_cal - target_cal) / (target_cal or 1.0)
    prot_err = abs(actual_prot - target_prot) / (target_prot or 1.0)

    forbidden_found = False
    forbidden_set = {item.lower().strip() for item in rule_results["forbidden_ingredients"]}
    for meal in ["breakfast", "lunch", "snack", "dinner"]:
        for food in portion_plan[meal]["foods"]:
            if food.lower().strip() in forbidden_set:
                forbidden_found = True

    diagnostics = {
        "calories": {
            "target": target_cal,
            "actual": actual_cal,
            "deviation_pct": round(cal_err * 100, 1),
            "pass": cal_err <= tolerance,
        },
        "protein": {
            "target": target_prot,
            "actual": round(actual_prot, 1),
            "deviation_pct": round(prot_err * 100, 1),
            "pass": prot_err <= tolerance,
        },
        "forbidden_foods": {
            "ban_count": len(rule_results["forbidden_ingredients"]),
            "pass": not forbidden_found,
        },
        "audit": {
            "passed": audit_report["passed"],
            "pass": audit_report["passed"],
        },
    }

    overall_pass = all(
        diagnostics[key]["pass"]
        for key in ["calories", "protein", "forbidden_foods", "audit"]
    )

    return {
        "passed": overall_pass,
        "diagnostics": diagnostics,
    }


def run_profile_pipeline(profile: Dict[str, Any], verbose: bool = False) -> Dict[str, Any]:
    user_payload = _build_user_payload(profile)
    try:
        result = run_planning_pipeline(user_payload, verbose=verbose)
        evaluation = evaluate_profile_success(result)
        return {
            "name": profile["name"],
            "passed": evaluation["passed"],
            "diagnostics": evaluation["diagnostics"],
            "result": result,
        }
    except Exception as exc:
        return {
            "name": profile["name"],
            "passed": False,
            "error": str(exc),
            "diagnostics": {},
        }
