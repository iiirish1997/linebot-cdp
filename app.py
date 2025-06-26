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

# ✅ 修正後的 get_listed_stock_price()，可正確抓 2330 收盤價
def get_listed_stock_price(stock_id):
    url = f'https://goodinfo.tw/tw/StockDetail.asp?STOCK_ID={stock_id}'
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://goodinfo.tw/"
    }
    r = requests.get(url, headers=headers)
    r.encoding = 'utf-8'
    soup = BeautifulSoup(r.text, 'html.parser')

    # 抓第一個包含 <b> 的 <nobr> 標籤中的價格（法人表格中出現）
    tag = soup.select_one('nobr:has(b)')
    if tag:
        price_text = tag.text.strip().replace(",", "")
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
