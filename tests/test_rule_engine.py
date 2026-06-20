import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.rule_engine import GuardrailRuleEngine


def test_rule_engine():
    print("\n==================================================")
    print("Testing Layer 3: Rule Engine")
    print("==================================================")

    try:
        engine = GuardrailRuleEngine(config_path="config/rules.json")

        gerd_result = engine.compile_user_constraints(
            medical_flags=["gerd"],
            allergy_flags=[],
            dietary_pref="eggitarian",
        )
        assert "forbidden_ingredients" in gerd_result
        assert "soft_restrictions" in gerd_result
        assert "clinical_guardrail_directives" in gerd_result
        assert any("tomato" in item for item in gerd_result["forbidden_ingredients"])
        assert len(gerd_result["clinical_guardrail_directives"]) >= 2

        vegan_result = engine.compile_user_constraints(
            medical_flags=[],
            allergy_flags=[],
            dietary_pref="vegan",
        )
        forbidden = {item.lower() for item in vegan_result["forbidden_ingredients"]}
        assert "milk" in forbidden
        assert "paneer" in forbidden
        assert "egg" in forbidden

        diabetes_result = engine.compile_user_constraints(
            medical_flags=["diabetes"],
            allergy_flags=[],
            dietary_pref="veg",
        )
        soft_targets = {rule["applies_to"] for rule in diabetes_result["soft_restrictions"]}
        hard_targets = set(diabetes_result["forbidden_ingredients"])
        assert "white rice" in soft_targets or "white rice" in hard_targets
        assert "white rice" not in hard_targets or "white rice" not in soft_targets

        print(f"GERD forbidden count: {len(gerd_result['forbidden_ingredients'])}")
        print(f"Vegan forbidden count: {len(vegan_result['forbidden_ingredients'])}")
        print(f"Diabetes soft restrictions: {len(diabetes_result['soft_restrictions'])}")
        print("\nResult: PASS")
        return True
    except Exception as exc:
        print("\nResult: FAIL")
        print(f"Diagnostics: {exc}")
        return False


if __name__ == "__main__":
    success = test_rule_engine()
    sys.exit(0 if success else 1)
