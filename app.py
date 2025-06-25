from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os
import requests
from datetime import datetime

app = Flask(__name__)

line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

@app.route("/", methods=["GET"])
def home():
    return "CDP Line Bot is running!"

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"

def fetch_tse_data():
    """抓取當日台股收盤資料"""
    today = datetime.today().strftime('%Y%m%d')
    url = f"https://www.twse.com.tw/exchangeReport/MI_INDEX?response=json&date={today}&type=ALL"
    res = requests.get(url)
    data = res.json()
    stock_data = {}

    if "data9" in data:
        for row in data["data9"]:
            code = row[0].strip()
            name = row[1].strip()
            try:
                high = float(row[4].replace(",", ""))
                low = float(row[5].replace(",", ""))
                close = float(row[6].replace(",", ""))
                stock_data[code] = {"name": name, "high": high, "low": low, "close": close}
                stock_data[name] = stock_data[code]  # 讓用名稱也可以查
            except:
                continue
    return stock_data

def calculate_cdp(high, low, close):
    """計算 CDP 區間"""
    cdp = (high + low + close) / 3
    ah = cdp + (high - low)
    al = cdp - (high - low)
    return {
        "AH": round(ah, 2),
        "H": round((cdp + high) / 2, 2),
        "CDP": round(cdp, 2),
        "L": round((cdp + low) / 2, 2),
        "AL": round(al, 2)
    }

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text.strip()
    stock_data = fetch_tse_data()

    if text in stock_data:
        info = stock_data[text]
        high, low, close = info["high"], info["low"], info["close"]
        cdp = calculate_cdp(high, low, close)
        msg = (
            f"📈 {text}（{info['name']}）今日數據\n"
            f"收盤：{close}｜最高：{high}｜最低：{low}\n"
            f"\n🔍 隔日 CDP 區間：\n"
            f"・AH：{cdp['AH']}\n"
            f"・H：{cdp['H']}\n"
            f"・CDP：{cdp['CDP']}\n"
            f"・L：{cdp['L']}\n"
            f"・AL：{cdp['AL']}"
        )
    else:
        msg = "請輸入正確的股票代碼或名稱（如：2330 或 台積電）"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=msg)
    )
