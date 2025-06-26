# get_stock_data.py
import requests
from bs4 import BeautifulSoup

def get_stock_price(stock_id):
    url = f"https://goodinfo.tw/tw/StockDetail.asp?STOCK_ID={stock_id}"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://goodinfo.tw"
    }

    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")

    try:
        price_table = soup.find("table", class_="b1 p4_2 r10 box_shadow")
        rows = price_table.find_all("tr")
        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 7 and "最高" in cols[0].text:
                high = float(cols[1].text.replace(',', ''))
                low = float(cols[2].text.replace(',', ''))
                close = float(cols[6].text.replace(',', ''))
                return {"股票代號": stock_id, "最高價": high, "最低價": low, "收盤價": close}
    except Exception as e:
        print(f"[錯誤] 無法抓取 {stock_id}: {e}")
        return None

def calculate_cdp(H, L, C):
    CDP = (H + L + 2 * C) / 4
    AH = CDP + (H - L)
    NH = 2 * CDP - L
    NL = 2 * CDP - H
    AL = CDP - (H - L)
    return CDP, AH, H, L, AL
