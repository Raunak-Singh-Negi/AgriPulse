import time
import os
import random 
import pytesseract
import shutil
import sys
import platform
from PIL import Image
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime, timedelta

# --- YOUR VITAL GOVERNMENT URLS ---
MENU_URL = "https://fcainfoweb.nic.in/reports/report_menu_web.aspx"
DIRECT_URL = "https://fcainfoweb.nic.in/reports/Report_daily1_web_Statewise.aspx"

# --- 1. CROSS-PLATFORM TESSERACT CONFIG ---
if platform.system() == "Windows":
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# --- 2. DYNAMIC RELATIVE PATHS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "raw_data")
IMAGE_DIR = os.path.join(BASE_DIR, "z_images")

# Reset Image Directory
if os.path.exists(IMAGE_DIR):
    shutil.rmtree(IMAGE_DIR) 
os.makedirs(IMAGE_DIR) 

if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

# Define static file paths
CAPTCHA_PATH = os.path.join(IMAGE_DIR, "temp_captcha.png")
CRASH_PATH = os.path.join(IMAGE_DIR, "crash.png")

def setup_driver():
    options = webdriver.ChromeOptions()
    
    # --- HEADLESS MODE ---
    options.add_argument("--headless=new") 
    options.add_argument("--window-size=1920,1080")

    # --- humanify ---
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # --- PERFORMANCE & STABILITY ---
    options.add_argument("--disable-cache")
    options.add_argument("--disk-cache-size=0")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    
    prefs = {
        "download.default_directory": DOWNLOAD_DIR,
        "download.prompt_for_download": False,
        "directory_upgrade": True
    }
    options.add_experimental_option("prefs", prefs)
    
    driver = webdriver.Chrome(options=options)
    driver.set_window_size(1920, 1080)
    return driver

def solve_captcha(driver):
    try:
        # 1. Find the element
        captcha_img = driver.find_element(By.ID, "ctl00_MainContent_captchalogin")
        
        # 2. Scroll it into view (Crucial for Headless!)
        driver.execute_script("arguments[0].scrollIntoView();", captcha_img)
        time.sleep(0.5) 
        
        # 3. Take Screenshot
        captcha_img.screenshot(CAPTCHA_PATH)
        
        # 4. Read Text
        custom_config = r'--psm 6 -c tessedit_char_whitelist=abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        captcha_text = pytesseract.image_to_string(Image.open(CAPTCHA_PATH), config=custom_config)
        
        clean_text = captcha_text.strip()
        print(f"   [OCR Read]: '{clean_text}'") 
        return clean_text
        
    except Exception as e:
        print(f"   [OCR Error]: {e}")
        return ""

def main():
    try:
        driver = setup_driver()
        wait = WebDriverWait(driver, 15)
        print("Opened Browser as Headless")
    except Exception as e:
        print(f" Failed to start browser. Did you kill the old Chrome tasks? Error: {e}")
        return

    try:
        print(" Connecting to Menu...")
        driver.get(MENU_URL)

        # Standard navigation
        wait.until(EC.element_to_be_clickable((By.ID, "ctl00_MainContent_Rbl_Rpt_type_0"))).click()
        wait.until(EC.presence_of_element_located((By.ID, "ctl00_MainContent_Ddl_Rpt_Option0")))

        Select(driver.find_element(By.ID, "ctl00_MainContent_Ddl_Rpt_Option0")).select_by_visible_text("Daily Prices")
        wait.until(EC.presence_of_element_located((By.ID, "ctl00_MainContent_Txt_FrmDate")))

        yesterday_obj = datetime.now() - timedelta(days=1)
        yesterday_str = yesterday_obj.strftime("%d/%m/%Y") 
        file_date_str = yesterday_obj.strftime("%d-%m-%Y") 
        
        driver.find_element(By.ID, "ctl00_MainContent_Txt_FrmDate").send_keys(yesterday_str)

        # --- CAPTCHA LOOP ---
        max_retries = 5
        session_established = False
        
        for attempt in range(max_retries):
            print(f"\n Attempted {attempt + 1}/{max_retries}...")
            
            captcha_text = solve_captcha(driver)
            
            if len(captcha_text) == 6:
                captcha_box = driver.find_element(By.ID, "ctl00_MainContent_Captcha")
                captcha_box.clear()
                captcha_box.send_keys(captcha_text)
                
                driver.find_element(By.ID, "ctl00_MainContent_btn_getdata1").click()
                time.sleep(3) 

                # Check for errors
                errors = driver.find_elements(By.ID, "ctl00_MainContent_lblmsg")
                if len(errors) > 0 and "not correct" in errors[0].text:
                    print("  Website: Incorrect Captcha")
                    continue 
                else:
                    print("  Captcha Accepted! Session Valid.")
                    session_established = True
                    break
            else:
                print(" OCR Read Invalid Length (Not 6 chars). Retrying...")
                driver.refresh()
                time.sleep(3)
                try:
                    wait.until(EC.presence_of_element_located((By.ID, "ctl00_MainContent_Txt_FrmDate")))
                    driver.find_element(By.ID, "ctl00_MainContent_Txt_FrmDate").clear()
                    driver.find_element(By.ID, "ctl00_MainContent_Txt_FrmDate").send_keys(yesterday_str)
                except:
                    pass

        # --- STOP IF FAILED ---
        if not session_established:
            print("\n CRITICAL: Failed to solve Captcha 5 times. Aborting to prevent crash.")
            driver.quit()
            return

        # --- DOWNLOAD (The Teleport) ---
        print(" Teleporting to Download Page...")
        time.sleep(5) 
        driver.get(DIRECT_URL)
        
        print("Clicking Save button...")
        save_btn = wait.until(EC.element_to_be_clickable((By.ID, "btnsave")))
        save_btn.click()
        
        print(" Waiting for file...")
        time.sleep(8) 
        
        # --- RENAME LOGIC ---
        files = os.listdir(DOWNLOAD_DIR)
        paths = [os.path.join(DOWNLOAD_DIR, basename) for basename in files if basename.endswith(".xls")]
        
        if paths:
            newest_file_path = max(paths, key=os.path.getctime)
            new_filename = f"Prices_{file_date_str}.xls"
            new_file_path = os.path.join(DOWNLOAD_DIR, new_filename)
            
            if os.path.exists(new_file_path):
                os.remove(new_file_path)
                
            os.rename(newest_file_path, new_file_path)
            print(f"\nSUCCESS! Saved: {new_filename}")
        else:
            print("\n Error: Download button clicked, but no file found in folder.")

    except Exception as e:
        print(f"\n CRASH : {e}")
        driver.save_screenshot(CRASH_PATH)
        print(f"   Screenshot saved to {CRASH_PATH}")
    
    finally:
        driver.quit() 
        print(" Driver Closed.")

if __name__ == "__main__":
    main()