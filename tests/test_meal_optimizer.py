import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.meal_optimizer import MealOptimizer


def test_meal_optimization():
    print("\n==================================================")
    print("Testing Layer 7: Meal Optimization Engine")
    print("==================================================")

    mock_filtered_foods = [
        {"food_name": "Poha", "category": "breakfast", "calories": 130, "protein": 2.5, "serving": "100 g cooked"},
        {"food_name": "Curd", "category": "dairy", "calories": 60, "protein": 4.0, "serving": "100 g"},
        {"food_name": "Egg White", "category": "protein", "calories": 17, "protein": 4.0, "serving": "1 egg white"},
        {"food_name": "Milk", "category": "dairy", "calories": 120, "protein": 8.0, "serving": "250 ml"},
        {"food_name": "White Rice", "category": "grain", "calories": 130, "protein": 2.7, "serving": "100 g cooked"},
        {"food_name": "Brown Rice", "category": "grain", "calories": 110, "protein": 2.5, "serving": "100 g cooked"},
        {"food_name": "Roasted Chana", "category": "snack", "calories": 364, "protein": 19.0, "serving": "100 g"},
        {"food_name": "Peanuts", "category": "snack", "calories": 567, "protein": 26.0, "serving": "100 g"},
        {"food_name": "Apple", "category": "fruit", "calories": 52, "protein": 0.3, "serving": "100 g"},
        {"food_name": "Banana", "category": "fruit", "calories": 89, "protein": 1.1, "serving": "100 g"},
    ]

    initial_meal_plan = {
        "breakfast": {
            "foods": ["Poha", "Curd"],
            "target_calories": 250,
            "actual_calories": 190,
            "target_protein": 15.0,
            "actual_protein": 6.5,
            "food_details": [],
        },
        "lunch": {
            "foods": ["White Rice"],
            "target_calories": 120,
            "actual_calories": 130,
            "target_protein": 2.7,
            "actual_protein": 2.7,
            "food_details": [],
        },
        "snack": {
            "foods": ["Apple", "Banana"],
            "target_calories": 100,
            "actual_calories": 141,
            "target_protein": 8.0,
            "actual_protein": 1.4,
            "food_details": [],
        },
        "dinner": {
            "foods": ["Curd"],
            "target_calories": 60,
            "actual_calories": 60,
            "target_protein": 4.0,
            "actual_protein": 4.0,
            "food_details": [],
        },
    }

    try:
        optimizer = MealOptimizer(mock_filtered_foods, verbose=False)
        optimized = optimizer.optimize_meal_plan(initial_meal_plan)

        breakfast_foods = optimized["breakfast"]["foods"]
        snack_foods = optimized["snack"]["foods"]

        assert len(breakfast_foods) >= 2
        assert "Soy Chunks" not in snack_foods
        assert len(snack_foods) <= 2
        assert "Peanuts" not in snack_foods

        print(f"Optimized Breakfast Foods: {breakfast_foods}")
        print(f"Optimized Snack Foods: {snack_foods}")
        print("\nResult: PASS")
        return True
    except Exception as exc:
        print("\nResult: FAIL")
        print(f"Diagnostics: {exc}")
        return False


if __name__ == "__main__":
    success = test_meal_optimization()
    sys.exit(0 if success else 1)
