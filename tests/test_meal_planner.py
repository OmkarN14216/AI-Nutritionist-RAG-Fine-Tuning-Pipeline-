import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.food_loader import FoodDatabase
from core.food_filter import FoodFilter
from core.guideline_interpreter import GuidelineInterpreter
from core.meal_planner import MealPlanner


def test_meal_planner():
    print("\n==================================================")
    print("Testing Layer 7: Meal Planner")
    print("==================================================")

    try:
        food_db = FoodDatabase()
        foods = food_db.get_all_foods()
        filtered_foods = FoodFilter.filter_foods(foods, ["Egg"])

        allocation = MealPlanner.allocate_calories(1800)
        assert allocation["breakfast"] + allocation["lunch"] + allocation["snack"] + allocation["dinner"] > 0

        signals = GuidelineInterpreter.extract_planner_signals(
            ["Include whole grains and pulses daily."]
        )

        meal_plan = MealPlanner.generate_meal_plan(
            filtered_foods,
            allocation,
            target_protein=80.0,
            active_conditions=["weight_loss"],
            rag_food_bonuses=signals,
            enable_rag_scoring=True,
        )

        for meal_name in ["breakfast", "lunch", "snack", "dinner"]:
            meal = meal_plan[meal_name]
            assert isinstance(meal["foods"], list)
            assert meal["target_calories"] > 0
            assert len(meal["foods"]) <= MealPlanner.MAX_ITEMS_BY_MEAL[meal_name]

        snack = meal_plan["snack"]
        assert len(snack["foods"]) <= 2
        assert snack["target_protein"] <= MealPlanner.SNACK_PROTEIN_ABSOLUTE_CAP
        assert "Soy Chunks" not in snack["foods"] or len(snack["foods"]) == 1

        print(f"Breakfast foods: {meal_plan['breakfast']['foods']}")
        print(f"Snack foods: {snack['foods']} (target protein {snack['target_protein']}g)")
        print(f"Dinner foods: {meal_plan['dinner']['foods']}")
        print("\nResult: PASS")
        return True
    except Exception as exc:
        print("\nResult: FAIL")
        print(f"Diagnostics: {exc}")
        return False


if __name__ == "__main__":
    success = test_meal_planner()
    sys.exit(0 if success else 1)
