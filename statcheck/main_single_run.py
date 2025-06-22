"""
Runs the StatcheckTester on a given file once.
"""

import time

from pipeline import StatcheckTester


def main() -> None:
    tester = StatcheckTester()
    file_path = input("Please provide the file path to the context you want to analyse:\n")
    file_context = tester.read_context_from_file(file_path)
    start_time = time.time() # Start time after the file is read
    if not file_context:
        return

    result_df = tester.perform_statcheck_test(file_context)

    if result_df is not None:
        print("\nStatcheck result:")
        print(result_df)
    else:
        print("No statistical tests were found.")

    total_time = time.time() - start_time
    print(f"\nTotal running time: {total_time:.2f} seconds")


if __name__ == "__main__":
    main()
