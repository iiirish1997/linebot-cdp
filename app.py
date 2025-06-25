
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os
import requests
from datetime import datetime
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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

def fetch_single_stock(stock_no):
    """抓取個股最近交易日的高低收"""
    today = datetime.today().strftime('%Y%m01')  # 當月第一天
    url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={today}&stockNo={stock_no}"
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers, verify=False)

    try:
        data = res.json()
    except:
        return None

    if "data" not in data:
        return None

    for row in reversed(data["data"]):
        try:
            high = float(row[4].replace(",", ""))
            low = float(row[5].replace(",", ""))
            close = float(row[6].replace(",", ""))
            return {"high": high, "low": low, "close": close}
        except:
            continue

    return None

def calculate_cdp_website_model(high, low, close):
    cdp = (high + low + close) / 3
    strong_resist = round(cdp + 2 * (cdp - low), 2)  # 多頭區 -> 強壓
    weak_resist = round(cdp + (cdp - low), 2)        # 轉強 -> 弱壓
    weak_support = round(cdp - (high - cdp), 2)      # 轉弱 -> 弱撐
    strong_support = round(cdp - 2 * (high - cdp), 2) # 空頭 -> 強撐
    return {
        "AH": strong_resist,
        "H": weak_resist,
        "L": weak_support,
        "AL": strong_support
    }

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text.strip()

    if not text.isdigit():
        msg = "⚠️ 請輸入正確的股票代碼，例如：2330（台積電）"
    else:
        stock_info = fetch_single_stock(text)
        if stock_info:
            high, low, close = stock_info["high"], stock_info["low"], stock_info["close"]
            cdp = calculate_cdp_website_model(high, low, close)
            msg = (
                f"📌 {text} 今日行情\n"
                f"📉 收盤：{close}\n"
                f"📈 高點：{high}\n"
                f"📉 低點：{low}\n"
                f"\n📊 明日撐壓（網站版）\n"
                f"🔺 強壓：{cdp['AH']}\n"
                f"🔻 弱壓：{cdp['H']}\n"
                f"🔻 弱撐：{cdp['L']}\n"
                f"🔽 強撐：{cdp['AL']}"
            )
        else:
            msg = f"❓ 查無「{text}」的資料，可能資料尚未更新或代碼錯誤。"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=msg)
    )
