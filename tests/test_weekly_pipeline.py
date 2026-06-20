import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.pipeline import run_weekly_planning_pipeline


def test_weekly_pipeline():
    print("\n==================================================")
    print("Testing Weekly Pipeline")
    print("==================================================")

    profile = {
        "age": 45,
        "gender": "female",
        "weight_kg": 78.0,
        "height_cm": 160.0,
        "waist_cm": 88.0,
        "neck_cm": 34.0,
        "hip_cm": 98.0,
        "activity_level": "sedentary",
        "goal": "weight_loss",
        "target_weight_kg": 65.0,
        "target_weeks": 12,
        "dietary_preference": "veg",
        "medical_conditions": ["diabetes"],
        "allergies": [],
        "climate_hot": True,
    }

    try:
        result = run_weekly_planning_pipeline(profile, verbose=False)
        assert result["weekly_plan"]["days"][0]["portion_plan"]["breakfast"]["foods"]
        assert result["weekly_audit_report"]["weekly_repetition_diagnostics"]["within_limits"]
        assert result["rule_results"]["forbidden_ingredients"]

        print("Weekly pipeline artifacts present: PASS")
        print("\nResult: PASS")
        return True
    except Exception as exc:
        print("\nResult: FAIL")
        print(f"Diagnostics: {exc}")
        return False


if __name__ == "__main__":
    success = test_weekly_pipeline()
    sys.exit(0 if success else 1)
