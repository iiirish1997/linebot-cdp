import os
import requests
from flask import Flask, request, abort
from bs4 import BeautifulSoup
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from datetime import datetime

app = Flask(__name__)

LINE_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_SECRET = os.getenv("LINE_CHANNEL_SECRET")
line_bot_api = LineBotApi(LINE_TOKEN)
handler = WebhookHandler(LINE_SECRET)

# ✅ 使用證交所收盤後 API（抓昨收，可用於 CDP）
def get_listed_stock_price(stock_id):
    today = datetime.now().strftime("%Y%m%d")
    url = f"https://www.twse.com.tw/exchangeReport/MI_INDEX?response=json&date={today}&type=ALLBUT0999"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json()
        if "data9" in data:
            for row in data['data9']:  # data9 = 普通股票
                if row[0].strip() == stock_id:
                    price = row[8].replace(",", "").strip()
                    return float(price)
    except Exception as e:
        print(f"⚠️ 抓取證交所資料錯誤：{e}")
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
            reply = "⚠️ 今日資料尚未公布，請於收盤後（15:00 後）再試。"
    else:
        reply = "請輸入股票代號。"
    line_bot_api.reply_message(event.reply_token, TextSendMessage(reply))

if __name__ == "__main__":
    app.run(debug=True, port=int(os.getenv("PORT", 5000)))
