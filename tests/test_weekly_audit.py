import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.pipeline import run_weekly_planning_pipeline


def test_weekly_audit():
    print("\n==================================================")
    print("Testing Weekly Audit")
    print("==================================================")

    profile = {
        "age": 35,
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

    try:
        result = run_weekly_planning_pipeline(profile, verbose=False)
        audit = result["weekly_audit_report"]

        assert "daily_diagnostics" in audit
        assert "weekly_repetition_diagnostics" in audit
        assert "diversity_diagnostics" in audit
        assert len(audit["daily_diagnostics"]) == 7
        assert audit["passed"] is True
        assert audit["weekly_repetition_diagnostics"]["within_limits"] is True

        print(f"Weekly audit passed: {audit['passed']}")
        print("\nResult: PASS")
        return True
    except Exception as exc:
        print("\nResult: FAIL")
        print(f"Diagnostics: {exc}")
        return False


if __name__ == "__main__":
    success = test_weekly_audit()
    sys.exit(0 if success else 1)
