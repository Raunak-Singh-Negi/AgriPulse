import os
import sqlite3
import pandas as pd
from bs4 import BeautifulSoup
import glob
import re
from datetime import datetime, timedelta
from io import StringIO 

#RAW_DATA_DIR = r"C:\Users\raunak\Desktop\AgriPulse\raw_data"
RAW_DATA_DIR = os.path.join(os.path.dirname(__file__), "raw_data")
DB_NAME = "agri_warehouse.db"

def get_db_connection():
    """Connects to the local SQLite Data Warehouse and creates table if missing."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Create the Master Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_prices (
            report_date TEXT,
            state_name TEXT,
            commodity TEXT,
            price REAL,
            UNIQUE(report_date, state_name, commodity) ON CONFLICT REPLACE
        )
    ''')
    conn.commit()
    return conn

def trim_old_data(days_to_keep=30):
    """Deletes records older than 'days_to_keep'."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).strftime('%Y-%m-%d')
    print(f" Maintenance: Deleting records older than {cutoff_date}...")
    
    cursor.execute("DELETE FROM daily_prices WHERE report_date < ?", (cutoff_date,))
    deleted_count = cursor.rowcount
    
    conn.commit()
    conn.close()
    print(f" Cleanup Complete. Removed {deleted_count} old rows.")

def parse_html_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    soup = BeautifulSoup(content, "html.parser")
    
    # 1. EXTRACT DATE
    date_str = None
    all_text = soup.get_text()
    match = re.search(r"Date\s+(\d{2}/\d{2}/\d{4})", all_text)
    
    if match:
        raw_date = match.group(1)
        date_obj = datetime.strptime(raw_date, "%d/%m/%Y")
        sql_date = date_obj.strftime("%Y-%m-%d")
    else:
        print(f" Warning: No date found in {os.path.basename(file_path)}. Skipping.")
        return None

    # 2. EXTRACT TABLE
    table = soup.find("table", {"id": "gv0"})
    if not table:
        return None
        
    # Use StringIO to avoid Pandas Warning
    html_io = StringIO(str(table))
    df = pd.read_html(html_io)[0]
    
    # 3. CLEANING
    df = df[~df.iloc[:, 0].astype(str).str.contains("Average|Maximum|Minimum|Modal", case=False, na=False)]
    df.rename(columns={df.columns[0]: 'state_name'}, inplace=True)
    
    # Handle bad data
    df = df.replace(["NR", "-", "&nbsp;", "nan"], 0)
    df = df.fillna(0)
    
    # 4. UNPIVOT (MELT)
    melted_df = df.melt(id_vars=['state_name'], var_name='commodity', value_name='price')
    melted_df['report_date'] = sql_date
    
    # 5. FORCE NUMERIC (Critical Safety Step)
    melted_df['price'] = pd.to_numeric(melted_df['price'], errors='coerce').fillna(0)
    
    return melted_df

def etl_process():
    print(f" Starting ETL Process...")
    conn = get_db_connection()
    
    files = glob.glob(os.path.join(RAW_DATA_DIR, "*.xls"))
    print(f" Found {len(files)} files in raw_data.")
    
    total_rows = 0
    
    for file_path in files:
        try:
            filename = os.path.basename(file_path)
            clean_df = parse_html_file(file_path)
            
            if clean_df is not None and not clean_df.empty:
                data_to_insert = clean_df.to_dict('records')
                
                cursor = conn.cursor()
                cursor.executemany('''
                    INSERT INTO daily_prices (report_date, state_name, commodity, price)
                    VALUES (:report_date, :state_name, :commodity, :price)
                    ON CONFLICT(report_date, state_name, commodity) DO UPDATE SET price=excluded.price
                ''', data_to_insert)
                
                total_rows += len(clean_df)
                
        except Exception as e:
            print(f" Error processing {filename}: {e}")
            
    conn.commit()
    conn.close()
    
    print(f"\n ETL Complete. Warehouse updated with {total_rows} records.")
    
    # Run the cleanup logic immediately after loading
    trim_old_data(days_to_keep=30)

if __name__ == "__main__":
    etl_process()