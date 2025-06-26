import os
import requests
from bs4 import BeautifulSoup
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

LINE_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_SECRET = os.getenv("LINE_CHANNEL_SECRET")
line_bot_api = LineBotApi(LINE_TOKEN)
handler = WebhookHandler(LINE_SECRET)

# ✅ 修正後的抓取上市股票收盤價函式
def get_listed_stock_price(stock_id):
    url = f'https://goodinfo.tw/tw/StockDetail.asp?STOCK_ID={stock_id}'
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://goodinfo.tw/"
    }
    r = requests.get(url, headers=headers)
    r.encoding = 'utf-8'
    soup = BeautifulSoup(r.text, 'html.parser')
    
    # 找到「個股資料表」中出現「收盤價」的欄位
    table = soup.find("table", class_="b1 p4_2 r10 box_shadow")
    if table:
        rows = table.find_all("tr")
        for row in rows:
            cells = row.find_all("td")
            if len(cells) >= 2 and "收盤" in cells[0].text:
                price_text = cells[1].text.strip().replace(",", "")
                try:
                    return float(price_text)
                except ValueError:
                    return None
    return None

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text.strip()
    if text.isdigit():
        stock_id = text
        price = get_listed_stock_price(stock_id)
        if price:
            reply = f"{stock_id} 上市收盤價：{price:.2f}，CDP 計算中..."
        else:
            reply = f"找不到 {stock_id} 的上市收盤價。"
    else:
        reply = "請輸入股票代號。"
    line_bot_api.reply_message(event.reply_token, TextSendMessage(reply))

if __name__ == "__main__":
    app.run(debug=True, port=int(os.getenv("PORT", 5000)))
