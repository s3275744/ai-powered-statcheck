"""
Core logic for extracting statistical tests and running AI-powered statcheck.
Use AI to automatically extract reported statistical tests from a given context and perform the statcheck to check for inconsistencies.

Credits
-------
The functionality is heavily inspired by the original statcheck tool, created by Michèle Nuijten.
(https://github.com/MicheleNuijten/statcheck)
(https://michelenuijten.shinyapps.io/statcheck-web/)
"""

import ast
import os

import fitz  # PyMuPDF
import pandas as pd
import scipy.stats as stats
from bs4 import BeautifulSoup

# Local imports
from config import (
    API_KEY,
    MAX_WORDS,
    OVERLAP_WORDS,
    SIGNIFICANCE_LEVEL,
    STATCHECK_PROMPT,
    apply_pandas_display_options,
)
from openai import OpenAI

# ------------------------------------------------------------------------- 
# Pandas display options
# -------------------------------------------------------------------------
apply_pandas_display_options() # Applies pandas display options for better readability

# ------------------------------------------------------------------------- 
# Main class, StatcheckTester
# -------------------------------------------------------------------------
class StatcheckTester:
    """
    Extracts NHST tests from scientific text using AI and checks their consistency using Python.
    """

    # Initialization
    def __init__(self) -> None:
        self.api_key = API_KEY  # Get the API key from the config file
        self.client = OpenAI(api_key=self.api_key)  # Initialize the OpenAI client

    # ------------------------------------------------------------------
    # Statcheck core calculations
    # ------------------------------------------------------------------
    @staticmethod
    def calculate_p_value(
        test_type: str,
        df1: float | None,
        df2: float | None,
        test_value: float | None,
        operator: str,
        reported_p_value: str | None,
        epsilon: float | None,
        tail: str = "two"
    ) -> tuple[bool, tuple[float | None, float | None]]:
        """
        Calculate the valid p-value range for different statistical tests.

        :param test_type: The type of statistical test ('r', 't', 'f', 'chi2', or 'z').
        :param df1: The first degree of freedom (set to None if not applicable (only z-tests)).
        :param df2: The second degree of freedom (set to None if not applicable).
        :param test_value: The test statistic value.
        :param operator: The operator used in the reported p-value ('=', '<', or '>').
        :param reported_p_value: The reported p-value as a string (e.g., '0.05' or 'ns').
        :param epsilon: The epsilon value for Huynh-Feldt correction (set to None if not applicable).
        :param tail: Specify 'one' for a one-tailed test or 'two' for a two-tailed test (default is 'two').
        :return: A tuple containing:
            - A boolean indicating whether the reported p-value is consistent with the recalculated range.
            - A tuple with the recalculated valid p-value range (lower bound, upper bound).
        """
        # Check if required degrees of freedom are missing
        if (test_type in ["t", "r", "chi2"] and df1 is None) or (test_type == "f" and (df1 is None or df2 is None)):
            return False, (None, None)

        # Calculate the rounding boundaries for the test statistic
        decimal_places = max(StatcheckTester.get_decimal_places(str(test_value)), 2)  # Treat 1 decimal as 2
        rounding_increment = 0.5 * 10 ** (-decimal_places)
        lower_test_value = test_value - rounding_increment
        upper_test_value = test_value + rounding_increment - 1e-10

        # For t-tests and similar, calculate p-values at the lower and upper test_value bounds
        if test_type == "r":
            # Correlation test (r)
            # Convert to t-values
            t_lower = (lower_test_value * ((df1) ** 0.5) / ((1 - lower_test_value**2) ** 0.5))
            t_upper = (upper_test_value * ((df1) ** 0.5) / ((1 - upper_test_value**2) ** 0.5))

            # Calculate p-values at lower and upper test_value bounds
            p_lower = stats.t.sf(abs(t_lower), df1)
            p_upper = stats.t.sf(abs(t_upper), df1)

        elif test_type == "t":
            # t-test
            # Calculate p-values at lower and upper test_value bounds
            p_lower = stats.t.sf(abs(lower_test_value), df1)
            p_upper = stats.t.sf(abs(upper_test_value), df1)

        elif test_type == "f":
            # Only apply the Huynh-Feldt correction if epsilon is not None and df1, df2 are both integers
            if epsilon is not None and isinstance(df1, int) and isinstance(df2, int):
                corrected_df1 = epsilon * df1
                corrected_df2 = epsilon * df2
                p_lower = stats.f.sf(lower_test_value, corrected_df1, corrected_df2)
                p_upper = stats.f.sf(upper_test_value, corrected_df1, corrected_df2)
            else:
                # Standard F-test (or df1/df2 are already floats, implying correction was applied previously)
                p_lower = stats.f.sf(lower_test_value, df1, df2)
                p_upper = stats.f.sf(upper_test_value, df1, df2)

        elif test_type == "chi2":
            # Chi-square test
            # Calculate p-values at lower and upper test_value bounds
            p_lower = stats.chi2.sf(lower_test_value, df1)
            p_upper = stats.chi2.sf(upper_test_value, df1)

        elif test_type == "z":
            # Z-test (does not require degrees of freedom)
            # Calculate p-values at lower and upper test_value bounds
            p_lower = stats.norm.sf(abs(lower_test_value))
            p_upper = stats.norm.sf(abs(upper_test_value))

        else:
            # Unknown test type
            return False, (None, None)

        # Adjust for one-tailed or two-tailed tests where applicable (not for chi2 and f)
        if test_type not in ["chi2", "f"]:
            if tail == "two":
                # For two-tailed tests, double the one-tailed p-value
                p_lower = min(p_lower * 2, 1)
                p_upper = min(p_upper * 2, 1)
            elif tail != "one":
                return False, (None, None)

        # Ensure p_lower is the smaller p-value
        p_value_lower = min(p_lower, p_upper)
        p_value_upper = max(p_lower, p_upper)

        # Handle reported_p_value being 'ns'
        if reported_p_value == "ns":
            return False, (p_value_lower, p_value_upper)

        # Convert reported_p_value to numeric if possible
        try:
            reported_p_value = float(reported_p_value)
        except ValueError:
            # Cannot convert to numeric
            return False, (None, None)

        consistent = StatcheckTester.compare_p_values(
            (p_value_lower, p_value_upper), operator, reported_p_value
        )

        return consistent, (p_value_lower, p_value_upper)

    @staticmethod
    def get_decimal_places(value_str: str) -> int:
        """
        Function to calculate the number of decimal places in a value, including trailing zeros.

        :param value_str: The string representation of the value.
        :return: The number of decimal places in the value.
        """
        return len(value_str.split(".")[1]) if "." in value_str else 0

    @staticmethod
    def compare_p_values(
        recalculated_p_value_range: tuple[float | None, float | None],
        operator: str,
        reported_value: float
    ) -> bool:
        """
        Compare recalculated valid p-value range with reported p-value.

        :param recalculated_p_value_range: Tuple (p_value_lower, p_value_upper).
        :param operator: The operator used in the reported p-value ('=', '<', '>').
        :param reported_value: The numerical value of the reported p-value.
        :return: True if consistent, False otherwise.
        """
        # Unpack the recalculated p-value range from the tuple
        p_value_lower, p_value_upper = recalculated_p_value_range

        if operator == "<":
            return p_value_lower < reported_value

        if operator == ">":
            return p_value_upper > reported_value

        if operator == "=":
            decimal_places = StatcheckTester.get_decimal_places(str(reported_value)) if "." in str(reported_value) else 0

            rounding_increment = 0.5 * 10 ** (-decimal_places)
            reported_p_lower = reported_value - rounding_increment
            reported_p_upper = reported_value + rounding_increment - 1e-10

            # Check if the reported p-value falls within the recalculated range
            if reported_p_upper >= p_value_lower and reported_p_lower <= p_value_upper:
                return True

            else:
                return False

    @staticmethod
    def determine_reported_significance(
        operator: str,
        reported_p_value: str,
        significance_level: float
    ) -> bool | None:
        """
        Determine the significance of the REPORTED p-value based on the provided operator and significance level.

        :param operator: The operator used in the reported p-value ('=', '<', '>').
        :param reported_p_value: The numerical value of the reported p-value.
        :return: True if significant, False if not significant.
        """
        if reported_p_value == "ns":
            return None  # Cannot determine significance for 'ns'

        try:
            reported_p_value = float(reported_p_value)
        except ValueError:
            return None  # If it cannot be converted, treat as indeterminate

        if operator in ("=", "<"):
            return reported_p_value <= significance_level
        elif operator == ">":
            return reported_p_value < significance_level
        return None  # Invalid operator

    @staticmethod
    def determine_recalculated_significance(
        p_value_range: tuple[float | None, float | None],
        significance_level: float
    ) -> bool | None:
        """
        Determine the significance of the RECALCULATED p-value range based on the significance level.

        :param p_value_range: Tuple (lower, upper) of the recalculated p-value range.
        :param significance_level: The significance level (set at 0.05 in cofig file).
        :return: True if significant, False if not significant.
        """
        lower, upper = p_value_range

        if upper < significance_level:
            return True
        if lower > significance_level:
            return False
        return None

    # ------------------------------------------------------------------
    # OpenAI interaction
    # ------------------------------------------------------------------
    def extract_data_from_text(self, context: str) -> str | None:

        """
        Send context to the gpt-4o-mini model to extract reported statistical tests.
        The model will return the extracted statistical tests as a list of dictionaries (still in string format).
        The list of dictionaries will look like this:
        tests = [
            {"test_type": "<test_type>", "df1": <df1>, "df2": <df2>, "test_value": <test_value>, "operator": "<operator>", "reported_p_value": <reported_p_value>, "tail": "<tail>"},
            ...
        ]

        :param context: The scientific text containing reported statistical tests.
        :return: The extracted test data as a string.
        """
        prompt = STATCHECK_PROMPT.format(context=context)

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system",
                    "content": "You are an assistant that extracts statistical test values from scientific text.",},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
        )

        response_content = response.choices[0].message.content.strip()
        # Remove any code blocks that might wrap the response
        response_content = (
            response_content.replace("```python", "")
            .replace("```json", "")
            .replace("```", "").strip()
        )

        # Results must start with 'tests ='
        if response_content.startswith("tests ="):
            return response_content[len("tests = ") :].strip()

        return None

    # ------------------------------------------------------------------
    # File reading
    # ------------------------------------------------------------------
    @staticmethod
    def read_context_from_file(file_path: str) -> list[str]:
        """
        Reads the context from a .txt, .pdf, .html, or .htm file and splits it into segments.

        :param file_path: The path to the file containing the context.
        :return: A list of context segments, each as a string.
        """
        try:
            # Get the lowercase file extension
            extension = os.path.splitext(file_path.strip())[-1].lower()

            # Read file content based on its extension
            if extension == ".txt":
                with open(file_path, "r", encoding="utf-8") as f:
                    text = f.read()

            elif extension == ".pdf":
                text = ""
                with fitz.open(file_path) as doc:
                    for page in doc:
                        text += page.get_text() + "\n"

            elif extension in (".html", ".htm"):
                with open(file_path, "r", encoding="utf-8") as f:
                    soup = BeautifulSoup(f, "html.parser")
                    text = soup.get_text(separator=" ")

            else:
                print("Unsupported file type. Please supply a .txt, .pdf, .html, or .htm file.")
                return []

            # Split text into overlapping segments
            words = text.split()
            segments = []
            step = MAX_WORDS - OVERLAP_WORDS # Get variables from config.py

            for i in range(0, len(words), step):
                segment = words[i:i + MAX_WORDS]
                segments.append(" ".join(segment))

            return segments

        except FileNotFoundError:
            print("File not found. Please provide a valid path.")
            return []

    # ------------------------------------------------------------------
    # StatcheckTester pipeline entry point
    # ------------------------------------------------------------------
    def perform_statcheck_test(self, file_context: list[str]) -> pd.DataFrame | None:
        """
        Extract test data from context segment(s) and perform statcheck.

        :param file_context: A list of context segments.
        :return: A pandas DataFrame containing the statcheck results (or None if no results).
        """
        significance_level = SIGNIFICANCE_LEVEL # Get significance level from config.py
        all_tests = []

        # ------------------------------ Extraction loop ------------------------------
        for idx, context in enumerate(file_context):
            print(f"Processing segment {idx + 1}/{len(file_context)}...")
            test_data = self.extract_data_from_text(context)
            if test_data is None:
                continue

            try:
                tests = ast.literal_eval(test_data)
                for test in tests:
                    if all_tests and test == all_tests[-1]:
                        continue  # Skip duplicates caused by segment overlap
                    all_tests.append(test)
            except Exception as e:
                print(f"Error parsing extracted test data: {e}")
                continue

        # ------------------------------ Run statcheck --------------------------------
        if not all_tests:
            return None

        statcheck_results = []

        for test in all_tests:
            test_type = test.get("test_type")
            df1 = test.get("df1")
            df2 = test.get("df2")
            test_value = test.get("test_value")
            operator = test.get("operator")
            reported_p_value = test.get("reported_p_value")
            epsilon = test.get("epsilon")
            tail = test.get("tail")

            # ---------------------- Skip incomplete entries ----------------------
            if reported_p_value is None or test_value is None:
                continue

            # ---------------------- Handle "ns" case ----------------------
            if reported_p_value == "ns":
                notes_list = ["Reported as ns."]
                apa_reporting = f"{test_type}({df1}{', ' + str(df2) if df2 is not None else ''}) = {test_value}, ns"
                consistent_str = "Cannot determine"
                valid_p_value_range_str = "N/A"

                statcheck_results.append(
                    {
                        "Consistent": consistent_str,
                        "APA Reporting": apa_reporting,
                        "Reported P-value": "ns",
                        "Valid P-value Range": valid_p_value_range_str,
                        "Notes": " ".join(notes_list),
                    }
                )
                continue

            # ---------------------- Validate DF requirements ----------------------
            if test_type == "r" and df1 is None:
                notes_list = ["Correlation test requires degrees of freedom (df1). None provided."]
                apa_reporting = f"{test_type} = {test_value:.2f}"
                consistent_str = "Cannot determine"
                valid_p_value_range_str = "N/A"
                statcheck_results.append(
                    {
                        "Consistent": consistent_str,
                        "APA Reporting": apa_reporting,
                        "Reported P-value": f"{operator} {reported_p_value}" if reported_p_value != "ns" else "ns",
                        "Valid P-value Range": valid_p_value_range_str,
                        "Notes": " ".join(notes_list),
                    }
                )
                continue  # Skip this test

            else:
                # ------------------ Calculate p-value range ------------------
                consistent, p_value_range = self.calculate_p_value(
                    test_type,
                    df1,
                    df2,
                    test_value,
                    operator,
                    reported_p_value,
                    epsilon if test_type == "f" and epsilon is not None and isinstance(df1, int) and isinstance(df2, int) else None,
                    tail,
                )

                # String displayed in the final df output
                valid_p_value_range_str = (f"{p_value_range[0]:.5f} to {p_value_range[1]:.5f}" if all(p_value_range) else "N/A")

                # ------------------ Determine significance ------------------
                reported_significant = self.determine_reported_significance(operator, reported_p_value, significance_level)

                # Determine if recalculated p-value range indicates significance at SIGNIFICANCE_LEVEL
                if p_value_range[0] is not None and p_value_range[1] is not None:
                    recalculated_significant = self.determine_recalculated_significance(p_value_range, significance_level)
                else:
                    recalculated_significant = None

                # ------------------ Check consistency ------------------
                gross_inconsistency = (
                    reported_significant is not None and recalculated_significant is not None
                    and reported_significant != recalculated_significant
                )

                consistent_str = "Yes" if consistent else "No"
                notes_list = []

                if reported_p_value == 0:
                    notes_list.append("A p-value is never exactly 0.")
                    consistent = False

                if p_value_range[0] is None and test_type == "f" and df2 is None:
                    notes_list.append("F-test requires two DF. Only one DF provided.")
                    consistent_str = "Cannot determine"
                elif not consistent:
                    if gross_inconsistency:
                        notes_list.append("Gross inconsistency: reported p-value and recalculated p-value differ in significance.")
                    else:
                        notes_list.append("Recalculated p-value does not match the reported p-value.")

                # ------------------ One-tailed edge case ------------------
                if test_type in ["t", "z", "r"] and not consistent and tail == "two":
                    consistent_one_tailed, _ = self.calculate_p_value(
                        test_type, df1, df2, test_value, operator, reported_p_value, None, tail="one"
                    )
                    if consistent_one_tailed:
                        notes_list.append("Consistent for one-tailed, inconsistent for two-tailed.")

            # ------------------ Format APA Reporting ------------------
            if test_type == "f" and epsilon is not None and isinstance(df1, int) and isinstance(df2, int):
                corrected_df1 = round(epsilon * df1, 2)
                corrected_df2 = round(epsilon * df2, 2)
                apa_reporting = f"{test_type}({corrected_df1}, {corrected_df2}) = {test_value:.2f}"
                notes_list.append(f"Degrees of freedom were adjusted due to a Huynh-Feldt correction. Epsilon = {epsilon}.")
            elif df1 is not None:
                apa_reporting = f"{test_type}({df1}{', ' + str(df2) if df2 is not None else ''}) = {test_value:.2f}"
            else:
                # z-test do not require degrees of freedom
                apa_reporting = f"{test_type} = {test_value:.2f}"

            notes = "-" if not notes_list else " ".join(notes_list)

            # ------------------ Append result ------------------
            statcheck_results.append(
                {
                    "Consistent": consistent_str,
                    "APA Reporting": apa_reporting,
                    "Reported P-value": f"{operator} {reported_p_value}" if reported_p_value != "ns" else "ns",
                    "Valid P-value Range": valid_p_value_range_str,
                    "Notes": notes,
                }
            )

        # ------------------------------ Return results --------------------------------
        if statcheck_results:
            df_statcheck_results = pd.DataFrame(statcheck_results)[
                ["Consistent", "APA Reporting", "Reported P-value", "Valid P-value Range", "Notes"]
            ]
            return df_statcheck_results

        return None
