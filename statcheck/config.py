"""
Configuration file for the StatcheckTester pipeline.
This file contains all the hyper-parameters and prompts used in the pipeline.
"""

import os

import pandas as pd
from dotenv import load_dotenv

# -------------------------------------------------------------------------
# Environment
# -------------------------------------------------------------------------
load_dotenv()
API_KEY: str | None = os.getenv("OPENAI_API_KEY")

# ------------------------------------------------------------------------- 
# Pipeline hyper‑parameters
# -------------------------------------------------------------------------
MAX_WORDS: int = 500 # Maximum number of words per text segment sent to the AI model
OVERLAP_WORDS: int = 8 # Number of overlap words between segments

# Default alpha value for NHST tests
SIGNIFICANCE_LEVEL: float = 0.05

# ------------------------------------------------------------------------- 
# Prompts
# -------------------------------------------------------------------------
STATCHECK_PROMPT: str = ("""
        You are an AI assistant that extracts statistical test results from scientific text.

        Please extract ALL statistical tests reported in the following text. For each test, extract the following components:

        - test_type: one of 'r', 't', 'f', 'chi2', 'z'.
        - df1: First degree of freedom (float or integer). If not applicable, set to None.
        - df2: Second degree of freedom (float or integer). If not applicable, set to None.
        - test_value: The test statistic value (float).
        - operator: The operator used in the reported p-value ('=', '<', '>').
        - reported_p_value: The numerical value of the reported p-value (float) if available, or 'ns' if reported as not significant.
        - epsilon (float): Only extract when a Huynh-Feldt correction is mentioned. If not applicable, set to None.
        - tail: 'one' or 'two'. Assume 'two' unless explicitly stated.

        Guidelines:

        - Do not extract any tests that does not EXPLICITY mention one of the predetermined test types (e.g., t, r, f, chi2, z).
        - Do not extract test that are incomplete (i.e., the minimal requirements are: test_type, df1, test_value, operator, reported_p_value).
        - IMPORTANT: EXTRACT THE CORRECT OPERATOR FROM THE P-VALUE (E.G., '=', '<', '>').
        - If you are not completely certain that a test meets the minimal requirements (e.g., test_type is not explicity mentioned), do not extract it.
        - You must never infer or assume test types, degrees of freedom, or test values based on contextual clues, reported means, or p-values. Only extract statistical tests that are explicitly reported in APA format and contain a clearly labeled test type (e.g., “t”, “z”, “f”, etc.).
        - Be tolerant of minor typos or variations in reporting.
        - Recognize tests even if they are embedded in sentences or reported in a non-standard way.
        - **Pay special attention to distinguishing between chi-square tests (often denoted as 'χ²' or 'chi2') and F-tests. Example: "𝜒2 (df =97)=80.12, p=.893"**
        - A chi-sqaure test can also be reported as "G-square", "G^2", or "G2". Example: G2(18) = 17.50, p =.489, is a chi2 test. The test type should still be chi2.
        - **IMPORTANT: "rho" is not the same as "r". Do not interpret "rho" as an "r" test.**
        - For p-values reported with inequality signs (e.g., p < 0.05), extract both the operator ('<') and the numerical value (0.05). This goes for all operators.
        - Do not perform any calculations or inferences beyond what's explicitly stated.
        - It can occur that a test is split over multiple sentences. Example: "F"(1, 25) = 11.36, MSE = .040, ηp
        2 =
        .312, p = .002". Make sure to extract the test correctly, pay close attention to the operator.
        - If ANY of the components are missing or unclear, skip that test, especially the test_value.
        - Treat commas in numbers as thousand separators, not decimal points. Remove commas from numbers before extracting them. For example, '16,107' should be extracted as '16107' (sixteen thousand one hundred seven), not '16.107'.
        - Regarding chi2 tests: do not extract the sample size (N).
        - Only an F-test requires two degrees of freedom (df1, df2). For all other tests, only extract df1.
        - It can occur that a thousand separator (,) is used in the degree(s) of freedom. Example: "r(31,724) = -0.02" has df1 = 31724.
        - Do not extract tests that have not been described in this prompt before. Example: "B(31,801) = -.030, p <.001" should not be extracted, since the test type 'B' has not been described in the prompt.
        - Again, never extract other tests than the ones described in this prompt!
        - Only extract an epsilon value if it is explicitly mentioned in the context AND if a Huynh-Feldt correction was applied. Otherwise, set epsilon to None.

        - IMPORTANT: EPSILON IS REPORTED AS (ε) OR (Epsilon). EPSILON IS NOT THE SAME AS ETA SQUARED (η2) OR ETA (η).
            - EXAMPLE:  F(1, 82) = 4.03, p <.05, η =.22, is NOT a Huynh-Feldt correction. DO NOT EXTRACT EPSILON, BECAUSE THIS IS NOT AN EPSILON VALUE, BUT AN ETA VALUE.
            - YOU NEVER EXTRACT ETA VALUES (η2) OR ETA (η) AS EPSILON. ONLY EXTRACT EPSILON VALUES (ε) OR (Epsilon) AS EPSILON!

        - You can also encounter NHST tests reported in a table. In these cases, the reported_p_value is often displayed using a symbol (e.g., * for p < 0.05, ** for p < 0.01, *** for p < 0.001).
        - In these cases, extract p < 0.05 for *, p < 0.01 for **, and p < 0.001 for ***.
            - EXAMPLE: 5.27 (2, 67)** in the column "F" should be extracted as:
            - test_type: "f"
            - df1: 2
            - df2: 67
            - test_value: 5.27
            - operator: "<"
            - reported_p_value: "0.01"
        - BUT, ONLY EXTRACT TESTS THAT HAVE A STAR SYMBOL. DO NOT EXTRACT INCOMPLETE TESTS WITHOUT A STAR SYMBOL, EVEN IF THEY ARE NHST TESTS. THIS IS BECAUSE THERE IS NO WAY TO DETERMINE THE REPORTED P-VALUE WITHOUT A STAR SYMBOL OR WITHOUT THE P-VALUE EXPLICITLY MENTIONED.
            - EXAPMLE: "F(1, 3184) = 2.20" - YOU DO NOT EXTRACT THIS TEST, BECAUSE IT IS INCOMPLETE. IT DOES NOT HAVE A STAR SYMBOL, AND THE OPERATOR IS NOT EXPLICITLY MENTIONED.
            You extract this test as:
            - DO NOT EXTRACT - CONTINUE

        - It is also possible that you enocounter a text that has typesetting issues: characters such as  "<", ">", or "=" might not be properly extracted. If you encounter a NHST where everything is present except the operator, assume the operator is "<".
           - EXAMPLE: "F(1, 11) 83.93, p .001" - extract this as:
            - test_type: "f"
            - df1: 1
            - df2: 11
            - test_value: 83.93
            - operator: "<"
            - reported_p_value: "0.001"

           - EXAMPLE: "F(1, 15)
            6.1, p
            .05."
            Extract this as:
            - test_type: "f"
            - df1: 1
            - df2: 15
            - test_value: 6.1
            - operator: "<"
            - reported_p_value: "0.05"

        Format the result EXACTLY like this:

        tests = [
            {{"test_type": <test_type>, "df1": <df1>, "df2": <df2>, "test_value": <test_value>, "operator": <operator>, "reported_p_value": <reported_p_value>, "epsilon": <epsilon>, "tail": <tail>}},
            ...
        ]

        Now, extract the tests from the following text:

        {context}

        After you have read the text above, read it again to ensure you understand the instructions. Then, extract the reported statistical tests as requested.
        """)

# -------------------------------------------------------------------------
# Pandas display options
# -------------------------------------------------------------------------
def apply_pandas_display_options() -> None:
    """
    Standard console-friendly Pandas formatting.
    """
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 10_000)
    pd.set_option("display.colheader_justify", "center")
    pd.set_option("display.max_rows", None)
    pd.set_option("display.max_colwidth", None)