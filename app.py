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

def get_listed_stock_price(stock_id):
    url = f'https://goodinfo.tw/tw/StockDetail.asp?STOCK_ID={stock_id}'
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://goodinfo.tw/"
    }
    r = requests.get(url, headers=headers)
    r.encoding = 'utf-8'
    soup = BeautifulSoup(r.text, 'html.parser')
    # 這裡假設抓取 K 線資料中的收盤價，範例簡化：
    price_tag = soup.select_one("td#_closingPrice")
    if price_tag:
        return float(price_tag.text.replace(",", ""))
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
            # 只處理上市，直接算 CDP 的部分略...
            reply = f"{stock_id} 上市收盤價：{price:.2f}，CDP 計算中..."
        else:
            reply = f"找不到 {stock_id} 的上市收盤價。"
    else:
        reply = "請輸入股票代號。"
    line_bot_api.reply_message(event.reply_token, TextSendMessage(reply))

if __name__ == "__main__":
    app.run(debug=True, port=int(os.getenv("PORT", 5000)))
