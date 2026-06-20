import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.audit_engine import AuditEngine


def test_audit_validation():
    print("\n==================================================")
    print("Testing Layer 9: Audit Engine")
    print("==================================================")

    user_profile = {
        "medical_conditions": ["gerd"],
        "allergies": [],
        "dietary_preference": "eggitarian",
    }

    calc_results = {
        "thermodynamics": {"target_dietary_calories_kcal": 2000.0},
        "target_macronutrients_absolute": {"protein_grams": 100.0},
    }

    rule_constraints = {
        "forbidden_ingredients": ["tomato", "raw onions", "garlic"],
        "soft_restrictions": [],
    }

    portion_plan_pass = {
        "breakfast": {
            "foods": ["Poha", "Curd"],
            "target_calories": 500,
            "target_protein": 25.0,
            "actual_calories": 500,
            "actual_protein": 25.0,
        },
        "lunch": {
            "foods": ["Brown Rice", "Paneer"],
            "target_calories": 700,
            "target_protein": 35.0,
            "actual_calories": 700,
            "actual_protein": 35.0,
        },
        "snack": {
            "foods": ["Oats"],
            "target_calories": 200,
            "target_protein": 10.0,
            "actual_calories": 200,
            "actual_protein": 10.0,
        },
        "dinner": {
            "foods": ["Roti", "Egg White"],
            "target_calories": 600,
            "target_protein": 30.0,
            "actual_calories": 600,
            "actual_protein": 30.0,
        },
    }

    portion_plan_fail_forbidden = {
        "breakfast": {
            "foods": ["Poha", "Tomato"],
            "target_calories": 500,
            "target_protein": 25.0,
            "actual_calories": 500,
            "actual_protein": 25.0,
        },
        "lunch": {
            "foods": ["Brown Rice", "Paneer"],
            "target_calories": 700,
            "target_protein": 35.0,
            "actual_calories": 700,
            "actual_protein": 35.0,
        },
        "snack": {
            "foods": ["Oats"],
            "target_calories": 200,
            "target_protein": 10.0,
            "actual_calories": 200,
            "actual_protein": 10.0,
        },
        "dinner": {
            "foods": ["Roti", "Egg White"],
            "target_calories": 600,
            "target_protein": 30.0,
            "actual_calories": 600,
            "actual_protein": 30.0,
        },
    }

    try:
        engine = AuditEngine(user_profile, calc_results, rule_constraints, verbose=False)

        report_pass = engine.run_audit(portion_plan_pass)
        assert report_pass["passed"] is True
        assert "metrics" in report_pass
        assert report_pass["metrics"]["calories_within_tolerance"] is True
        assert report_pass["metrics"]["protein_within_tolerance"] is True
        assert "meal_diagnostics" in report_pass
        assert "repetition_diagnostics" in report_pass

        report_fail = engine.run_audit(portion_plan_fail_forbidden)
        assert report_fail["passed"] is False
        assert report_fail["medical_diagnostics"]["count"] >= 1

        print("Structured metrics present: PASS")
        print("Forbidden food detection: PASS")
        print("\nResult: PASS")
        return True
    except Exception as exc:
        print("\nResult: FAIL")
        print(f"Diagnostics: {exc}")
        return False


if __name__ == "__main__":
    success = test_audit_validation()
    sys.exit(0 if success else 1)
