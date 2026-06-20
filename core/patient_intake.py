from typing import Any, Dict, List, Optional


REQUIRED_FIELDS = [
    "age",
    "gender",
    "weight_kg",
    "height_cm",
    "activity_level",
    "goal",
    "dietary_preference",
]


def validate_patient_intake(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Layer 1 validation.
    Returns normalized payload and validation metadata.
    """
    missing = [field for field in REQUIRED_FIELDS if field not in payload]
    if missing:
        raise ValueError(f"Missing required intake fields: {', '.join(missing)}")

    normalized = dict(payload)
    normalized["gender"] = str(payload["gender"]).lower().strip()
    normalized["goal"] = str(payload["goal"]).lower().strip()
    normalized["activity_level"] = str(payload["activity_level"]).lower().strip()
    normalized["dietary_preference"] = str(payload["dietary_preference"]).lower().strip()
    normalized["medical_conditions"] = payload.get("medical_conditions", []) or []
    normalized["allergies"] = payload.get("allergies", []) or []

    if normalized["gender"] == "female" and not payload.get("hip_cm"):
        raise ValueError(
            "Females require hip_cm measurements for the U.S. Navy Body Fat model."
        )

    return normalized


def build_default_payload(**overrides: Any) -> Dict[str, Any]:
    base = {
        "age": 30,
        "gender": "male",
        "weight_kg": 75.0,
        "height_cm": 175.0,
        "waist_cm": 85.0,
        "neck_cm": 38.0,
        "hip_cm": None,
        "activity_level": "sedentary",
        "goal": "weight_loss",
        "target_weight_kg": 68.0,
        "target_weeks": 12,
        "dietary_preference": "veg",
        "medical_conditions": [],
        "allergies": [],
        "climate_hot": True,
    }
    base.update(overrides)
    return validate_patient_intake(base)
