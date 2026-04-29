import sqlite3
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression

#CONFIGURATION
DB_NAME = "agri_warehouse.db"

def get_data():
    """
    Fetches the last 90 days of data and fixes the 'Zero' problem using Forward Fill.
    """
    conn = sqlite3.connect(DB_NAME)
    
    # Only load the last 90 days into RAM
    query = """
        SELECT * FROM daily_prices 
        WHERE report_date >= date('now', '-90 days') 
        ORDER BY report_date ASC
    """
    df = pd.read_sql(query, conn)
    conn.close()

    # Convert 0 to NaN 
    df['price'] = df['price'].replace(0, np.nan)

    # Fix Missing Data (Imputation)
    df['price'] = df.groupby(['state_name', 'commodity'])['price'].ffill().bfill()

    # Drop rows that are STILL empty
    df = df.dropna(subset=['price'])
    
    return df

def get_daily_report_data(df, date=None):
    """
    Analyzes the data and returns a structured list of Highs, Lows, 
    Differences, and Averages for every commodity.
    """
    if date is None:
        date = df['report_date'].max()

    day_df = df[df['report_date'] == date]
    
    if day_df.empty:
        return []

    report_data = []
    
    for commodity in day_df['commodity'].unique():
        crop_data = day_df[day_df['commodity'] == commodity]
        
        if len(crop_data) < 2:
            continue

        min_row = crop_data.loc[crop_data['price'].idxmin()]
        max_row = crop_data.loc[crop_data['price'].idxmax()]
        avg_price = crop_data['price'].mean()
        
        spread = max_row['price'] - min_row['price']
        
        report_data.append({
            'commodity': commodity,
            'max_price': max_row['price'],
            'max_state': max_row['state_name'],
            'min_price': min_row['price'],
            'min_state': min_row['state_name'],
            'spread': spread,
            'avg_price': avg_price
        })

    # Sort by spread and return the list
    report_data = sorted(report_data, key=lambda x: x['spread'], reverse=True)
    return report_data

def get_trend_report_data(df, date=None):
    """
    Calculates 30-day inflation, 7-day inflation, backtests 'Today's' predicted price,
    and uses Linear Regression to forecast tomorrow's price change.
    
    Returns: 
        trend_data (list of dictionaries)
        daily_avg (dataframe needed for the visualizer line charts)
    """
    if date is None:
        date = df['report_date'].max()
        
    daily_avg = df.groupby(['report_date', 'commodity'])['price'].mean().reset_index()
    daily_avg['report_date'] = pd.to_datetime(daily_avg['report_date'])
    
    target_date = pd.to_datetime(date)
    week_ago = target_date - pd.Timedelta(days=7)
    month_ago = target_date - pd.Timedelta(days=30)
    
    trend_data = []
    
    for commodity in daily_avg['commodity'].unique():
        series = daily_avg[daily_avg['commodity'] == commodity].sort_values('report_date')
        today_data = series[series['report_date'] == target_date]
        
        if today_data.empty:
            continue
        today_price = today_data.iloc[0]['price']
        
        week_series = series[series['report_date'] <= week_ago]
        week_price = week_series.iloc[-1]['price'] if not week_series.empty else series.iloc[0]['price']
            
        month_series = series[series['report_date'] <= month_ago]
        month_price = month_series.iloc[-1]['price'] if not month_series.empty else series.iloc[0]['price']
        
        week_inflation = ((today_price - week_price) / week_price) * 100 if week_price > 0 else 0
        month_inflation = ((today_price - month_price) / month_price) * 100 if month_price > 0 else 0
        
        momentum_days = 10 
    
        historical_series = series[series['report_date'] < target_date].tail(momentum_days)
        
        if len(historical_series) >= 5:
            X_hist = np.arange(len(historical_series)).reshape(-1, 1)
            y_hist = historical_series['price'].values
            
            model_today = LinearRegression()
            model_today.fit(X_hist, y_hist)
            today_predicted = model_today.predict([[len(historical_series)]])[0]
        else:
            today_predicted = today_price 
            
        #PREDICT TOMORROW
        momentum_series = series.tail(momentum_days)
        
        if len(momentum_series) >= 5:
            X_all = np.arange(len(momentum_series)).reshape(-1, 1)
            y_all = momentum_series['price'].values
            
            model_tomorrow = LinearRegression()
            model_tomorrow.fit(X_all, y_all)
            tomorrow_price = model_tomorrow.predict([[len(X_all)]])[0]
            forecast_change = tomorrow_price - today_price
        else:
            forecast_change = 0.0
            
        trend_data.append({
            'commodity': commodity,
            'month_inf': month_inflation,
            'week_inf': week_inflation,
            'today_pred': today_predicted,
            'today_actual': today_price,
            'forecast': forecast_change
        })
        
    return trend_data, daily_avg

