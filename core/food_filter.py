class FoodFilter:

    @staticmethod
    def filter_foods(foods, forbidden_ingredients):
        forbidden = {
            item.lower().strip()
            for item in forbidden_ingredients
            if item
        }

        filtered = []
        for food in foods:
            food_name = food["food_name"].lower().strip()
            diet_type = str(food.get("diet_type", "")).lower().strip()
            is_forbidden = any(
                forbidden_item == food_name
                or forbidden_item in food_name
                or food_name in forbidden_item
                for forbidden_item in forbidden
            )
            if diet_type == "eggitarian" and {"egg", "eggs", "egg white", "egg whites"} & forbidden:
                is_forbidden = True
            if diet_type == "nonveg" and {
                "chicken", "mutton", "fish", "seafood", "prawn", "prawns", "beef", "pork"
            } & forbidden:
                is_forbidden = True
            if not is_forbidden:
                filtered.append(food)

        return filtered
