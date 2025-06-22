"""
Runs the StatcheckTester on a given file three times and returns the most frequent output.
"""

import time
from collections import Counter
from io import StringIO

import pandas as pd
from pipeline import StatcheckTester


def main() -> None:

    tester = StatcheckTester()
    file_path = input("Please provide the file path to the context you want to analyse:\n")
    file_context = tester.read_context_from_file(file_path)
    start_time = time.time() # Start time after the file is read
    if not file_context:
        return

    results_list = []
    for i in range(3):
        print(f"Run {i + 1} of 3")
        df = tester.perform_statcheck_test(file_context)
        if df is not None:
            results_list.append(df)
        else:
            print("No results in this run.")

    if results_list:
        results_csv = [df.to_csv(index=False) for df in results_list]
        counts = Counter(results_csv)
        most_common_csv, _ = counts.most_common(1)[0]
        most_common_df = pd.read_csv(StringIO(most_common_csv))
        print("\nMost frequent result:")
        print(most_common_df)
    else:
        print("Inconsistent results, please run the test again.")

    total_time = time.time() - start_time
    print(f"\nTotal running time: {total_time:.2f} seconds")


if __name__ == "__main__":
    main()