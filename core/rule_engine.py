import json
import os
from typing import List, Dict, Any, Set

class GuardrailRuleEngine:
    """
    Ingests official ICMR-NIN structured rules to extract hard item bans (forbidden_ingredients),
    soft restrictions, and output clinical system-level generation directives.
    """
    def __init__(self, config_path: str = "config/rules.json"):
        self.config_path = config_path
        self.rules_registry = self._load_rules_json()

    def _load_rules_json(self) -> Dict[str, Any]:
        """Reads and validates the master configuration file."""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(
                f"Configuration file missing at path: '{self.config_path}'. "
                f"Please ensure rules.json exists in your config directory."
            )
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Malformed JSON layout detected in your rulebook: {str(e)}")

    def compile_user_constraints(
        self, medical_flags: List[str], allergy_flags: List[str], dietary_pref: str
    ) -> Dict[str, Any]:
        """
        Gathers medical concerns, allergies, and lifestyle factors to assemble
        a single deduplicated list of banned ingredients, soft restrictions,
        and specific clinical commands.
        """
        active_conditions = [m.lower().strip() for m in medical_flags]
        active_allergies = [a.lower().strip() for a in allergy_flags]
        active_diet = dietary_pref.lower().strip()

        # Gather active contexts for rule matching
        all_active_contexts = set(active_conditions + active_allergies + [active_diet])

        hard_forbidden: Set[str] = set()
        soft_restrictions: List[Dict[str, Any]] = []
        clinical_guardrail_directives: List[str] = []

        # 1. Parse clinical directives (text commands)
        directives_map = self.rules_registry.get("directives", {})
        for context in all_active_contexts:
            if context in directives_map:
                clinical_guardrail_directives.append(directives_map[context])

        # 2. Parse structured rules
        structured_rules = self.rules_registry.get("structured_rules", [])
        for rule in structured_rules:
            rule_cond = rule.get("condition", "").lower().strip()
            if rule_cond in all_active_contexts:
                food_item = rule.get("applies_to", "").lower().strip()
                severity = rule.get("severity", "hard").lower().strip()
                restriction = rule.get("restriction", "forbid").lower().strip()

                if severity == "hard" or restriction == "forbid":
                    hard_forbidden.add(food_item)
                else:
                    soft_restrictions.append({
                        "applies_to": food_item,
                        "restriction": restriction,
                        "severity": severity,
                        "source": rule.get("source", "ICMR-NIN"),
                        "condition": rule.get("condition", "")
                    })

        # Conflict Resolution: If any food is in hard_forbidden, remove it from soft_restrictions
        soft_restrictions = [
            r for r in soft_restrictions 
            if r["applies_to"] not in hard_forbidden
        ]

        return {
            "forbidden_ingredients": sorted(list(hard_forbidden)),
            "soft_restrictions": soft_restrictions,
            "clinical_guardrail_directives": clinical_guardrail_directives
        }