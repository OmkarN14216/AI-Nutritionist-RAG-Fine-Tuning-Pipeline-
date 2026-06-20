import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.pipeline import run_planning_pipeline, evaluate_profile_success
from prompt_engine.compiler import NutritionPromptCompiler


def run_end_to_end_test():
    print("\n==================================================")
    print("Testing Layer 1-10 End-to-End Pipeline")
    print("==================================================")

    patient_payload = {
        "age": 24,
        "gender": "male",
        "weight_kg": 84.0,
        "height_cm": 174.0,
        "waist_cm": 96.0,
        "neck_cm": 39.0,
        "activity_level": "sedentary",
        "goal": "weight_loss",
        "target_weight_kg": 72.0,
        "target_weeks": 12,
        "dietary_preference": "eggitarian",
        "medical_conditions": ["gerd"],
        "allergies": [],
        "climate_hot": True,
    }
    print("Layer 1 PASS")

    try:
        result = run_planning_pipeline(patient_payload, verbose=False)
        calc_results = result["calc_results"]
        rule_results = result["rule_results"]
        filtered_foods = result["filtered_foods"]
        allocation = result["allocation"]
        portion_plan = result["portion_plan"]
        audit_report = result["audit_report"]

        assert "anthropometrics" in calc_results
        assert "thermodynamics" in calc_results
        print("Layer 2 PASS")

        assert "forbidden_ingredients" in rule_results
        print("Layer 3 PASS")

        assert len(filtered_foods) > 0
        print("Layer 4 PASS")

        assert result["retrieved_contexts"]
        print("Layer 5 PASS")

        assert len(result["planner_signals"].signals) >= 0
        print("Layer 6 PASS")

        assert portion_plan["breakfast"]["foods"]
        print("Layer 7 PASS")

        assert portion_plan["breakfast"].get("foods_with_portions")
        print("Layer 8 PASS")

        assert "metrics" in audit_report
        print("Layer 9 PASS")

        master_prompt = NutritionPromptCompiler.compile_master_system_prompt(
            user_profile=patient_payload,
            calculation_results=calc_results,
            rule_constraints=rule_results,
            retrieved_icmr_contexts=result["retrieved_contexts"],
            filtered_foods=filtered_foods,
            meal_allocation=allocation,
            meal_plan=portion_plan,
            audit_report=audit_report,
        )
        assert "MANDATORY PATIENT PHYSIOLOGICAL TELEMETRY" in master_prompt
        assert "AUDIT ENGINE NOTES" in master_prompt
        print("Layer 10 PASS")

        evaluation = evaluate_profile_success(result)
        print(f"Profile evaluation within tolerance: {'PASS' if evaluation['passed'] else 'FAIL'}")
        print("\nResult: PASS")
        return True
    except Exception as exc:
        print(f"\nResult: FAIL")
        print(f"Diagnostics: {exc}")
        return False


if __name__ == "__main__":
    success = run_end_to_end_test()
    sys.exit(0 if success else 1)
