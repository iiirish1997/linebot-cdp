
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os
import requests
from bs4 import BeautifulSoup
import re

app = Flask(__name__)

line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

@app.route("/", methods=["GET"])
def home():
    return "CDP bot is running."

@app.route("/", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"

def fetch_stock_data(stock_id):
    try:
        url = f"https://goodinfo.tw/tw/StockDetail.asp?STOCK_ID={stock_id}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36"
        }
        res = requests.get(url, headers=headers, timeout=5)
        res.encoding = "utf-8"

        soup = BeautifulSoup(res.text, "html.parser")
        table = soup.find("table", class_="b1 p4_2 r10 box_shadow")

        if table is None:
            return None

        text = table.text
        match = re.search(r"收盤\xa0(.+?)\xa0.+?最高\xa0(.+?)\xa0.+?最低\xa0(.+?)\xa0", text)

        if not match:
            return None

        close = float(match.group(1).replace(',', ''))
        high = float(match.group(2).replace(',', ''))
        low = float(match.group(3).replace(',', ''))

        return {"close": close, "high": high, "low": low}

    except Exception as e:
        return None

def calc_cdp_formula(close, high, low):
    cdp = (high + low + 2 * close) / 4
    ah = cdp + (high - low)
    nh = 2 * cdp - low
    nl = 2 * cdp - high
    al = cdp - (high - low)
    return {"AH": round(ah, 1), "NH": round(nh, 1), "NL": round(nl, 1), "AL": round(al, 1)}

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    stock_id = event.message.text.strip()

    if not stock_id.isdigit():
        return

    stock_data = fetch_stock_data(stock_id)

    if not stock_data:
        reply = "⚠️ 無法取得資料，可能代碼錯誤或資料尚未更新。"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
        return

    result = calc_cdp_formula(stock_data["close"], stock_data["high"], stock_data["low"])

    reply = (
        f"📌 {stock_id} 今日行情\n"
        f"📉 收盤：{stock_data['close']}\n"
        f"📈 高點：{stock_data['high']}\n"
        f"📉 低點：{stock_data['low']}\n\n"
        f"📊 明日撐壓\n"
        f"🔺 強壓：{result['AH']}\n"
        f"🔻 弱壓：{result['NH']}\n"
        f"🔻 弱撐：{result['NL']}\n"
        f"🔽 強撐：{result['AL']}"
    )

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

