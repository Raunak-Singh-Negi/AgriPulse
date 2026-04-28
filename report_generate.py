import analyzer
import visualizer
from datetime import datetime

def generate_markdown_tables(report_data, trend_data):
    """Converts the raw data into GitHub-friendly Markdown tables with swapped columns and S.No."""
    
    # 1. Create a lookup dictionary. This allows us to easily grab "Spread" from report_data
    # and put it next to "1-Month Trend" from trend_data.
    trend_dict = {item['commodity']: item for item in trend_data}
    report_dict = {item['commodity']: item for item in report_data}
    
    # 2. Get an Alphabetical list of all commodities. 
    # This ensures "Atta (Wheat)" is always S.No 1 in BOTH tables.
    all_commodities = sorted(list(report_dict.keys()))

    # --- TABLE 1: HIGH / LOW / TODAY PREDICTED (Swapped) / AVERAGE ---
    table1 = "| S.No | Commodity | Highest Price | Lowest Price | Today (Predicted) | Average |\n"
    table1 += "|---|---|---|---|---|---|\n"
    
    # --- TABLE 2: TRENDS / SPREAD (Swapped) / FORECAST ---
    table2 = "| S.No | Commodity | 1-Month Trend | 1-Week Trend | Price Difference | Tomorrow (Forecast) |\n"
    table2 += "|---|---|---|---|---|---|\n"
    
    # 3. Loop through them alphabetically and assign a Serial Number (index)
    for index, commodity in enumerate(all_commodities, start=1):
        
        # Grab the math for this specific commodity from both lists
        r_data = report_dict.get(commodity)
        t_data = trend_dict.get(commodity)
        
        # Skip if a commodity happens to be missing from one of the datasets
        if not r_data or not t_data:
            continue
            
        # Format Table 1 Strings
        high_str = f"₹{r_data['max_price']:.2f} ({r_data['max_state'][:10]})" # Shortened state name to 10 chars to save space
        low_str = f"₹{r_data['min_price']:.2f} ({r_data['min_state'][:10]})"
        today_pred_str = f"**₹{t_data['today_pred']:.2f}**" # Made bold so it stands out
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

def build_readme():
    print("Fetching data from Warehouse...")
    df = analyzer.get_data()
    
    if df.empty:
        print("Database empty. Aborting.")
        return
        
    print("Calculating Intelligence...")
    report_data = analyzer.get_daily_report_data(df)
    trend_data, daily_avg_df = analyzer.get_trend_report_data(df)
    
    print("Drawing Graphs...")
    visualizer.plot_arbitrage_bar_chart(report_data)
    visualizer.plot_30_day_trend(daily_avg_df)
    
    print("Writing Markdown Tables...")
    table1, table2 = generate_markdown_tables(report_data, trend_data)
    
    # Assembly: The Final README
    today_str = datetime.now().strftime("%B %d, %Y")
    
    readme_content = f"""#  Agri-Price Intelligence Dashboard
**Last Updated:** {today_str}

This project tracks wholesale prices of essential commodities across India, using Machine Learning to forecast short-term price momentum.


{table2}

<details>
<summary><b> Click to Expand: Daily State-by-State Highs & Lows</b></summary>

{table1}

</details>
"""
    
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(readme_content)
        
    print(" Success! README.md and graphs generated.")

if __name__ == "__main__":
    build_readme()