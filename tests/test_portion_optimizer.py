import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.portion_optimizer import PortionOptimizer
from core.daily_rebalance import DailyRebalanceEngine


def test_portion_optimization():
    print("\n==================================================")
    print("Testing Layer 8: Portion Optimizer")
    print("==================================================")

    mock_foods = [
        {"food_name": "Poha", "category": "breakfast", "calories": 130, "protein": 2.5, "serving": "100 g cooked"},
        {"food_name": "Curd", "category": "dairy", "calories": 60, "protein": 4.0, "serving": "100 g"},
        {"food_name": "Egg White", "category": "protein", "calories": 17, "protein": 4.0, "serving": "1 egg white"},
    ]

    meal_plan = {
        "breakfast": {
            "foods": ["Poha", "Curd", "Egg White"],
            "target_calories": 450,
            "actual_calories": 207,
            "target_protein": 22.0,
            "actual_protein": 10.5,
            "foods_with_portions": [],
        },
        "lunch": {"foods": [], "target_calories": 0, "actual_calories": 0, "target_protein": 0.0, "actual_protein": 0.0},
        "snack": {"foods": [], "target_calories": 0, "actual_calories": 0, "target_protein": 0.0, "actual_protein": 0.0},
        "dinner": {"foods": [], "target_calories": 0, "actual_calories": 0, "target_protein": 0.0, "actual_protein": 0.0},
    }

    try:
        optimizer = PortionOptimizer(mock_foods, verbose=False)
        optimized = optimizer.optimize_portions(meal_plan)
        breakfast = optimized["breakfast"]

        assert set(breakfast["foods"]) == {"Poha", "Curd", "Egg White"}
        assert breakfast["actual_calories"] > 207
        assert breakfast["actual_protein"] > 10.5
        assert abs(breakfast["actual_protein"] - 22.0) <= 4.0

        rebalancer = DailyRebalanceEngine(mock_foods, PortionOptimizer.CONSTRAINTS)
        rebalanced = rebalancer.rebalance(
            optimized,
            target_calories=450,
            target_protein=22.0,
        )
        reb_breakfast = rebalanced["breakfast"]
        assert set(reb_breakfast["foods"]) == {"Poha", "Curd", "Egg White"}

        print(f"Target Calories: {breakfast['target_calories']} | Target Protein: {breakfast['target_protein']}g")
        print(f"Actual Calories: {breakfast['actual_calories']} | Actual Protein: {breakfast['actual_protein']}g")
        print("\nResult: PASS")
        return True
    except Exception as exc:
        print("\nResult: FAIL")
        print(f"Diagnostics: {exc}")
        return False


if __name__ == "__main__":
    success = test_portion_optimization()
    sys.exit(0 if success else 1)
