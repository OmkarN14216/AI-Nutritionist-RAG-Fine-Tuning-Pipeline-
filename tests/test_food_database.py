import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.food_loader import FoodDatabase


def test_food_database():
    print("\n==================================================")
    print("Testing Expanded Food Database")
    print("==================================================")

    required_fields = {
        "food_name", "category", "diet_type", "calories",
        "protein", "carbs", "fat", "fiber", "serving",
    }

    try:
        foods = FoodDatabase().get_all_foods()
        assert len(foods) >= 100

        names = [food["food_name"] for food in foods]
        assert len(names) == len(set(names))

        categories = {food["category"] for food in foods}
        for category in ["protein", "pulse", "vegetable", "regional", "breakfast"]:
            assert category in categories

        for food in foods:
            assert required_fields.issubset(food.keys())
            assert str(food["food_name"]).strip()
            assert str(food["serving"]).strip()
            for macro in ["calories", "protein", "carbs", "fat", "fiber"]:
                assert float(food[macro]) >= 0

        print(f"Food count: {len(foods)}")
        print("\nResult: PASS")
        return True
    except Exception as exc:
        print("\nResult: FAIL")
        print(f"Diagnostics: {exc}")
        return False


if __name__ == "__main__":
    success = test_food_database()
    sys.exit(0 if success else 1)
