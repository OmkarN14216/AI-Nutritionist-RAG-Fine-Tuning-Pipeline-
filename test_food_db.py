from core.food_loader import FoodDatabase
from core.meal_planner1 import MealPlanner

db = FoodDatabase()

foods = db.get_all_foods()

plan = MealPlanner.generate_meal_plan(
    foods
)

print(plan)