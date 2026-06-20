import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.test_profiles import main

if __name__ == "__main__":
    # Just run main and print which ones pass/fail
    try:
        main()
    except SystemExit:
        pass
