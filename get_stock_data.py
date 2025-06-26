from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import time

def get_stock_price(stock_id):
    url = f"https://goodinfo.tw/tw/StockDetail.asp?STOCK_ID={stock_id}"
    
    options = Options()
    options.add_argument("--headless")  # 無頭模式
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("window-size=1920x1080")
    options.add_argument("user-agent=Mozilla/5.0")
    
    driver = webdriver.Chrome(options=options)
    driver.get(url)
    time.sleep(3)  # 等待 JS 載入

    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    try:
        table = soup.find("table", class_="b1 p4_2 r10 box_shadow")  # goodinfo 的日線表格
        rows = table.find_all("tr")
        data_row = rows[2].find_all("td")  # 抓最近一天的資料

        high = float(data_row[4].text.replace(',', ''))
        low = float(data_row[5].text.replace(',', ''))
        close = float(data_row[6].text.replace(',', ''))

        # 計算 CDP
        cdp = round((high + low + 2 * close) / 4, 2)
        ah = round(cdp + (high - low), 2)
        nh = round(2 * cdp - low, 2)
        nl = round(2 * cdp - high, 2)
        al = round(cdp - (high - low), 2)

        return {
            "C": close,
            "H": high,
            "L": low,
            "AH": ah,
            "AL": al
        }

    except Exception as e:
        return None
