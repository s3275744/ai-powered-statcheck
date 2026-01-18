"""
Runs the StatcheckTester on all files in input_pdfs/.
"""

import os
import time

from pipeline import StatcheckTester

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".html", ".htm"}


def main() -> None:
    tester = StatcheckTester()

    # Resolve input_pdfs relative to current working directory (statcheck/)
    project_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..")
    )

    input_dir = os.path.join(project_root, "data", "input_pdfs")

    if not os.path.isdir(input_dir):
        print(f"Input directory not found: {input_dir}")
        return

    files = [
        f for f in os.listdir(input_dir)
        if os.path.splitext(f)[1].lower() in SUPPORTED_EXTENSIONS
    ]

    if not files:
        print("No supported files found in input_pdfs/.")
        return

    print(f"Found {len(files)} file(s) to analyse.\n")

    for filename in files:
        file_path = os.path.join(input_dir, filename)
        print(f"{'-'*80}")
        print(f"Analysing file: {filename}")

        file_context = tester.read_context_from_file(file_path)
        if not file_context:
            print("No readable content found, skipping.")
            continue

        start_time = time.time()
        result_df = tester.perform_statcheck_test(file_context)
        total_time = time.time() - start_time

        if result_df is not None:
            print("\nStatcheck result:")
            print(result_df)
        else:
            print("No statistical tests were found.")

        print(f"\nRunning time: {total_time:.2f} seconds\n")


if __name__ == "__main__":
    main()