def calculate_inflation_trends(df):
    #  Get the average price per state, per day (FIXED: 'state_name')
    state_daily = df.groupby(['report_date', 'state_name'])['price'].mean().reset_index()
    state_daily = state_daily.sort_values(['state_name', 'report_date'])

    # Calculate Cumulative Inflation 
    state_daily['base_price'] = state_daily.groupby('state_name')['price'].transform('first')
    state_daily['inflation_pct'] = ((state_daily['price'] - state_daily['base_price']) / state_daily['base_price']) * 100

    #Calculate the National Average Inflation per day
    national_avg = state_daily.groupby('report_date')['inflation_pct'].mean().reset_index()

    # Identify the Highest and Lowest states based on the FINAL day
    last_day = state_daily['report_date'].max()
    final_day_data = state_daily[state_daily['report_date'] == last_day]
    
    # (FIXED: Extracting from 'state_name')
    highest_state = final_day_data.loc[final_day_data['inflation_pct'].idxmax()]['state_name']
    lowest_state = final_day_data.loc[final_day_data['inflation_pct'].idxmin()]['state_name']

    # 5. Extract the 30-day data just for those two specific states
    highest_trend = state_daily[state_daily['state_name'] == highest_state]
    lowest_trend = state_daily[state_daily['state_name'] == lowest_state]

    return national_avg, highest_trend, lowest_trend, highest_state, lowest_state
def calculate_arbitrage_matrix(df):
    #Filter to the last 10 days
    df['report_date'] = pd.to_datetime(df['report_date'])
    last_10_days = df['report_date'].max() - pd.Timedelta(days=10)
    df_10 = df[df['report_date'] >= last_10_days]

    # Calculate X-Axis (Arbitrage Spread %)
    # Find max and min prices across states for each commodity, every day
    daily_spread = df_10.groupby(['report_date', 'commodity'])['price'].agg(['max', 'min']).reset_index()
    daily_spread['spread_pct'] = ((daily_spread['max'] - daily_spread['min']) / daily_spread['min']) * 100
    
    # Average that spread over the 10 days
    commodity_spread = daily_spread.groupby('commodity')['spread_pct'].mean().reset_index()

    # Calculate Y-Axis (Volatility %)
    # Get national daily average, then find the Coefficient of Variation (Std / Mean)
    daily_avg = df_10.groupby(['report_date', 'commodity'])['price'].mean().reset_index()
    commodity_volatility = daily_avg.groupby('commodity')['price'].agg(['std', 'mean']).reset_index()
    commodity_volatility['volatility_pct'] = (commodity_volatility['std'] / commodity_volatility['mean']) * 100

    # Merge into our final Matrix DataFrame
    matrix_data = pd.merge(commodity_spread, commodity_volatility[['commodity', 'volatility_pct']], on='commodity')
    matrix_data = matrix_data.fillna(0) # Catch any math errors (like dividing by zero)

    return matrix_data
#TEST BLOCK
if __name__ == "__main__":
    print(" Initializing Analyzer Engine...")
    
    clean_df = get_data()
    
    if not clean_df.empty:
        print(f"Data Loaded. Total Valid Rows: {len(clean_df)}")
        
        r_data = get_daily_report_data(clean_df)
        t_data, d_avg = get_trend_report_data(clean_df)
        
        print(f" Processed {len(r_data)} commodities successfully.")
        print(" Ready to pass data to visualizer.py!")
    else:
        print(" Database is empty! Run the scraper first.")