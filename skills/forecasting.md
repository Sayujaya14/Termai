# Skill: Forecasting Report

## When to use
User wants a time-series forecast, prediction, or future-values report from historical data.

## Steps
1. Load the dataset using pandas
2. Install required libs: `pip install pandas matplotlib statsmodels scikit-learn`
3. Write the forecasting script inside the workspace folder:
   ```python
   import pandas as pd
   import matplotlib
   matplotlib.use('Agg')
   import matplotlib.pyplot as plt
   from statsmodels.tsa.arima.model import ARIMA

   df = pd.read_csv("<dataset_path>")
   # fit ARIMA model and forecast
   model = ARIMA(df['<target_col>'], order=(5,1,0))
   result = model.fit()
   forecast = result.forecast(steps=30)

   # save plot
   plt.figure()
   plt.plot(df['<target_col>'], label='Historical')
   plt.plot(forecast, label='Forecast')
   plt.legend()
   plt.savefig("<workspace>/forecast.png")
   plt.close()
   ```
4. Save forecast CSV and HTML summary inside workspace
5. Run the script and confirm output files

## Rules
- Always use matplotlib.use('Agg') to avoid display errors on headless systems
- Save all plots as PNG inside the workspace folder
- Never open browser or GUI windows
