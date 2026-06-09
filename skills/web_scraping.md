# Skill: Web Scraping

## When to use
User wants to scrape or extract structured data from a website or URL.

## Steps
1. Install required libs: `pip install requests beautifulsoup4 pandas`
2. Write the scraping script inside the workspace folder:
   ```python
   import requests
   from bs4 import BeautifulSoup
   import pandas as pd

   url = "<target_url>"
   response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
   soup = BeautifulSoup(response.text, "html.parser")

   # extract data and save to CSV
   data = []
   # ... parsing logic ...
   df = pd.DataFrame(data)
   df.to_csv("<workspace>/scraped_data.csv", index=False)
   ```
3. Run the script and confirm CSV was created

## Rules
- Always set a User-Agent header to avoid being blocked
- Save output as CSV inside the workspace folder
- Handle request errors with try/except
