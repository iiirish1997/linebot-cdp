
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

def calculate_cdp_custom(high, low, close):
    cdp = (high + low + 2 * close) / 4
    ah = round(cdp + (high - low), 2)         # AH
    nh = round(2 * cdp - low, 2)              # NH
    nl = round(2 * cdp - high, 2)             # NL
    al = round(cdp - (high - low), 2)         # AL
    return {
        "AH": ah,
        "NH": nh,
        "NL": nl,
        "AL": al
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
            cdp_result = calculate_cdp_custom(high, low, close)
            msg = (
                f"📌 {text} 今日行情\n"
                f"📉 收盤：{close}\n"
                f"📈 高點：{high}\n"
                f"📉 低點：{low}\n"
                f"\n📊 明日撐壓\n"
                f"🔺 AH：{cdp_result['AH']}\n"
                f"🔻 NH：{cdp_result['NH']}\n"
                f"🔻 NL：{cdp_result['NL']}\n"
                f"🔽 AL：{cdp_result['AL']}"
            )
        else:
            msg = f"❓ 查無「{text}」的資料，可能資料尚未更新或代碼錯誤。"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=msg)
    )
