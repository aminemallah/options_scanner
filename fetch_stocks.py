from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from datetime import datetime

import json
import time
import undetected_chromedriver as uc


class MarketChameleonScraper:
    def __init__(self, driver_path=None):
        """Initialize the Selenium WebDriver."""
        self.driver = uc.Chrome(headless=False,use_subprocess=False)

        self.wait = WebDriverWait(self.driver, 20)

    def load_page(self, url="https://marketchameleon.com/volReports/VolatilityRankings"):
        self.driver.get(url)
        self.wait_for_element(By.CLASS_NAME, "horiz-filter-box")
        self.wait_for_element(By.CSS_SELECTOR, 'table[id="iv_rankings_report_tbl"]')
        time.sleep(5)

        spans = self.driver.find_elements(By.CSS_SELECTOR, 'span[data-jvalue]')
        for span in spans:
            if span.text == 'IV Up' or span.text == 'Common':
                print('cicked')
                span.click()
                time.sleep(5)

        time.sleep(5)
        select_element = Select(self.driver.find_element(By.NAME, "MarketCap"))
        select_element.select_by_value('Over 100000000000')

        time.sleep(5)
        select_element = Select(self.driver.find_element(By.NAME, "iv_rankings_report_tbl_length"))
        select_element.select_by_value('100')

        time.sleep(5)
        return self.fetch_table_data()
        
    def fetch_table_data(self):
        """Fetch all <tr> data from the <tbody> and return it as JSON."""
        try:
            tbody = self.driver.find_element(By.TAG_NAME, "tbody")
            rows = tbody.find_elements(By.TAG_NAME, "tr")  # Get all <tr> elements
            data = []

            for row in rows:
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) < 14:
                    continue  # Skip rows with missing data

                symbol = cells[0].find_element(By.TAG_NAME, 'a').text
                company_name = cells[1].text
                last_price = cells[2].text
                change_percent = cells[3].text
                market_cap = cells[4].text
                iv_rank = cells[9].text
                volume = cells[11].text
                earnings_date_raw = cells[13].text
                earnings_date = self.convert_date_to_yyyymmdd(earnings_date_raw)

                # Append the data as a dictionary
                data.append({
                    "symbol": symbol,
                    "company_name": company_name,
                    "last_price": last_price,
                    "change_percent": change_percent,
                    "market_cap": market_cap,
                    "iv_rank": iv_rank,
                    "volume": volume,
                    "earnings_date": earnings_date
                })

            return json.dumps(data, indent=4)
        except Exception as e:
            print(f"Error fetching table data: {e}")
            return json.dumps({"error": str(e)})

    def convert_date_to_yyyymmdd(self, date_str):
        """Convert date from '6-Nov-2024 AMC' to 'YYYYMMDD'."""
        try:
            # Remove any time-of-day information like "AMC"
            date_part = date_str.split()[0] if date_str else ""
            # Convert the string to a datetime object
            date_obj = datetime.strptime(date_part, "%d-%b-%Y")
            # Format the datetime object as YYYYMMDD
            return date_obj.strftime("%Y%m%d")
        except Exception as e:
            print(f"Error converting date: {e}")
            return None

    def wait_for_element(self, by, value):
        """Wait for the specified element to be present."""
        try:
            self.wait.until(EC.presence_of_element_located((by, value)))
            print(f"Element '{value}' loaded successfully.")
        except Exception as e:
            print(f"Error: {e}")

    def close(self):
        """Close the Selenium WebDriver."""
        self.driver.quit()

if __name__ == "__main__":
    controller = MarketChameleonScraper()
    print(controller.load_page())