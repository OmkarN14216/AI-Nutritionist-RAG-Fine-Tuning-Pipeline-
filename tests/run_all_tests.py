import importlib.util
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _load_test_module(relative_path, function_name):
    module_path = os.path.join(ROOT, relative_path)
    spec = importlib.util.spec_from_file_location(
        os.path.basename(relative_path).replace(".py", ""),
        module_path,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, function_name)()


def _run_profile_suite():
    from core.pipeline import PROFILES, run_profile_pipeline

    passed = 0
    total = len(PROFILES)
    failing = []

    for profile in PROFILES:
        outcome = run_profile_pipeline(profile, verbose=False)
        if outcome["passed"]:
            passed += 1
        else:
            reason = outcome.get("error") or "macro/audit mismatch"
            failing.append(f"{profile['name']} ({reason})")

    return passed, total, failing


def main():
    os.chdir(ROOT)

    layer_tests = [
        ("Food Database", "tests/test_food_database.py", "test_food_database"),
        ("Layer 3 Rule Engine", "tests/test_rule_engine.py", "test_rule_engine"),
        ("Layer 4 Food Filter", "tests/test_food_filter.py", "test_food_filter"),
        ("Layer 6 RAG Engine", "tests/test_rag_signal_engine.py", "test_rag_signal_extraction"),
        ("Layer 7 Meal Planner", "tests/test_meal_planner.py", "test_meal_planner"),
        ("Layer 7 Meal Optimizer", "tests/test_meal_optimizer.py", "test_meal_optimization"),
        ("Layer 8 Portion Optimizer", "tests/test_portion_optimizer.py", "test_portion_optimization"),
        ("Layer 9 Audit Engine", "tests/test_audit_engine.py", "test_audit_validation"),
        ("End-to-End Pipeline", "tests/test_end_to_end_pipeline.py", "run_end_to_end_test"),
        ("Weekly Planner", "tests/test_weekly_planner.py", "test_weekly_planner"),
        ("Weekly Diversity", "tests/test_weekly_diversity.py", "test_weekly_diversity"),
        ("Weekly Audit", "tests/test_weekly_audit.py", "test_weekly_audit"),
        ("Weekly Pipeline", "tests/test_weekly_pipeline.py", "test_weekly_pipeline"),
    ]

    print("\n==================================================")
    print("AI NUTRITIONIST TEST RUNNER")
    print("==================================================")

    layer_results = []
    all_pass = True

    for label, path, function_name in layer_tests:
        try:
            passed = _load_test_module(path, function_name)
        except Exception as exc:
            passed = False
            print(f"\n{label} .......... FAIL")
            print(f"Diagnostics: {exc}")
        status = "PASS" if passed else "FAIL"
        layer_results.append((label, status))
        print(f"{label} .......... {status}")
        if not passed:
            all_pass = False

    profile_passed, profile_total, failing_profiles = _run_profile_suite()
    print("\nProfile Suite:")
    print(f"{profile_passed} / {profile_total} PASS")
    if failing_profiles:
        print("Failures:")
        for item in failing_profiles:
            print(f"  - {item}")

    print("\n==================================================")
    print("SUMMARY")
    print("==================================================")
    for label, status in layer_results:
        print(f"{label}: {status}")
    print(f"Profile Suite: {profile_passed}/{profile_total} PASS")
    print("==================================================")

    if not all_pass or profile_passed < 10:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
