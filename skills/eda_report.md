# Skill: EDA Report

## When to use
User wants an exploratory data analysis report (HTML + plots + summary statistics) on a dataset — not a definition of what EDA means.

## Steps
1. Load the dataset using pandas (read_csv, read_excel, etc.)
2. Install required libs: `pip install pandas matplotlib seaborn`
3. Write the EDA script inside the workspace folder:
   ```python
   import pandas as pd
   import matplotlib
   matplotlib.use('Agg')
   import matplotlib.pyplot as plt
   import seaborn as sns

   df = pd.read_csv("<dataset_path>")

   # summary stats
   summary = df.describe(include='all').to_html()

   # plots
   for col in df.select_dtypes(include='number').columns:
       plt.figure()
       sns.histplot(df[col], kde=True)
       plt.title(f'Distribution of {col}')
       plt.savefig("<workspace>/{col}_distribution.png")
       plt.close()

   # correlation heatmap
   plt.figure(figsize=(10, 8))
   sns.heatmap(df.select_dtypes(include='number').corr(), annot=True, fmt='.2f')
   plt.title('Correlation Heatmap')
   plt.savefig("<workspace>/correlation_heatmap.png")
   plt.close()

   # write HTML report
   with open("<workspace>/eda_report.html", "w") as f:
       f.write(f"<h1>EDA Report</h1>{summary}")
       for col in df.select_dtypes(include='number').columns:
           f.write(f'<h2>{col}</h2><img src="{col}_distribution.png">')
       f.write('<h2>Correlation</h2><img src="correlation_heatmap.png">')
   ```
4. Run the script using absolute path
5. Confirm the HTML and PNG files were created

## Rules
- Always use matplotlib.use('Agg') to avoid display errors on headless systems
- Never use sweetviz, pandas_profiling or ydata_profiling
- Save all output files inside the workspace folder using absolute paths
- Use the actual dataset file path provided by the user
