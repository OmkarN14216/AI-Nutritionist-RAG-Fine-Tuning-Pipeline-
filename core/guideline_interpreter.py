from typing import Dict, List, Any

class RAGSignal:
    """Represents a structured guideline signal extracted from retrieved text."""
    def __init__(self, food_category: str, score_delta: float, source: str, food_bonuses: Dict[str, float] = None):
        self.food_category = food_category
        self.score_delta = score_delta
        self.source = source
        self.food_bonuses = food_bonuses or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "food_category": self.food_category,
            "score_delta": self.score_delta,
            "source": self.source,
            "food_bonuses": self.food_bonuses
        }


class RAGSignals:
    """Container for holding multiple RAGSignal objects and querying them."""
    def __init__(self, signals: List[RAGSignal] = None):
        self.signals = signals or []

    def get_bonus_for_food(self, food_name: str, food_category: str) -> float:
        """Determines the active score bonus for a food based on matching signals."""
        max_bonus = 0.0
        for signal in self.signals:
            # Match by category
            if signal.food_category.lower() == food_category.lower():
                val = signal.food_bonuses.get(food_name, signal.score_delta)
                max_bonus = max(max_bonus, float(val))
            # Match by specific food name if defined in food_bonuses
            elif food_name in signal.food_bonuses:
                val = signal.food_bonuses[food_name]
                max_bonus = max(max_bonus, float(val))
        return max_bonus

    def to_list(self) -> List[Dict[str, Any]]:
        return [sig.to_dict() for sig in self.signals]


class GuidelineInterpreter:
    """
    Parses retrieved ICMR-NIN guidelines to extract structured RAGSignals.
    Keep guideline interpreter 100% deterministic using keyword mappings.
    """
    FOOD_SIGNAL_RULES = [
        {
            "keywords": ["whole grain", "whole grains", "grain", "grains", "cereal", "millet", "millets"],
            "category": "grain",
            "score_delta": 1.0,
            "food_bonuses": {
                "Brown Rice": 1.5,
                "Roti": 1.0,
                "Oats": 1.5,
                "Poha": 0.5,
                "Upma": 0.5,
                "Idli": 0.5,
                "Dosa": 0.5,
                "White Rice": 0.0
            }
        },
        {
            "keywords": ["pulse", "pulses", "bean", "beans", "dal", "lentil", "lentils"],
            "category": "pulse",
            "score_delta": 1.5,
            "food_bonuses": {
                "Moong Dal": 1.5,
                "Masoor Dal": 1.5,
                "Chana Dal": 1.5,
                "Rajma": 1.5,
                "Chole": 1.5
            }
        },
        {
            "keywords": ["protein", "protein sources", "high protein"],
            "category": "protein",
            "score_delta": 1.0,
            "food_bonuses": {
                "Egg": 1.0,
                "Egg White": 1.0,
                "Paneer": 1.0,
                "Tofu": 1.0,
                "Soy Chunks": 1.0
            }
        },
        {
            "keywords": ["fruit", "fruits"],
            "category": "fruit",
            "score_delta": 0.5,
            "food_bonuses": {
                "Apple": 0.5,
                "Banana": 0.5
            }
        },
        {
            "keywords": ["milk", "curd", "yogurt", "dairy"],
            "category": "dairy",
            "score_delta": 0.5,
            "food_bonuses": {
                "Curd": 0.5,
                "Milk": 0.5
            }
        }
    ]

    @staticmethod
    def extract_planner_signals(retrieved_contexts: List[str]) -> RAGSignals:
        """Extracts structured signals from the retrieved text contexts."""
        signals_list = []
        
        for i, context in enumerate(retrieved_contexts or []):
            normalized_context = context.lower()
            source_name = f"ICMR Guideline Segment {i+1}"
            
            for rule in GuidelineInterpreter.FOOD_SIGNAL_RULES:
                if any(keyword in normalized_context for keyword in rule["keywords"]):
                    # Create a structured RAGSignal object
                    signal = RAGSignal(
                        food_category=rule["category"],
                        score_delta=rule["score_delta"],
                        source=source_name,
                        food_bonuses=rule["food_bonuses"]
                    )
                    signals_list.append(signal)
                    
        return RAGSignals(signals_list)