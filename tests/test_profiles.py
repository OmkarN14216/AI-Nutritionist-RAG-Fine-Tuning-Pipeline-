import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.pipeline import PROFILES, run_profile_pipeline


def main():
    success_count = 0
    total_count = len(PROFILES)
    results = []

    for profile in PROFILES:
        outcome = run_profile_pipeline(profile, verbose=False)
        results.append(outcome)
        if outcome["passed"]:
            success_count += 1

        print(f"\nProfile Name: {profile['name']}")
        print("-" * 40)
        if outcome.get("error"):
            print(f"Pipeline FAIL: {outcome['error']}")
        else:
            diag = outcome["diagnostics"]
            print(f"Diagnostics for {profile['name']}:")
            print(
                f"  Calories       (Target: {diag['calories']['target']}, "
                f"Actual: {diag['calories']['actual']}): "
                f"{'PASS' if diag['calories']['pass'] else 'FAIL'}"
            )
            print(
                f"  Protein        (Target: {diag['protein']['target']}g, "
                f"Actual: {diag['protein']['actual']}g): "
                f"{'PASS' if diag['protein']['pass'] else 'FAIL'}"
            )
            print(
                f"  Forbidden Foods (Ban Count: {diag['forbidden_foods']['ban_count']}): "
                f"{'PASS' if diag['forbidden_foods']['pass'] else 'FAIL'}"
            )
            print(
                f"  Audit Report   (Passed Status): "
                f"{'PASS' if diag['audit']['pass'] else 'FAIL'}"
            )
        print(f"Overall Result: {'PASS' if outcome['passed'] else 'FAIL'}")

    print("\n" + "=" * 50)
    print(f"PROFILE SUITE SUMMARY: {success_count}/{total_count} Passed")
    print("=" * 50)

    if success_count == total_count:
        sys.exit(0)
    sys.exit(1)


if __name__ == "__main__":
    main()
