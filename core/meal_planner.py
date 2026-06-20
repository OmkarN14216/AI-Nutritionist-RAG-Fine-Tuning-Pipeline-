import json
import os
from collections import Counter
from itertools import combinations


class MealPlanner:

    CONDITION_SCORING_PATH = "config/condition_scoring.json"
    MAX_REPETITIONS_PER_DAY = 2
    MAX_DAILY_PROTEIN_MULTIPLIER = 1.08
    MIN_DAILY_PROTEIN_MULTIPLIER = 0.92
    RAG_SIGNAL_WEIGHT = 1.0
    SNACK_PROTEIN_FRACTION = 0.10
    SNACK_PROTEIN_ABSOLUTE_CAP = 12.0
    MAX_CANDIDATES_BY_MEAL = {
        "breakfast": 18,
        "lunch": 28,
        "snack": 16,
        "dinner": 28,
    }
    CANDIDATE_CATEGORY_LIMITS = {
        "breakfast": {
            "breakfast": 8,
            "dairy": 4,
            "protein": 6,
            "grain": 4,
        },
        "lunch": {
            "pulse": 7,
            "grain": 5,
            "vegetable": 6,
            "regional": 6,
            "protein": 5,
        },
        "snack": {
            "fruit": 6,
            "snack": 5,
            "dairy": 5,
        },
        "dinner": {
            "pulse": 7,
            "grain": 5,
            "vegetable": 6,
            "regional": 6,
            "protein": 5,
        },
    }
    MAX_ITEMS_BY_MEAL = {
        "breakfast": 4,
        "lunch": 4,
        "snack": 2,
        "dinner": 4,
    }

    PROTEIN_PRIORITY = {
        "Soy Chunks": 0,
        "Egg White": 1,
        "Paneer": 2,
        "Tofu": 3,
        "Egg": 4,
        "Moong Dal": 5,
        "Masoor Dal": 6,
        "Chana Dal": 7,
        "Rajma": 8,
        "Chole": 9,
        "Curd": 10,
        "Milk": 11,
        "Roti": 12,
        "Brown Rice": 13,
        "White Rice": 14,
        "Oats": 15,
        "Poha": 16,
        "Upma": 17,
        "Idli": 18,
        "Dosa": 19,
        "Apple": 20,
        "Banana": 21,
        "Roasted Chana": 22,
        "Peanuts": 23
    }

    MEAL_RULES = {
        "breakfast": {
            "preferred_categories": {"breakfast", "dairy", "protein", "grain"},
            "carb_categories": {"breakfast", "grain"},
            "protein_categories": {"protein", "dairy"},
            "priority_categories": [
                ("breakfast", ["Poha", "Upma", "Idli", "Dosa", "Oats"]),
                ("dairy", ["Curd", "Milk"]),
                ("protein", ["Egg White", "Egg", "Paneer", "Tofu", "Soy Chunks"])
            ]
        },
        "lunch": {
            "preferred_categories": {"pulse", "grain", "protein", "vegetable", "regional"},
            "carb_categories": {"grain", "pulse"},
            "protein_categories": {"protein", "pulse", "regional"},
            "priority_categories": [
                ("pulse", ["Moong Dal", "Masoor Dal", "Chana Dal", "Rajma", "Chole"]),
                ("grain", ["Brown Rice", "Roti", "White Rice", "Oats"]),
                ("vegetable", ["Bhindi Bhaji", "Mixed Vegetable Sabzi", "Cabbage Sabzi", "Dudhi Bhaji"]),
                ("regional", ["Vegetable Khichdi", "Sambar", "Maharashtrian Pithla", "Zunka"]),
                ("protein", ["Paneer", "Tofu", "Soy Chunks", "Egg", "Egg White"])
            ]
        },
        "snack": {
            "preferred_categories": {"fruit", "snack", "dairy"},
            "carb_categories": {"fruit", "snack"},
            "protein_categories": {"snack", "dairy"},
            "priority_categories": [
                ("fruit", ["Apple", "Banana"]),
                ("dairy", ["Curd", "Milk"]),
                ("snack", ["Roasted Chana", "Peanuts"])
            ]
        },
        "dinner": {
            "preferred_categories": {"pulse", "grain", "protein", "vegetable", "regional"},
            "carb_categories": {"grain", "pulse"},
            "protein_categories": {"protein", "pulse", "regional"},
            "priority_categories": [
                ("pulse", ["Moong Dal", "Masoor Dal", "Chana Dal", "Rajma", "Chole"]),
                ("grain", ["Brown Rice", "Roti", "White Rice", "Oats"]),
                ("vegetable", ["Palak Sabzi", "Beans Sabzi", "Karela Sabzi", "Pumpkin Sabzi"]),
                ("regional", ["Moong Khichdi", "Rasam", "Avial", "Vegetable Stew"]),
                ("protein", ["Egg White", "Egg", "Paneer", "Tofu", "Soy Chunks"])
            ]
        }
    }

    @staticmethod
    def allocate_calories(total_calories):

        return {
            "breakfast": round(total_calories * 0.25),
            "lunch": round(total_calories * 0.35),
            "snack": round(total_calories * 0.10),
            "dinner": round(total_calories * 0.30)
        }

    @staticmethod
    def _normalize(value):

        return (value or "").strip().lower()

    @staticmethod
    def _food_name(food):

        return (food.get("food_name") or "").strip()

    @staticmethod
    def _food_calories(food):

        calories = food.get("calories", 0)

        try:

            return float(calories)

        except (TypeError, ValueError):

            return 0.0

    @staticmethod
    def _food_protein(food):

        protein = food.get("protein", 0)

        try:

            return float(protein)

        except (TypeError, ValueError):

            return 0.0

    @staticmethod
    def _food_fiber(food):

        fiber = food.get("fiber", 0)

        try:

            return float(fiber)

        except (TypeError, ValueError):

            return 0.0

    @staticmethod
    def _food_priority_score(food):

        return MealPlanner.PROTEIN_PRIORITY.get(MealPlanner._food_name(food), 100)

    @staticmethod
    def _load_condition_scoring(config_path=None):

        scoring_path = config_path or MealPlanner.CONDITION_SCORING_PATH

        if not os.path.exists(scoring_path):

            return {}

        try:

            with open(scoring_path, "r", encoding="utf-8") as file_handle:
                raw_config = json.load(file_handle)

        except (OSError, json.JSONDecodeError):

            return {}

        normalized_config = {}

        for condition_name, condition_config in raw_config.items():

            normalized_config[MealPlanner._normalize(condition_name)] = {
                "bonus_foods": {
                    MealPlanner._normalize(food_name)
                    for food_name in condition_config.get("bonus_foods", [])
                },
                "penalty_foods": {
                    MealPlanner._normalize(food_name)
                    for food_name in condition_config.get("penalty_foods", [])
                },
                "bonus_points": float(condition_config.get("bonus_points", 10)),
                "penalty_points": float(condition_config.get("penalty_points", 5))
            }

        return normalized_config

    @staticmethod
    def _normalize_conditions(active_conditions):

        normalized_conditions = []

        for condition in active_conditions or []:

            normalized_condition = MealPlanner._normalize(condition)

            if normalized_condition and normalized_condition not in normalized_conditions:

                normalized_conditions.append(normalized_condition)

        return normalized_conditions

    @staticmethod
    def _food_condition_bonus(food, active_conditions, condition_scoring):

        food_name = MealPlanner._normalize(MealPlanner._food_name(food))
        bonus_total = 0.0

        for condition_name in active_conditions:

            condition_config = condition_scoring.get(condition_name)

            if not condition_config:

                continue

            if food_name in condition_config["bonus_foods"]:

                bonus_total += condition_config["bonus_points"]

            if food_name in condition_config["penalty_foods"]:

                bonus_total -= condition_config["penalty_points"]

        return bonus_total

    @staticmethod
    def _food_rag_bonus(food, rag_food_bonuses):
        food_name = MealPlanner._food_name(food)
        food_category = food.get("category", "")
        
        # If it's a RAGSignals object:
        if hasattr(rag_food_bonuses, "get_bonus_for_food"):
            return float(rag_food_bonuses.get_bonus_for_food(food_name, food_category))
        
        # Fallback to dictionary
        if isinstance(rag_food_bonuses, dict):
            return float(rag_food_bonuses.get(food_name, 0.0))
            
        return 0.0

    @staticmethod
    def _food_final_score(food, active_conditions, condition_scoring, rag_food_bonuses):

        protein_score = MealPlanner._food_protein(food)
        fiber_score = MealPlanner._food_fiber(food)
        condition_bonus = MealPlanner._food_condition_bonus(
            food,
            active_conditions,
            condition_scoring
        )
        rag_bonus = MealPlanner._food_rag_bonus(food, rag_food_bonuses)
        final_score = protein_score - fiber_score + condition_bonus + rag_bonus

        return {
            "protein_score": round(protein_score, 1),
            "fiber_score": round(fiber_score, 1),
            "condition_bonus": round(condition_bonus, 1),
            "rag_bonus": round(rag_bonus, 1),
            "final_score": round(final_score, 1)
        }

    @staticmethod
    def _build_candidate_pool(filtered_foods, category_rules):

        candidate_pool = []
        seen_food_names = set()

        for category_name, preferred_names in category_rules:

            category_foods = [
                food
                for food in filtered_foods
                if MealPlanner._normalize(food.get("category")) == category_name
            ]

            ordered_foods = []
            seen_in_category = set()

            for preferred_name in preferred_names:

                for food in category_foods:

                    if MealPlanner._food_name(food) == preferred_name:

                        food_name = MealPlanner._food_name(food)

                        if food_name not in seen_in_category:

                            ordered_foods.append(food)
                            seen_in_category.add(food_name)

            for food in category_foods:

                food_name = MealPlanner._food_name(food)

                if food_name not in seen_in_category:

                    ordered_foods.append(food)
                    seen_in_category.add(food_name)

            for food in ordered_foods:

                food_name = MealPlanner._food_name(food)

                if food_name and food_name not in seen_food_names:

                    candidate_pool.append(food)
                    seen_food_names.add(food_name)

        return candidate_pool

    @staticmethod
    def _combo_repetition_penalty(combo, food_usage_counts):

        penalty = 0.0

        for food in combo:

            food_name = MealPlanner._food_name(food)
            previous_count = food_usage_counts.get(food_name, 0)

            if previous_count == 0:

                continue

            if previous_count < MealPlanner.MAX_REPETITIONS_PER_DAY:

                penalty += previous_count * 8.0

            else:

                penalty += 200.0

        return penalty

    @staticmethod
    def _food_weekly_key(food_name, weekly_repetition_limits):

        normalized_food_name = MealPlanner._normalize(food_name)

        for weekly_key in weekly_repetition_limits or {}:

            normalized_key = MealPlanner._normalize(weekly_key)

            if normalized_key and normalized_key in normalized_food_name:

                return weekly_key

        return food_name

    @staticmethod
    def _combo_weekly_repetition_penalty(combo, weekly_usage_counts, weekly_repetition_limits):

        if not weekly_usage_counts or not weekly_repetition_limits:

            return 0.0

        penalty = 0.0

        combo_counts = Counter()

        for food in combo:

            food_name = MealPlanner._food_name(food)
            weekly_key = MealPlanner._food_weekly_key(food_name, weekly_repetition_limits)
            combo_counts[weekly_key] += 1
            limit = weekly_repetition_limits.get(weekly_key)

            if limit is None:

                limit = weekly_repetition_limits.get(MealPlanner._normalize(weekly_key))

            if limit is None:

                continue

            previous_count = weekly_usage_counts.get(weekly_key, 0)
            projected_count = previous_count + combo_counts[weekly_key]

            if projected_count > limit:

                penalty += 500.0

            elif projected_count == limit:

                penalty += 50.0

            elif previous_count > 0:

                penalty += previous_count * 6.0

        return penalty

    @staticmethod
    def _candidate_sort_score(food, active_conditions, condition_scoring, rag_food_bonuses):

        final_score = MealPlanner._food_final_score(
            food,
            active_conditions,
            condition_scoring,
            rag_food_bonuses
        )["final_score"]

        return (
            -final_score,
            MealPlanner._food_priority_score(food),
            MealPlanner._food_name(food)
        )

    @staticmethod
    def _limit_candidate_pool(
        candidate_pool,
        meal_name,
        active_conditions,
        condition_scoring,
        rag_food_bonuses,
        rotation_offset
    ):

        category_limits = MealPlanner.CANDIDATE_CATEGORY_LIMITS.get(meal_name, {})
        selected_candidates = []
        seen_foods = set()

        for category_name, limit in category_limits.items():

            category_foods = [
                food
                for food in candidate_pool
                if MealPlanner._normalize(food.get("category")) == category_name
            ]
            category_foods = sorted(
                category_foods,
                key=lambda food: MealPlanner._candidate_sort_score(
                    food,
                    active_conditions,
                    condition_scoring,
                    rag_food_bonuses
                )
            )

            if category_foods:
                rotation = rotation_offset % len(category_foods)
                category_foods = category_foods[rotation:] + category_foods[:rotation]

            for food in category_foods[:limit]:

                food_name = MealPlanner._food_name(food)

                if food_name not in seen_foods:

                    selected_candidates.append(food)
                    seen_foods.add(food_name)

        if not selected_candidates:

            selected_candidates = sorted(
                candidate_pool,
                key=lambda food: MealPlanner._candidate_sort_score(
                    food,
                    active_conditions,
                    condition_scoring,
                    rag_food_bonuses
                )
            )

        candidate_limit = MealPlanner.MAX_CANDIDATES_BY_MEAL.get(
            meal_name,
            len(selected_candidates)
        )

        return selected_candidates[:candidate_limit]

    @staticmethod
    def _combo_meal_quality(combo, meal_name):

        meal_rules = MealPlanner.MEAL_RULES[meal_name]
        categories_present = {
            MealPlanner._normalize(food.get("category"))
            for food in combo
        }

        preferred_match_score = len(
            categories_present & meal_rules["preferred_categories"]
        ) * 5.0
        carb_bonus = 8.0 if categories_present & meal_rules["carb_categories"] else 0.0
        protein_bonus = 8.0 if categories_present & meal_rules["protein_categories"] else 0.0
        diversity_bonus = len(categories_present) * 2.0
        vegetable_bonus = 10.0 if meal_name in {"lunch", "dinner"} and "vegetable" in categories_present else 0.0
        regional_bonus = 8.0 if meal_name in {"lunch", "dinner"} and "regional" in categories_present else 0.0
        fruit_bonus = 12.0 if meal_name == "snack" and "fruit" in categories_present else 0.0

        return (
            preferred_match_score
            + carb_bonus
            + protein_bonus
            + diversity_bonus
            + vegetable_bonus
            + regional_bonus
            + fruit_bonus
        )

    @staticmethod
    def _select_best_combo(
        candidate_pool,
        target_calories,
        target_protein,
        meal_name,
        active_conditions,
        condition_scoring,
        rag_food_bonuses,
        food_usage_counts,
        daily_protein_total,
        daily_protein_upper,
        weekly_usage_counts=None,
        weekly_repetition_limits=None
    ):

        if not candidate_pool or target_calories <= 0:

            return []

        max_items = min(MealPlanner.MAX_ITEMS_BY_MEAL.get(meal_name, 4), len(candidate_pool))
        lower_bound = target_calories * 0.85
        upper_bound = target_calories * 1.15

        best_combo = []
        best_score = None

        for combo_size in range(1, max_items + 1):

            for combo in combinations(candidate_pool, combo_size):

                total_calories = sum(
                    MealPlanner._food_calories(food)
                    for food in combo
                )
                total_protein = sum(
                    MealPlanner._food_protein(food)
                    for food in combo
                )
                total_condition_bonus = sum(
                    MealPlanner._food_condition_bonus(
                        food,
                        active_conditions,
                        condition_scoring
                    )
                    for food in combo
                )
                total_food_score = sum(
                    MealPlanner._food_final_score(
                        food,
                        active_conditions,
                        condition_scoring,
                        rag_food_bonuses
                    )["final_score"]
                    for food in combo
                )
                total_rag_bonus = sum(
                    MealPlanner._food_rag_bonus(food, rag_food_bonuses)
                    for food in combo
                )
                weighted_rag_bonus = total_rag_bonus * MealPlanner.RAG_SIGNAL_WEIGHT
                calorie_difference = abs(total_calories - target_calories)
                protein_difference = abs(total_protein - target_protein)
                protein_shortfall = max(0.0, target_protein - total_protein)
                protein_excess = max(0.0, total_protein - target_protein)
                protein_upper_violation = max(
                    0.0,
                    (daily_protein_total + total_protein) - daily_protein_upper
                )
                categories_present = {
                    MealPlanner._normalize(food.get("category"))
                    for food in combo
                }
                category_missing_penalty = 0
                if meal_name == "snack" and "fruit" not in categories_present:
                    category_missing_penalty += 1
                if meal_name in {"lunch", "dinner"}:
                    if "vegetable" not in categories_present:
                        category_missing_penalty += 1
                    if "regional" not in categories_present:
                        category_missing_penalty += 1
                repetition_penalty = MealPlanner._combo_repetition_penalty(
                    combo,
                    food_usage_counts
                )
                weekly_repetition_penalty = MealPlanner._combo_weekly_repetition_penalty(
                    combo,
                    weekly_usage_counts or {},
                    weekly_repetition_limits or {}
                )
                meal_quality_score = MealPlanner._combo_meal_quality(combo, meal_name)
                priority_score = sum(
                    MealPlanner._food_priority_score(food)
                    for food in combo
                )
                would_exceed_rep = any(
                    food_usage_counts.get(MealPlanner._food_name(food), 0)
                    >= MealPlanner.MAX_REPETITIONS_PER_DAY
                    for food in combo
                )

                if lower_bound <= total_calories <= upper_bound:

                    score = (
                        1 if would_exceed_rep else 0,
                        0,
                        category_missing_penalty,
                        0 if total_protein >= target_protein * MealPlanner.MIN_DAILY_PROTEIN_MULTIPLIER else 1,
                        protein_upper_violation,
                        protein_excess,
                        protein_shortfall,
                        repetition_penalty,
                        weekly_repetition_penalty,
                        -weighted_rag_bonus,
                        -meal_quality_score,
                        -total_food_score,
                        -total_condition_bonus,
                        calorie_difference,
                        protein_difference,
                        -total_protein,
                        priority_score,
                        combo_size
                    )

                else:

                    score = (
                        1 if would_exceed_rep else 0,
                        1,
                        calorie_difference,
                        category_missing_penalty,
                        0 if total_protein >= target_protein * MealPlanner.MIN_DAILY_PROTEIN_MULTIPLIER else 1,
                        protein_upper_violation,
                        protein_excess,
                        protein_shortfall,
                        repetition_penalty,
                        weekly_repetition_penalty,
                        -weighted_rag_bonus,
                        -meal_quality_score,
                        -total_food_score,
                        -total_condition_bonus,
                        protein_difference,
                        -total_protein,
                        priority_score,
                        combo_size,
                        max(0.0, total_calories - upper_bound)
                    )

                if best_score is None or score < best_score:

                    best_score = score
                    best_combo = list(combo)

        return best_combo

    @staticmethod
    def generate_meal_plan(
        filtered_foods,
        meal_allocation,
        target_protein,
        active_conditions=None,
        condition_scoring_path=None,
        rag_food_bonuses=None,
        enable_rag_scoring=True,
        weekly_usage_counts=None,
        weekly_repetition_limits=None,
        rotation_offset=0
    ):

        active_conditions = MealPlanner._normalize_conditions(active_conditions)
        condition_scoring = MealPlanner._load_condition_scoring(condition_scoring_path)
        if not enable_rag_scoring:
            rag_food_bonuses = None
        else:
            # If it's a dict, normalize it; if it's RAGSignals, keep it as is
            if isinstance(rag_food_bonuses, dict):
                rag_food_bonuses = {
                    MealPlanner._food_name({"food_name": k}): float(v)
                    for k, v in rag_food_bonuses.items()
                }

        meal_order = ["breakfast", "lunch", "snack", "dinner"]

        meal_plan = {
            meal_name: {
                "foods": [],
                "target_calories": round(meal_allocation.get(meal_name, 0)),
                "actual_calories": 0,
                "target_protein": 0.0,
                "actual_protein": 0.0,
                "food_details": []
            }
            for meal_name in meal_order
        }
        meal_plan["repetition_counts"] = {}

        total_target_calories = sum(meal_allocation.values()) or 1
        daily_protein_lower = target_protein * MealPlanner.MIN_DAILY_PROTEIN_MULTIPLIER
        daily_protein_upper = target_protein * MealPlanner.MAX_DAILY_PROTEIN_MULTIPLIER

        food_usage_counts = Counter()
        running_protein_total = 0.0
        running_calorie_total = 0.0

        for meal_index, meal_name in enumerate(meal_order):

            target_calories = meal_plan[meal_name]["target_calories"]
            remaining_meals = len(meal_order) - meal_index
            remaining_protein_allowance = max(0.0, daily_protein_upper - running_protein_total)
            remaining_protein_floor = max(0.0, daily_protein_lower - running_protein_total)
            proportional_meal_protein = target_protein * target_calories / total_target_calories

            if meal_name == "snack":
                meal_target_protein = min(
                    proportional_meal_protein,
                    target_protein * MealPlanner.SNACK_PROTEIN_FRACTION,
                    MealPlanner.SNACK_PROTEIN_ABSOLUTE_CAP,
                    remaining_protein_allowance,
                )
            else:
                meal_target_protein = min(
                    proportional_meal_protein,
                    remaining_protein_allowance / max(1, remaining_meals),
                )
                if meal_name != "snack":
                    meal_target_protein = max(
                        meal_target_protein,
                        remaining_protein_floor / max(1, remaining_meals),
                    )

            candidate_pool = MealPlanner._build_candidate_pool(
                filtered_foods=filtered_foods,
                category_rules=MealPlanner.MEAL_RULES[meal_name]["priority_categories"]
            )
            candidate_pool = MealPlanner._limit_candidate_pool(
                candidate_pool,
                meal_name,
                active_conditions,
                condition_scoring,
                rag_food_bonuses,
                rotation_offset
            )

            selected_foods = MealPlanner._select_best_combo(
                candidate_pool=candidate_pool,
                target_calories=target_calories,
                target_protein=meal_target_protein,
                meal_name=meal_name,
                active_conditions=active_conditions,
                condition_scoring=condition_scoring,
                rag_food_bonuses=rag_food_bonuses,
                food_usage_counts=food_usage_counts,
                daily_protein_total=running_protein_total,
                daily_protein_upper=daily_protein_upper,
                weekly_usage_counts=weekly_usage_counts,
                weekly_repetition_limits=weekly_repetition_limits
            )

            meal_plan[meal_name]["foods"] = [
                MealPlanner._food_name(food)
                for food in selected_foods
            ]
            meal_plan[meal_name]["food_details"] = [
                {
                    "food_name": MealPlanner._food_name(food),
                    **MealPlanner._food_final_score(
                        food,
                        active_conditions,
                        condition_scoring,
                        rag_food_bonuses
                    ),
                    "repetition_count": food_usage_counts[MealPlanner._food_name(food)]
                }
                for food in selected_foods
            ]
            meal_plan[meal_name]["actual_calories"] = round(
                sum(
                    MealPlanner._food_calories(food)
                    for food in selected_foods
                )
            )
            meal_plan[meal_name]["actual_protein"] = round(
                sum(
                    MealPlanner._food_protein(food)
                    for food in selected_foods
                ),
                1
            )
            meal_plan[meal_name]["target_protein"] = round(meal_target_protein, 1)

            running_calorie_total += meal_plan[meal_name]["actual_calories"]
            running_protein_total += meal_plan[meal_name]["actual_protein"]

            for food_name in meal_plan[meal_name]["foods"]:

                food_usage_counts[food_name] += 1

        meal_plan["repetition_counts"] = dict(food_usage_counts)

        return meal_plan
