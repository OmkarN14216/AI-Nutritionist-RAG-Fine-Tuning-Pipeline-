import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.pipeline import run_weekly_planning_pipeline


def test_weekly_planner():
    print("\n==================================================")
    print("Testing Weekly Planner")
    print("==================================================")

    profile = {
        "age": 30,
        "gender": "male",
        "weight_kg": 70.0,
        "height_cm": 175.0,
        "waist_cm": 85.0,
        "neck_cm": 38.0,
        "activity_level": "sedentary",
        "goal": "maintenance",
        "target_weight_kg": 70.0,
        "target_weeks": 12,
        "dietary_preference": "veg",
        "medical_conditions": [],
        "allergies": [],
        "climate_hot": True,
    }

    try:
        result = run_weekly_planning_pipeline(profile, verbose=False)
        weekly_plan = result["weekly_plan"]
        assert len(weekly_plan["days"]) == 7

        for day in weekly_plan["days"]:
            portion_plan = day["portion_plan"]
            for meal in ["breakfast", "lunch", "snack", "dinner"]:
                assert portion_plan[meal]["foods"]
                assert portion_plan[meal].get("foods_with_portions")

        print("Generated days: 7")
        print("\nResult: PASS")
        return True
    except Exception as exc:
        print("\nResult: FAIL")
        print(f"Diagnostics: {exc}")
        return False


if __name__ == "__main__":
    success = test_weekly_planner()
    sys.exit(0 if success else 1)
