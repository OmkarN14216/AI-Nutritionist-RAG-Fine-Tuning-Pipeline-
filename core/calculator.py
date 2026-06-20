import math
from typing import Dict, Any, Optional

class EliteNutritionEngine:
    """
    Advanced physiological computing suite adjusted for South Asian WHO/ICMR-NIN thresholds,
    U.S. Navy Body Fat models, Robinson Ideal Weight, Clinical Obesity adjustments,
    Fluid dynamics, and ICMR-NIN Scaled Macro Distributions for 100% Indian Cohorts.
    Includes Dynamic Deficit Pacing to prevent metabolic crash states.
    """
    
    @staticmethod
    def calculate_bmi_category(bmi: float, age_years: int, gender: str) -> str:
        """Determines clinical weight categories adjusted for South Asian Phenotype guidelines."""
        if age_years < 20:
            if gender.lower() == "male":
                if bmi < 14.5: return "Underweight (Pediatric)"
                elif 14.5 <= bmi < 21.0: return "Normal Weight (Pediatric)"
                elif 21.0 <= bmi < 23.5: return "Overweight (Pediatric Alert)"
                else: return "Obese (Pediatric)"
            else: 
                if bmi < 14.0: return "Underweight (Pediatric)"
                elif 14.0 <= bmi < 21.5: return "Normal Weight (Pediatric)"
                elif 21.5 <= bmi < 24.0: return "Overweight (Pediatric Alert)"
                else: return "Obese (Pediatric)"
        elif age_years > 65:
            if bmi < 22.0: return "Underweight (Geriatric Threshold)"
            elif 22.0 <= bmi <= 26.0: return "Normal Weight (Healthy Elderly Baseline)"
            elif 26.0 < bmi <= 28.0: return "Overweight (Geriatric)"
            else: return "Obese (Geriatric)"
        else:
            # Consensus Cut-offs for Asian Indians (WHO/ICMR)
            if bmi < 18.5: return "Underweight"
            elif 18.5 <= bmi < 23.0: return "Normal Weight"
            elif 23.0 <= bmi < 25.0: return "Overweight (Increased South Asian Metabolic Risk)"
            else: return "Obese (High Cardiovascular/Diabetic Risk Profile)"

    @staticmethod
    def evaluate_visceral_risk(waist_cm: float, gender: str) -> str:
        """Evaluates metabolic syndrome risk based on Indian waist circumference cut-offs."""
        if gender.lower() == "male":
            if waist_cm > 90.0:
                return "HIGH RISK (South Asian Visceral Adiposity Threshold Crossed)"
            return "Normal Baseline"
        else:
            if waist_cm > 80.0:
                return "HIGH RISK (South Asian Visceral Adiposity Threshold Crossed)"
            return "Normal Baseline"

    @staticmethod
    def calculate_robinson_ideal_weight(height_cm: float, gender: str) -> float:
        """Calculates Ideal Body Weight (IBW) using the Robinson Formula (1983)."""
        inches_over_5ft = (height_cm - 152.4) / 2.54
        if inches_over_5ft < 0:
            inches_over_5ft = 0 
            
        if gender.lower() == "male":
            return round(52.0 + (1.9 * inches_over_5ft), 2)
        else:
            return round(49.0 + (1.7 * inches_over_5ft), 2)

    @staticmethod
    def estimate_body_fat_navy(
        gender: str, height_cm: float, waist_cm: float, neck_cm: float, hip_cm: Optional[float] = None
    ) -> float:
        """Estimates Body Fat Percentage using the U.S. Navy Circumference Equation."""
        if gender.lower() == "female" and hip_cm is None:
            raise ValueError("Females require Hip Circumference measurements for the U.S. Navy Body Fat model.")

        if gender.lower() == "male":
            try:
                return round(86.010 * math.log10(waist_cm - neck_cm) - 70.041 * math.log10(height_cm) + 36.76, 1)
            except ValueError:
                return 26.0  # Safe South Asian average baseline override
        else:
            try:
                return round(163.205 * math.log10(waist_cm + hip_cm - neck_cm) - 97.684 * math.log10(height_cm) - 78.387, 1)
            except ValueError:
                return 34.0  # Safe South Asian average baseline override

    @staticmethod
    def calculate_time_bound_deficit(current_weight: float, target_weight: float, weeks: int, current_age: int) -> Dict[str, Any]:
        """Calculates daily deficit based on time horizons while guarding metabolic pacing limits."""
        total_weight_to_lose = current_weight - target_weight
        if total_weight_to_lose <= 0:
            return {"daily_deficit": 0.0, "weekly_loss_kg": 0.0, "velocity_percentage": 0.0, "status": "stable", "guidance": "Goal trajectory stable."}
            
        weight_loss_per_week = total_weight_to_lose / weeks
        pct_body_weight_per_week = (weight_loss_per_week / current_weight) * 100
        daily_deficit = (total_weight_to_lose * 7700 / weeks) / 7.0
        
        status = "safe"
        message = f"Timeline verified. Progressing at {round(weight_loss_per_week, 2)} kg/week ({round(pct_body_weight_per_week, 2)}% of body weight)."
        
        velocity_ceiling = 1.0 if current_age < 65 else 0.7
        if pct_body_weight_per_week > velocity_ceiling:
            status = "unsafe"
            recommended_weeks = math.ceil(total_weight_to_lose / (current_weight * (velocity_ceiling / 100)))
            message = f"CRITICAL SPEED WARNING: Dropping {round(pct_body_weight_per_week, 2)}% body weight weekly risks intense lean muscle wasting. Adjust timeline to at least {recommended_weeks} weeks for safer metabolic preservation."
            
        return {"daily_deficit": round(daily_deficit, 1), "weekly_loss_kg": round(weight_loss_per_week, 2), "velocity_percentage": round(pct_body_weight_per_week, 2), "status": status, "guidance": message}

    @staticmethod
    def calculate_fluid_requirements(weight_kg: float, activity_level: str, climate_hot: bool = True) -> Dict[str, Any]:
        """
        Computes fluid requirement baselines adhering to ICMR-NIN seasonal criteria.
        Includes mandatory thermal adjustments for baseline ambient climates across India.
        """
        base_fluid_ml = weight_kg * 35.0
        
        activity_fluid_additions = {
            "sedentary": 0.0, "lightly_active": 350.0, "moderately_active": 700.0,
            "active_intense": 1000.0, "very_active": 1500.0, "extra_active": 2000.0
        }
        activity_bonus = activity_fluid_additions.get(activity_level.lower(), 0.0)
        climate_bonus = 600.0 if climate_hot else 0.0  # Increased for tropical baseline humidity
        
        total_ml = base_fluid_ml + activity_bonus + climate_bonus
        return {
            "baseline_water_liters": round(base_fluid_ml / 1000.0, 2),
            "total_target_water_liters": round(total_ml / 1000.0, 2),
            "guidance_notes": f"Target fluid baseline: {round(total_ml / 1000.0, 1)}L per day. Crucial to mitigate heat stress under tropical ambient shifts."
        }

    @classmethod
    def generate_comprehensive_profile(cls, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Synthesizes Indian physiological modules into a high-fidelity diagnostic packet."""
        raw_weight = user_data["weight_kg"]
        height = user_data["height_cm"]
        age = user_data["age"]
        gender = user_data["gender"]
        goal = user_data["goal"]
        activity = user_data["activity_level"]
        diet_pref = user_data.get("dietary_preference", "veg")
        med_conditions = user_data.get("medical_conditions", [])
        
        # 1. Anthropometrics & South Asian Cutoff Screening
        bmi = round(raw_weight / ((height / 100.0) ** 2), 2)
        ibw = cls.calculate_robinson_ideal_weight(height, gender)
        
        # Clinical adjustment: Indian obesity ceiling cuts off at BMI >= 25
        is_obese_profile = bmi >= 25.0
        calc_weight = ibw + 0.4 * (raw_weight - ibw) if is_obese_profile else raw_weight
        
        # Visceral fat screening
        visceral_status = "Not Provided"
        if "waist_cm" in user_data:
            visceral_status = cls.evaluate_visceral_risk(user_data["waist_cm"], gender)
        
        # 2. Composition Architecture
        body_fat = user_data.get("body_fat_pct")
        if body_fat is None and "waist_cm" in user_data and "neck_cm" in user_data:
            body_fat = cls.estimate_body_fat_navy(gender, height, user_data["waist_cm"], user_data["neck_cm"], user_data.get("hip_cm"))
            
        fat_mass_kg = round(raw_weight * (body_fat / 100.0), 2) if body_fat else None
        lbm_kg = round(raw_weight - fat_mass_kg, 2) if fat_mass_kg else round(raw_weight * 0.72, 2) # Adjusted South Asian lean muscle floor
        
        # 3. Energy Expenditure (BMR Multipliers scaled down slightly for Sedentary South Asian thin-fat risk mitigation)
        if body_fat:
            bmr_val = round(370 + (21.6 * (raw_weight * (1 - (body_fat / 100.0)))), 2)
        else:
            if gender.lower() == "male":
                bmr_val = round((10 * calc_weight) + (6.25 * height) - (5 * age) + 5, 2)
            else:
                bmr_val = round((10 * calc_weight) + (6.25 * height) - (5 * age) - 161, 2)
                
        # Local physical baseline activity scaling modifier (-5% to Western norms for standard sedentary tiers)
        base_multiplier = cls.get_activity_multiplier(activity)
        if activity.lower() == "sedentary":
            base_multiplier = 1.15  # Scaled down to prevent energy target overshoot
            
        tdee = round(bmr_val * base_multiplier, 2)
        
        # 4. Target Calorie Framing with Dynamic Deficit Safety Clamping
        target_weight = user_data.get("target_weight_kg", ibw if goal == "weight_loss" else raw_weight)
        target_calories = tdee
        time_metrics = {"status": "maintenance"}
        
        if goal == "weight_loss":
            if "target_weeks" in user_data:
                time_metrics = cls.calculate_time_bound_deficit(raw_weight, target_weight, user_data["target_weeks"], age)
                
                # Dynamic Check: Prevent the deficit from exceeding a safe 25% boundary of total energy availability
                max_safe_deficit = tdee * 0.25
                actual_deficit = time_metrics["daily_deficit"]
                
                if actual_deficit > max_safe_deficit:
                    actual_deficit = max_safe_deficit
                    time_metrics["status"] = "deficit_capped"
                    time_metrics["guidance"] = (
                        f"CRITICAL OVERRIDE: Requested timeline required a harsh -{round(time_metrics['daily_deficit'])} kcal deficit. "
                        f"Engine auto-clamped the target deficit to a safe 25% ceiling (-{round(max_safe_deficit)} kcal) "
                        f"to preserve lean muscle tissue and shield systemic thyroid performance."
                    )
                target_calories = tdee - actual_deficit
            else:
                target_calories = tdee - 450  # Conservative safe step down for Indian cohorts
                time_metrics = {"status": "static_deficit", "guidance": "Standard local -450 kcal fat-loss protocol implemented."}
        elif goal == "weight_gain":
            target_calories = tdee + 300
            
        # Protect absolute physiological baseline using individual BMR instead of an arbitrary global integer
        minimum_safe_intake = max(
            bmr_val,
            1500 if gender.lower() == "male" else 1200
        )

        if target_calories < minimum_safe_intake:
            target_calories = minimum_safe_intake

            time_metrics["guidance"] = (
                f"Safety Override Activated: "
                f"Calorie target raised to "
                f"{round(target_calories)} kcal/day."
            )

        # 5. ICMR-NIN 2024 Macro Split Allocation Layer
        # ==========================================================
# 5. ICMR-NIN 2024 Macro Allocation Layer
# ==========================================================

        is_diabetic = "diabetes" in [c.lower() for c in med_conditions]

        # ----------------------------------------------------------
        # Protein Allocation
        # ----------------------------------------------------------

        if goal == "weight_loss":

            if activity.lower() == "sedentary":
                protein_factor = 1.1

            elif activity.lower() in [
                "lightly_active",
                "moderately_active"
            ]:
                protein_factor = 1.3

            else:
                protein_factor = 1.5

        elif goal == "weight_gain":

            protein_factor = 1.6

        else:

            protein_factor = 1.0

        protein_g = round(
            raw_weight * protein_factor,
            1
        )

        protein_kcal = protein_g * 4

        # ----------------------------------------------------------
        # Fat Allocation
        # ----------------------------------------------------------

        if is_diabetic:
            fat_pct = 0.25
        else:
            fat_pct = 0.23

        fat_kcal = target_calories * fat_pct

        fat_g = round(
            fat_kcal / 9,
            1
        )

        # ----------------------------------------------------------
        # Carbohydrate Allocation
        # ----------------------------------------------------------

        remaining_kcal = (
            target_calories
            - protein_kcal
            - fat_kcal
        )

        if remaining_kcal < 0:
            remaining_kcal = 0

        carb_g = round(
            remaining_kcal / 4,
            1
        )

        # ----------------------------------------------------------
        # ICMR Carb Ceiling
        # ----------------------------------------------------------

        carb_pct = (
            (carb_g * 4)
            / target_calories
        )

        if carb_pct > 0.55:

            carb_g = round(
                (target_calories * 0.55) / 4,
                1
            )

            fat_g = round(
                (
                    target_calories
                    - (protein_g * 4)
                    - (carb_g * 4)
                ) / 9,
                1
            )

        # ----------------------------------------------------------
        # Final Validation
        # ----------------------------------------------------------

        actual_kcal = round(
            protein_g * 4
            + fat_g * 9
            + carb_g * 4
        )

        print("\n========== MACRO VALIDATION ==========")
        print(f"Target Calories : {round(target_calories)}")
        print(f"Actual Calories : {actual_kcal}")
        print(f"Protein         : {protein_g} g")
        print(f"Fat             : {fat_g} g")
        print(f"Carbohydrates   : {carb_g} g")
        print("======================================\n")

        # 6. Hydration Telemetry
        hydration = cls.calculate_fluid_requirements(raw_weight, activity, climate_hot=user_data.get("climate_hot", True))
        
        return {
            "anthropometrics": {
                "bmi": bmi,
                "bmi_category": cls.calculate_bmi_category(bmi, age, gender),
                "visceral_fat_risk": visceral_status,
                "estimated_body_fat_pct": body_fat,
                "calculated_lean_mass_kg": lbm_kg,
                "calculated_fat_mass_kg": fat_mass_kg,
                "robinson_ideal_weight_kg": ibw,
                "is_obesity_adjusted_formula": is_obese_profile
            },
            "thermodynamics": {
                "calculated_bmr_kcal": bmr_val,
                "tdee_maintenance_kcal": tdee,
                "target_dietary_calories_kcal": round(target_calories, 2)
            },
            "target_macronutrients_absolute": {
                "protein_grams": protein_g,
                "fats_grams": fat_g,
                "carbohydrates_grams": carb_g,
                "carb_energy_percentage": round(((carb_g * 4) / target_calories) * 100, 1)
            },
            "hydration_telemetry": hydration,
            "goal_validation": {
                "time_horizon_analysis": time_metrics
            }
        }

    @staticmethod
    def get_activity_multiplier(activity_tier: str) -> float:
        tiers = {
            "sedentary": 1.2, "lightly_active": 1.375, "moderately_active": 1.465,
            "active_intense": 1.55, "very_active": 1.725, "extra_active": 1.9
        }
        return tiers.get(activity_tier.lower(), 1.2)