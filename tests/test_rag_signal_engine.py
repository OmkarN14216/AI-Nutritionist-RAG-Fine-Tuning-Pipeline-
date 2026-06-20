import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.guideline_interpreter import GuidelineInterpreter, RAGSignals


def test_rag_signal_extraction():
    print("\n==================================================")
    print("Testing Layer 6: RAG Signal Engine")
    print("==================================================")

    mock_contexts = [
        "[ICMR Manual - Page 12]: Patients should consume whole grains, cereals, and millets like oats or brown rice for fiber.",
        "[ICMR Manual - Page 45]: Increase protein sources like tofu, egg white, or paneer to support muscle retention.",
        "[ICMR Manual - Page 89]: Ensure high-quality pulses, beans, and lentils are included daily in meals.",
    ]

    try:
        signals = GuidelineInterpreter.extract_planner_signals(mock_contexts)

        assert isinstance(signals, RAGSignals)
        assert len(signals.signals) > 0

        for signal in signals.signals:
            assert hasattr(signal, "food_category")
            assert hasattr(signal, "score_delta")
            assert hasattr(signal, "source")
            assert hasattr(signal, "food_bonuses")

        grain_bonus = signals.get_bonus_for_food("Brown Rice", "grain")
        pulse_bonus = signals.get_bonus_for_food("Moong Dal", "pulse")
        signal_dicts = signals.to_list()

        assert grain_bonus > 0.0
        assert pulse_bonus > 0.0
        assert isinstance(signal_dicts, list)

        print(f"Signals count extracted: {len(signals.signals)}")
        print(f"Brown Rice (grain) bonus: {grain_bonus}")
        print(f"Moong Dal (pulse) bonus: {pulse_bonus}")
        print("\nResult: PASS")
        return True
    except Exception as exc:
        print("\nResult: FAIL")
        print(f"Diagnostics: {exc}")
        return False


if __name__ == "__main__":
    success = test_rag_signal_extraction()
    sys.exit(0 if success else 1)
