import requests
import pandas as pd
from datetime import datetime

def fetch_today_stock_prices():
    date_str = datetime.now().strftime("%Y%m%d")
    url = f"https://www.twse.com.tw/exchangeReport/MI_INDEX?response=json&date={date_str}&type=ALLBUT0999"
    headers = {"User-Agent": "Mozilla/5.0"}

    response = requests.get(url, headers=headers)
    data = response.json()

    if "data9" not in data:
        print("⚠️ 今日資料尚未公布或格式錯誤")
        return

    rows = []
    for row in data["data9"]:
        stock_id = row[0].strip()
        name = row[1].strip()
        try:
            high = float(row[4].replace(",", ""))
            low = float(row[5].replace(",", ""))
            close = float(row[8].replace(",", ""))
            rows.append([stock_id, name, high, low, close])
        except:
            continue

    df = pd.DataFrame(rows, columns=["股票代號", "名稱", "最高價", "最低價", "收盤價"])
    df.to_excel("listed_prices.xlsx", index=False)
    print(f"✅ 已匯出 {len(df)} 筆資料至 listed_prices.xlsx")

if __name__ == "__main__":
    fetch_today_stock_prices()
