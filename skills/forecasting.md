# Skill: Forecasting Report

## When to use
User wants a time-series forecast, prediction, trend projection, or future values from historical dated data.

## Steps
1. Load the dataset using pandas
2. Install required libs: `pip install pandas matplotlib statsmodels jinja2`
3. Write a short script in the workspace that calls **`build_forecast_report()`**:

   ```python
   import os
   import sys

   import pandas as pd

   WORKSPACE = "<workspace>"
   DATASET = "<dataset_path>"

   _TERMAI_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
   sys.path.insert(0, _TERMAI_ROOT)
   from report_html import build_forecast_report

   df = pd.read_csv(DATASET)
   report_path = os.path.join(WORKSPACE, "forecast_report.html")
   build_forecast_report(
       df,
       report_path,
       dataset_name=os.path.basename(DATASET),
       date_col=None,      # auto-detect, or set e.g. "date"
       value_col=None,     # auto-detect, or set e.g. "sales"
       horizon=30,
   )
   print(f"Report: {report_path}")
   print(f"CSV: {os.path.join(WORKSPACE, 'forecast.csv')}")
   ```

4. Run the script with absolute paths
5. Confirm `forecast_report.html` and `forecast.csv` exist in the workspace

## What the report includes
- Auto-detected date + target columns (or use explicit `date_col` / `value_col`)
- ARIMA order search with holdout validation (MAE, RMSE, MAPE)
- Forecast chart: history + holdout + future with 95% confidence band
- Holdout actual vs predicted chart
- Residuals plot
- `forecast.csv` with date, forecast, lower, upper bounds
- Self-contained HTML (embedded base64 charts)

## Rules
- Always use `build_forecast_report()` — do not hand-build HTML or use relative `<img src="...">`
- Requires at least **20** dated observations after cleaning
- Data must be sorted by time; duplicate timestamps keep the last value
- Use `matplotlib.use('Agg')` only if writing custom plots (builder handles charts)
- Never open browser or GUI windows
- If date/target columns are ambiguous, pass `date_col` and `value_col` explicitly

## Do not use when
- Dataset has no date/time column and no parseable dates
- Fewer than 20 rows after dropping nulls
- User only wants EDA (use `build_eda_report()` instead)
