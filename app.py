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

def get_listed_prices(stock_id):
    today = datetime.now().strftime("%Y%m%d")
    url = f"https://www.twse.com.tw/exchangeReport/MI_INDEX?response=json&date={today}&type=ALLBUT0999"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json()
        if "data9" in data:
            for row in data["data9"]:
                if row[0].strip() == stock_id:
                    high = float(row[4].replace(",", ""))
                    low = float(row[5].replace(",", ""))
                    close = float(row[8].replace(",", ""))
                    return close, high, low
    except Exception as e:
        print(f"⚠️ 抓取資料錯誤：{e}")
    return None, None, None

def calculate_cdp(C, H, L):
    CDP = (H + L + 2 * C) / 4
    AH = CDP + (H - L)
    NH = 2 * CDP - L
    NL = 2 * CDP - H
    AL = CDP - (H - L)
    return CDP, AH, NH, NL, AL

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
        C, H, L = get_listed_prices(stock_id)
        if C and H and L:
            CDP, AH, NH, NL, AL = calculate_cdp(C, H, L)
            reply_text = f"""📌 {stock_id} 今日行情
📉 收盤：{C}
📈 高點：{H}
📉 低點：{L}

📊 明日撐壓
🔺 強壓：{AH:.1f}
🔻 弱壓：{H}
🔻 弱撐：{L}
🔽 強撐：{AL:.1f}
"""
        else:
            reply_text = "⚠️ 今日資料尚未公布，請於收盤後（15:00 後）再試。"
    else:
        reply_text = "請輸入股票代號。"

    line_bot_api.reply_message(event.reply_token, TextSendMessage(reply_text))

if __name__ == "__main__":
    app.run(debug=True, port=int(os.getenv("PORT", 5000)))
