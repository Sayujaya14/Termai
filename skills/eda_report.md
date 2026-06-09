# Skill: EDA Report

## When to use
User wants an exploratory data analysis report (HTML + plots + summary statistics) on a dataset — not a definition of what EDA means.

## Steps
1. Load the dataset using pandas (read_csv, read_excel, etc.)
2. Install required libs: `pip install pandas matplotlib seaborn jinja2`
3. Write a short script in the workspace that calls **`build_eda_report()`** from `report_html.py`.
   Do **not** hand-build HTML strings — the template handles layout, CSS, and embedded charts.

   ```python
   import os
   import sys

   import pandas as pd

   WORKSPACE = "<workspace>"  # absolute task workspace path
   DATASET = "<dataset_path>"   # absolute path to CSV/Excel file

   _TERMAI_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
   sys.path.insert(0, _TERMAI_ROOT)
   from report_html import build_eda_report

   df = pd.read_csv(DATASET)
   report_path = os.path.join(WORKSPACE, "eda_report.html")
   build_eda_report(
       df,
       report_path,
       dataset_name=os.path.basename(DATASET),
       title="Exploratory Data Analysis",
   )
   print(f"Report written: {report_path}")
   ```

4. Run the script with absolute path
5. Confirm `eda_report.html` opens standalone with styled layout and all charts visible

## What the report includes
- Header with dataset name, row/column counts, timestamp
- Key findings (rule-based insights)
- Overview statistics table (styled)
- Missing-value bars
- Numeric distribution histograms (embedded base64)
- Categorical value-count charts (top 10 per column)
- Pie charts for low-cardinality categories (2–8 unique values)
- Scatter plots for top correlated numeric column pairs
- Box plot: first numeric column vs first low-cardinality category
- Correlation heatmap (when 2+ numeric columns)
- Optional PNG copies saved in workspace for zip download

## Rules
- Always use `build_eda_report()` — never write raw `<h1>` / `<img src="file.png">` HTML
- Never use sweetviz, pandas_profiling or ydata_profiling
- Use the actual dataset file path provided by the user
- Save the script inside the workspace folder
