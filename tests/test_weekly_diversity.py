import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.pipeline import run_weekly_planning_pipeline


def test_weekly_diversity():
    print("\n==================================================")
    print("Testing Weekly Diversity")
    print("==================================================")

    profile = {
        "age": 28,
        "gender": "female",
        "weight_kg": 65.0,
        "height_cm": 165.0,
        "waist_cm": 78.0,
        "neck_cm": 33.0,
        "hip_cm": 92.0,
        "activity_level": "sedentary",
        "goal": "weight_loss",
        "target_weight_kg": 58.0,
        "target_weeks": 12,
        "dietary_preference": "eggitarian",
        "medical_conditions": [],
        "allergies": [],
        "climate_hot": True,
    }

    try:
        result = run_weekly_planning_pipeline(profile, verbose=False)
        audit = result["weekly_audit_report"]
        diversity = audit["diversity_diagnostics"]

        assert diversity["metrics"]["protein_sources"] >= 4
        assert diversity["metrics"]["fruit_variety"] >= 3
        assert diversity["metrics"]["vegetable_variety"] >= 4
        assert diversity["metrics"]["regional_variety"] >= 3

        print(f"Diversity metrics: {diversity['metrics']}")
        print("\nResult: PASS")
        return True
    except Exception as exc:
        print("\nResult: FAIL")
        print(f"Diagnostics: {exc}")
        return False


if __name__ == "__main__":
    success = test_weekly_diversity()
    sys.exit(0 if success else 1)
