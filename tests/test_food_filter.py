import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.food_loader import FoodDatabase
from core.food_filter import FoodFilter


def test_food_filter():
    print("\n==================================================")
    print("Testing Layer 4: Food Filter")
    print("==================================================")

    try:
        food_db = FoodDatabase()
        foods = food_db.get_all_foods()
        assert len(foods) > 0, "Food database is empty"

        filtered = FoodFilter.filter_foods(foods, ["Egg", "Milk"])
        filtered_names = {food["food_name"].lower() for food in filtered}
        assert "egg" not in filtered_names
        assert "milk" not in filtered_names
        assert all("egg" not in name for name in filtered_names)
        assert all("milk" not in name for name in filtered_names)
        assert len(filtered) < len(foods)

        case_filtered = FoodFilter.filter_foods(foods, ["curd"])
        case_names = {food["food_name"].lower() for food in case_filtered}
        assert "curd" not in case_names

        empty_filter = FoodFilter.filter_foods(foods, [])
        assert len(empty_filter) == len(foods)

        print(f"Total foods: {len(foods)}")
        print(f"Filtered foods (Egg/Milk removed): {len(filtered)}")
        print("\nResult: PASS")
        return True
    except Exception as exc:
        print("\nResult: FAIL")
        print(f"Diagnostics: {exc}")
        return False


if __name__ == "__main__":
    success = test_food_filter()
    sys.exit(0 if success else 1)
