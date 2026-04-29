import analyzer
import visualizer
from datetime import datetime

def generate_markdown_tables(report_data, trend_data):
    """Converts the raw data into GitHub Markdown tables with S.No."""
    
    #Create a lookup dictionary. 
    trend_dict = {item['commodity']: item for item in trend_data}
    report_dict = {item['commodity']: item for item in report_data}
    
    # Alphabetical list of all commodities. 
    all_commodities = sorted(list(report_dict.keys()))

    #TABLE 1: HIGH / LOW / TODAY PREDICTED  / AVERAGE 
    table1 = "| S.No | Commodity | Highest Price | Lowest Price | Today (Predicted) | Average |\n"
    table1 += "|---|---|---|---|---|---|\n"
    
    #TABLE 2: TRENDS / SPREAD / FORECAST
    table2 = "| S.No | Commodity | 1-Month Trend | 1-Week Trend | Price Difference | Tomorrow (Forecast) |\n"
    table2 += "|---|---|---|---|---|---|\n"
    
    #Loop through them alphabetically and assign a Serial Number (index)
    for index, commodity in enumerate(all_commodities, start=1):
        
        r_data = report_dict.get(commodity)
        t_data = trend_dict.get(commodity)
        
        if not r_data or not t_data:
            continue
            
        # Format Table 1 Strings
        high_str = f"₹{r_data['max_price']:.2f} ({r_data['max_state'][:10]})" 
        low_str = f"₹{r_data['min_price']:.2f} ({r_data['min_state'][:10]})"
        today_pred_str = f"**₹{t_data['today_pred']:.2f}**" 
        avg_str = f"₹{r_data['avg_price']:.2f}"
        
        # Format Table 2 Strings
        m_inf = f"+{t_data['month_inf']:.2f}%" if t_data['month_inf'] > 0 else f"{t_data['month_inf']:.2f}%"
        w_inf = f"+{t_data['week_inf']:.2f}%" if t_data['week_inf'] > 0 else f"{t_data['week_inf']:.2f}%"
        spread_str = f"₹{r_data['spread']:.2f}"
        f_cast = f"+₹{t_data['forecast']:.2f}" if t_data['forecast'] > 0 else f"-₹{abs(t_data['forecast']):.2f}"
        
        # Add the rows to the tables
        table1 += f"| {index} | **{commodity}** | {high_str} | {low_str} | {today_pred_str} | {avg_str} |\n"
        table2 += f"| {index} | **{commodity}** | {m_inf} | {w_inf} | {spread_str} | {f_cast} |\n"

    return table1, table2
#def build_readme():
 #   print(" AgriPulse: Fetching data from Warehouse...")
  #  df = analyzer.get_data()
    
    # ADD THIS TEMPORARY LINE:
   # print("MY COLUMNS ARE:", df.columns)"""
def build_readme():
    print(" AgriPulse: Fetching data from Warehouse...")
    df = analyzer.get_data()
    
    if df.empty:
        print(" Database empty. Aborting.")
        return
        
    print(" Calculating ...")
    report_data = analyzer.get_daily_report_data(df)
    trend_data, daily_avg_df = analyzer.get_trend_report_data(df)
    
    # Get the inflation data from the analyzer
    national_avg, high_trend, low_trend, high_state, low_state = analyzer.calculate_inflation_trends(df)
    
    # Calculate Topline National Inflation Metrics
    # Month is the final cumulative number. Week is last 7 days. Today is last 24 hours.
    nat_month_inf = national_avg['inflation_pct'].iloc[-1]
    nat_week_inf = national_avg['inflation_pct'].iloc[-1] - national_avg['inflation_pct'].iloc[-8] if len(national_avg) >= 8 else 0
    nat_daily_inf = national_avg['inflation_pct'].iloc[-1] - national_avg['inflation_pct'].iloc[-2] if len(national_avg) >= 2 else 0

    def fmt_inf(val):
        return f"+{val:.2f}%" if val > 0 else f"{val:.2f}%"

    topline_str = f"**National Average Inflation:** 30-Day: {fmt_inf(nat_month_inf)} | 7-Day: {fmt_inf(nat_week_inf)} | 24-Hour: {fmt_inf(nat_daily_inf)}"

    print(" Drawing Graphs...")
    matrix_data = analyzer.calculate_arbitrage_matrix(df)
    visualizer.plot_arbitrage_matrix(matrix_data)
    visualizer.plot_inflation_variance(national_avg, high_trend, low_trend, high_state, low_state)
    
    print(" Writing Markdown Tables...")
    table1, table2 = generate_markdown_tables(report_data, trend_data)
    
    data_date = df['report_date'].max()
    formatted_date = data_date.strftime("%B %d, %Y")
    
    #Markdown Template
    readme_content = f"""#  Agri-Price daily smart Dashboard
> **Status:** Operational | **Data Snapshot:** {formatted_date}

This automated engine tracks wholesale prices across India and uses Machine Learning to forecast short-term price momentum.

> {topline_str}

##  Price Momentum & Forecasts
{table2}

##  Visual Trends

### 30-Day Inflation Variance (National vs Extremes)
*The graph below represents the average cumulative inflation across India, compared against the specific State or Union Territory experiencing the highest and lowest price variations over the last 30 days.*

![Inflation Variance](report_images/30_day_trend.png)

### 10-Day Market Risk Matrix (Arbitrage vs. Volatility)
**How to read this matrix:**
* **Bottom-Right Quadrant (Golden Zone):** High profit margins, stable prices.
* **Top-Right Quadrant (High Risk):** Huge profit margins, but prices change violently.
* **Top-Left Quadrant (Chaos Zone):** Low profit margins and highly unstable prices.
* **Bottom-Left Quadrant (Safe Zone):** Low profit margins, but very predictable staple prices.

![Market Risk Matrix](report_images/top_arbitrage.png)

<details>
<summary><b>  Click to View: Daily State-by-State Highs & Lows</b></summary>

{table1}

</details>

---
*Generated automatically by AgriPulse Engine on GitHub Actions.*
"""
    
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(readme_content)
        
    print(f" Success! Dashboard updated for {formatted_date}.")

if __name__ == "__main__":
    build_readme()