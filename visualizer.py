import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import os

# Create an output folder for images
IMAGE_DIR = "report_images"
if not os.path.exists(IMAGE_DIR):
    os.makedirs(IMAGE_DIR)

# Set a professional visual theme
sns.set_theme(style="whitegrid")

def plot_arbitrage_bar_chart(report_data):
    """Draws a horizontal bar chart of the Top 5 Arbitrage opportunities."""
    if not report_data:
        return
        
    # Grab the top 5 highest spread items
    top_5 = report_data[:5]
    
    commodities = [item['commodity'] for item in top_5]
    spreads = [item['spread'] for item in top_5]
    
    plt.figure(figsize=(10, 6))
    bars = sns.barplot(x=spreads, y=commodities, palette="viridis")
    
    plt.title("Top 5 Arbitrage Opportunities (Price Spread ₹)", fontsize=16, pad=15)
    plt.xlabel("Profit Margin (₹ per kg)", fontsize=12)
    plt.ylabel("")
    
    # Add the exact numbers on the bars
    for bar in bars.containers:
        bars.bar_label(bar, fmt='₹%.2f', padding=5)
        
    plt.tight_layout()
    plt.savefig(os.path.join(IMAGE_DIR, "top_arbitrage.png"), dpi=300)
    plt.close() # Close to save memory

def plot_30_day_trend(daily_avg_df, target_crops=["Potato", "Onion", "Tomato"]):
    """Plots a 30-day line graph for the most essential crops."""
    
    # Filter for the last 30 days
    latest_date = daily_avg_df['report_date'].max()
    thirty_days_ago = latest_date - pd.Timedelta(days=30)
    
    mask = (daily_avg_df['report_date'] >= thirty_days_ago) & (daily_avg_df['commodity'].isin(target_crops))
    recent_data = daily_avg_df[mask]
    
    plt.figure(figsize=(12, 6))
    sns.lineplot(data=recent_data, x='report_date', y='price', hue='commodity', linewidth=2.5, marker='o')
    
    plt.title("National Average Price Trend (Last 30 Days)", fontsize=16, pad=15)
    plt.xlabel("Date", fontsize=12)
    plt.ylabel("Average Price (₹/Kg)", fontsize=12)
    plt.xticks(rotation=45)
    
    plt.tight_layout()
    plt.savefig(os.path.join(IMAGE_DIR, "30_day_trend.png"), dpi=300)
    plt.close()
def plot_inflation_variance(national_avg, highest_trend, lowest_trend, highest_state, lowest_state):
    plt.figure(figsize=(10, 6))

    # Convert string dates to datetime objects for smooth plotting
    national_dates = pd.to_datetime(national_avg['report_date'])
    high_dates = pd.to_datetime(highest_trend['report_date'])
    low_dates = pd.to_datetime(lowest_trend['report_date'])

    # Plot the three lines
    plt.plot(national_dates, national_avg['inflation_pct'], 
             label='National Average', color='black', linewidth=3, linestyle='--')
    
    plt.plot(high_dates, highest_trend['inflation_pct'], 
             label=f'Highest Inflation ({highest_state})', color='crimson', linewidth=2)
    
    plt.plot(low_dates, lowest_trend['inflation_pct'], 
             label=f'Lowest Inflation ({lowest_state})', color='gold', linewidth=3)

    # --- THE DYNAMIC Y-AXIS FIX ---
    # Find the absolute max and min across all three lines
    all_values = pd.concat([national_avg['inflation_pct'], 
                            highest_trend['inflation_pct'], 
                            lowest_trend['inflation_pct']])
    
    y_max = all_values.max()
    y_min = all_values.min()
    
    # Add a 10% buffer to the top and bottom so lines don't touch the edge
    buffer = (y_max - y_min) * 0.1 
    if buffer == 0: buffer = 1 # Fallback if inflation is exactly 0 everywhere
    
    plt.ylim(y_min - buffer, y_max + buffer)
    # ------------------------------

    # Formatting to make it look professional
    plt.title('30-Day Agricultural Inflation Variance', fontsize=14, fontweight='bold')
    plt.xlabel('Date')
    plt.ylabel('Cumulative Inflation (%)')
    plt.axhline(0, color='grey', linewidth=1, linestyle=':') # Adds a baseline at 0%
    
    # Format X-axis to show dates nicely (e.g., "Apr 15")
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
    plt.xticks(rotation=45)
    
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    # Save over the old image so the YAML and README don't need to change
    plt.savefig('report_images/30_day_trend.png', dpi=300)
    plt.close()

def plot_arbitrage_matrix(matrix_data):
    plt.figure(figsize=(10, 6))

    # 1. The Density Overlay (The "Aura" of normal market behavior)
    sns.kdeplot(
        data=matrix_data, x='spread_pct', y='volatility_pct',
        fill=True, cmap="Blues", thresh=0.05, alpha=0.5
    )

    # 2. The Scatter Plot (The actual commodities)
    sns.scatterplot(
        data=matrix_data, x='spread_pct', y='volatility_pct',
        color='black', s=60, edgecolor='white', alpha=0.8
    )

    # 3. Auto-Labeling the Outliers (Top 3 spread, Top 3 volatility)
    top_spread = matrix_data.nlargest(3, 'spread_pct')
    top_vol = matrix_data.nlargest(3, 'volatility_pct')
    outliers = pd.concat([top_spread, top_vol]).drop_duplicates()

    for _, row in outliers.iterrows():
        plt.annotate(
            row['commodity'],
            (row['spread_pct'], row['volatility_pct']),
            xytext=(6, 6), textcoords='offset points',
            fontsize=10, fontweight='bold', color='darkred'
        )

    # 4. Formatting and Quadrant Lines
    plt.title('10-Day Market Risk Matrix (Arbitrage vs. Volatility)', fontsize=14, fontweight='bold')
    plt.xlabel('Inter-State Arbitrage Spread (%)')
    plt.ylabel('Price Volatility (Day-to-Day %)')

    # Add crosshairs based on the median data
    plt.axvline(matrix_data['spread_pct'].median(), color='grey', linestyle='--', alpha=0.6)
    plt.axhline(matrix_data['volatility_pct'].median(), color='grey', linestyle='--', alpha=0.6)

    plt.grid(True, alpha=0.2)
    plt.tight_layout()

    # Save exactly over the old image to avoid changing GitHub Actions YAML
    plt.savefig('report_images/top_arbitrage.png', dpi=300)
    plt.close()