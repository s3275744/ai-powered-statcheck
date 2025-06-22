[![Python 3.10.11](https://img.shields.io/badge/python-3.10.11-blue.svg)](https://www.python.org/downloads/release/python-31011/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Linted with Ruff](https://img.shields.io/badge/linter-ruff-orange)](https://docs.astral.sh/ruff/)
[![OpenAI API](https://img.shields.io/badge/OpenAI-API-informational?logo=openai&logoColor=white&color=412991)](https://platform.openai.com/docs)



# bachelorThesis
This project contains two AI-powered Python scripts which can be used for automated statistical error detection. The following tests are included: the **GRIM Test** & **Statcheck**. Both scripts leverage AI to extract data from provided files and then use Python to perform the necessary calculations. This is to ensure that the calculations are done correctly, since AI models are still prone to making errors when it comes to mathematics.

# Credits
The creation of the code for the GRIM test has been inspired by the paper "_The GRIM Test: A Simple Technique Detects Numerous Anomalies in the Reporting of Results in Psychology_", `(Brown & Heathers, 2016)`. DOI: `10.1177/1948550616673876`.

The creation of the code for Statcheck has been inspired by the paper "_The prevalence of statistical reporting errors in psychology (1985-2013)_", `(Nuijten et al., 2016)`. DOI: `10.3758/s13428-015-0664-2`.

The GitHub page for the R package of `statcheck` created by Michèle Nuijten can be found [here](https://github.com/MicheleNuijten/statcheck). 

# Contents

- [Getting Started](#getting-started)
    - [Installation](#installation)
    - [Running the Tests](#running-the-tests)
- [GRIM Test](#grim-test)
    - [How It Works](#how-it-works)
- [Statcheck](#statcheck)
    - [How It Works](#how-it-works)
- [Important Tips](#important-tips)
- [Known issues](#known-issues)
    - [GRIM-Related Issues](#grim-related-issues)
    - [Statcheck-Related Issues](#statcheck-related-issues)
- [Code Quality](#code-quality)



# Getting Started

## Installation
First, clone the repository using Git. Make sure Python 3.10.11 is installed. Then, in the root directory of the project, install all dependencies by running: `$ pip install -r requirements.txt`. After all dependencies have successfully installed, create a `.env` file in the root directory of the project. This file should contain your environment variables. For this project, only the OpenAI API key is relevant. The `.env` file should be formattted as follows:

`OPENAI_API_KEY = "your_openai_api_key_here"`


Once this is done, everything should be installed and ready for use.

## Running the Tests
You can run the GRIM Test and Statcheck scripts by executing their corresponding Python file and providing the path to your `.pdf`, `.htm`, `.html`, or `.txt`  file when prompted.

 - To run the **GRIM Test**:
   
   Execute `$ python testers\GRIM\main.py`
    
 - To run **statcheck**:

   Execute `$ python testers\statcheck\main_single_run.py`
   
   Execute `$ python testers\statcheck\main_multiple_runs.py` if you want to automatically analyse the provided file three times. This improves consistency but increases runtime and costs.

# GRIM Test

The GRIM Test (Granularity-Related Inconsistency of Means) is a tool for detecting inconsistencies in reported statistical means within scientific texts. This code automates this test by using the `GPT-4o` AI model to automatically extract reported mean values along with their corresponding sample sizes from a provided file. 

> [!IMPORTANT]
> The test only works for means that are composed of integer data, since the calculation relies on the granularity of whole numbers to determine whether the mean is mathematically possible given the sample size. 


## How It Works

The process involves the following steps:

1. **Central class:**  The `GRIMTester` class contains all methods for reading context from files, extracting reported means and sample sizes, validating whether GRIM is applicable, performing the GRIM test, and presenting results.

2. **Convert:**  The `.pdf`, `.htm`, or `.html` file gets converted into plain text. `.txt` files are already in plain text.

3. **Segmentation and overlap:**  The plain text is split into segments of 1,000 words each, with an overlap of 200 words between consecutive segments. This larger context window increases the chances that all relevant parameters are captured together in the same context window.

4. **Extract data:**  The `extract_data_from_text` method uses the `GPT-4o` AI model to identify and extract reported means and sample sizes from each segment. The model is instructed to extract values only if:
   - The value is explicitly labelled as a `mean`.
   - The mean is based on discrete integer data (e.g., Likert scales).
   - A sample size (`N`) is explicitly mentioned and clearly linked to the mean.

   Besides extracting relevant data, the model is also instructed to return a `reasoning string`, in which the model must provide a brief justification for why the identified mean value is considered GRIM-applicable.

   This method transforms unstructured data (tests found in the text) into structured data: a Python list of dictionaries. Each extracted test is represented as a dictionary with the following keys:
   - `reported_mean`: The mean value as reported in the article (float).
   - `sample_size`: The sample size associated with the reported mean (integer).
   - `discrete_reasoning`: A brief explanation of why the mean value is considered GRIM-applicable (string). For example: `"mean of 7-point Likert responses clearly linked to N = 28 in same sentence"`.

5. **GRIM applicability check:**  This check removes entries from the final output that are not theoretically testable using the GRIM formula. More specifically, the sample size must not exceed `10^d`, where `d` is the number of decimal places in the reported mean. This is because *any* mean value where the sample size exceeds this threshold can be constructed from integer data, always resulting in a valid mean value. To reduce clutter in the final output, these entries are excluded from the final results.

6. **GRIM test:**  The `grim_test` method calculates if the reported mean is mathematically possible given the sample size and number of decimal places.

7. **Processing results:**  After extraction and testing, the results are added into a `DataFrame` and printed. Each test is displayed in a separate row with the following column headers:
   - `Consistent`: Indicates whether the reported mean passed the GRIM test (`Yes` or `No`).
   - `Reported Mean`: The original mean value as extracted from the text, including trailing zeros.
   - `Sample Size`: The corresponding sample size.
   - `Decimals`: The number of decimal places in the reported mean.
   - `Reasoning`: The AI-generated explanation for why the reported mean was considered GRIM-applicable.




# Statcheck
Statcheck is a tool for checking the consistency of reported statistical test results in scientific texts. It works as a "spellchecker" for statistics. It recalculates a valid _p_-value range based on the corresponding test statistic and degree(s) of freedom (a z-test only requires a test statistic). If the reported _p_-value falls within this valid range of _p_-values, the test is considered to be consistent. If the reported _p_-value does not fall within this range of valid _p_-values, the test is considered to be inconsistent. This script can recognise the following NHST results: t-tests, F-tests, correlations (r), z-tests & $\chi^2$ -tests.

> [!IMPORTANT]
> The script calculates a valid range of _p_-values, and the reported _p_-value must fall within this range to be considered consistent. There are two types of inconsistencies in which the script makes a distinction: _regular_ and _gross inconsistencies_. A _gross inconsistency_ occurs when a reported _p_-value indicates statistical significance, but the recalculated _p_-values show otherwise, or vice versa. A _regular inconsistency_ occurs when the reported _p_-value does not fall within the valid _p_-value range, but the (in)significance remains unchanged. 

### Example:

For a reported t-test with `t(30) = 1.96` and `p = 0.059`, the script calulates a valid _p_-value range between the largest and the smallest possible numbers that still round to `1.96`.

- Lower bound: `t = 1.964999...` gives a _p_-value of `0.05873`.
- Upper bound: `t = 1.955` gives a _p_-value of `0.05996`.

Since the reported _p_-value of `0.059` falls between the recalculated range of `0.05873 to 0.05996`, the test is consistent.

## How It Works

The process involves the following steps:

1. **Central class**: The `StatcheckTester` class contains all methods for reading context from files, extracting reported  statistical tests, recalculating a valid _p_-value range, comparison and presenting results.
2. **Convert**: The `.pdf`, `.htm` or `.html` file gets converted into plain text. `.txt` files are already in plain text.

3. **Segmentation and overlap**: The plain text is then split into segments of 500 words each, with an overlap of 8 words between consecutive segments. Using segmentation, the script does a much better job at correctly identifying all statistical tests in the entire context. The overlap ensures that each statistical test is detected, even if the test spans multiple segments (e.g., a test starting at the end of segment `n` and ending at the beginning of segment `n + 1`).

   
4. **Extract data**: The `extract_data_from_text` method uses the `GPT-4o-mini` AI model to identify and extract reported statistical tests from the text. This method transforms unstructured data (tests found in the text) into structured data: a Python list of dictionaries. Each extracted test is represented as a dictionary with the following keys:

    - `test_type`: One of `'r'`, `'t'`, `'f'`, `'chi2'`, `'z'`.
    - `df1`: First degree of freedom (float or integer). If not applicable, set to `None`.
    - `df2`: Second degree of freedom (float or integer). If not applicable, set to `None`.
    - `test_value`: The test statistic value (float).
    - `operator`: The operator used in the reported _p_-value (`=`, `<`, `>`).
    - `reported_p_value`: The numerical value of the reported _p_-value (float).
    - `epsilon`: Only applicable for Huynh-Feldt corrections (float). If not applicable, set to `None`.
    - `tail`: `'one'` or `'two'`. Assume `'two'` unless explicitly stated.

5. **Apply statistical correction (if applicable)**: Currently, the script can only account for Huynh-Feldt corrections. It automatically applies this correction when the following conditions apply:
    - `test_type` == `f`.
    - `epsilon` is not `None`.
    - `df1` & `df2` are `integers`.
  
    If there is an `epsilon` value reported, but `df1` & `df2` are not `integers`, this may imply the degrees of freedom have already been adjusted by the the `epsilon` value. In this case, the script does not reapply the correction.

10. **_p_-Value calculation**: The `calculate_p_value` method calculates a valid range of _p_-values (lower, upper) for each extracted test based on its parameters.

11. **Consistency checking**: The `compare_p_value` method checks the reported _p_-value falls within the range of the valid _p_-values (lower, upper). The script also makes a distinction between _gross inconsistencies_ and _regular inconsistencies_.

12. **Processing results**: After extraction and testing, the results are added into a DataFrame and printed. Each test is displayed in a separate row with the following column headers:

   - `Consistent`: Indicates whether the reported _p_-value falls within the valid recalculated range (`Yes` for consistent, `No` for inconsistent).
   - `APA Reporting`: Displays the correct APA reporting of the detected test, regardless of how the test is reported in the context.
   - `Reported p-Value`: The _p_-value as originally reported in the text.
   - `Valid p-Value Range`: The range of valid _p_-values (lower, upper) based on the test type, test statistic and degrees of freedom.
   - `Notes`: Any additional information regarding the result, such as the presence of gross or regular inconsistencies or the usage of a statistical correction.


# Important Tips

- **API key**: Ensure that you have an OpenAI API key stored in your `.env` file under the variable `OPENAI_API_KEY` for the code to work. Without an OpenAI API key, the code cannot use the `extract_data_from_text` method, which means the code cannot extract the relevant data from the context. 

- **Decimal places**: Both the GRIM test and Statcheck respect the number of decimal places in the reported data. Keep this in mind when interpreting the results.

- **Decimal separator**: Both the GRIM test and Statcheck only recognize a dot `.` as a valid decimal separator. A comma `,` is regarded as thousand separator. For example, `'10,159'` is interpreted as 'ten thousand one hundred fifty-nine', not 'ten point one five nine'.

- **Error handling**: The script includes basic error handling for file formats and extraction issues. Make sure to check the console for any error messages if something goes wrong. Some hints are also programmed in the scripts: e.g., when providing an `"r"` test with no `DF`, the script returns the following `Note`: _"Correlation test requires degrees of freedom (df1). None provided."_


# Known Issues
## GRIM-Related Issues
- **Incorrect GRIM applicability detection:**  The AI model frequently misclassifies floating-point means as GRIM-applicable, resulting in false positives. GRIM should only be applied to means derived from discrete integer data (e.g., Likert scales).

- **Segmentation trade-off:**   Articles are processed in segments of 1,000 words with 200-word overlap. While this prevents the context windows from becoming too large, it also increases the chance that relevant values (mean and sample size) appear in separate segments and cannot be matched.



## Statcheck-Related Issues
- **Typesetting issues:** In some journals, mathematical symbols such as `<` are replaced by an image of this symbol, which can’t be converted to plain text. This means that the correct operator cannot be extracted, meaning the script has to fill in an operator itself. Usually, the script fills in the `=` operator, which is likely to be incorrect.
- **Contextual understanding:** Currently, the script only accounts for Huynh-Feldt corrections; other statistical corrections have not yet been implemented. Furthermore, the script attempts to identifiy the test tail (`'one'` or `'two'`) which was used, based on the context. In future versions, the script can be programmed to allow for the detection of additional statistical corrections.


# Code Quality
All code is compliant with the [Ruff linter](https://docs.astral.sh/ruff/).


