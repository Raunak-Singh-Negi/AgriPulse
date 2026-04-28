import pandas as pd
import matplotlib.pyplot as plt
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