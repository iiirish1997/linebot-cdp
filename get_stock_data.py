import requests
from bs4 import BeautifulSoup

def get_cdp_info(stock_id):
    url = f"https://goodinfo.tw/tw/StockDetail.asp?STOCK_ID={stock_id}"
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(url, headers=headers)
    response.encoding = "utf-8"
    soup = BeautifulSoup(response.text, "html.parser")

    try:
        table = soup.find("table", class_="b1 p4_2 r10 box_shadow")
        rows = table.find_all("tr")
        for row in rows:
            cells = row.find_all("td")
            if len(cells) >= 5 and "昨收" in cells[0].text:
                C = float(cells[1].text.strip())
                H = float(cells[2].text.strip())
                L = float(cells[3].text.strip())
                break
        else:
            raise ValueError("未找到價格資料")

        CDP = (H + L + 2 * C) / 4
        AH = CDP + (H - L)
        NH = 2 * CDP - L
        NL = 2 * CDP - H
        AL = CDP - (H - L)

        result = f"""📌 {stock_id} 今日行情
📉 收盤：{C}
📈 高點：{H}
📉 低點：{L}

📊 明日撐壓
🔺 強壓：{AH:.2f}
🔻 弱壓：{H}
🔻 弱撐：{L}
🔽 強撐：{AL:.2f}"""
        return result

    except Exception as e:
        return f"❌ 資料擷取失敗：{e}"
