
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

def fetch_stock_data(stock_no):
    """根據股票代碼自動抓取 上市 or 上櫃 資料"""
    today = datetime.today().strftime('%Y%m%d')
    headers = {"User-Agent": "Mozilla/5.0"}

    if stock_no.startswith("6") or stock_no.startswith("1") or stock_no.startswith("2") or stock_no.startswith("3") or stock_no.startswith("4") or stock_no.startswith("5"):
        # 上市
        url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={today[:6]}01&stockNo={stock_no}"
        res = requests.get(url, headers=headers, verify=False)
        try:
            data = res.json()
            for row in reversed(data.get("data", [])):
                try:
                    high = float(row[4].replace(",", ""))
                    low = float(row[5].replace(",", ""))
                    close = float(row[6].replace(",", ""))
                    return {"high": high, "low": low, "close": close}
                except:
                    continue
        except:
            return None
    else:
        # 上櫃
        url = f"https://www.tpex.org.tw/web/stock/aftertrading/daily_trading/st43_result.php?l=zh-tw&d={int(today[:4]) - 1911}/{today[4:6]}/{today[6:]}&stkno={stock_no}&_=123"
        res = requests.get(url, headers=headers, verify=False)
        try:
            data = res.json()
            for row in reversed(data.get("aaData", [])):
                try:
                    high = float(row[4].replace(",", ""))
                    low = float(row[5].replace(",", ""))
                    close = float(row[2].replace(",", ""))
                    return {"high": high, "low": low, "close": close}
                except:
                    continue
        except:
            return None
    return None

def calculate_cdp_custom(high, low, close):
    cdp = (high + low + 2 * close) / 4
    strong_resist = round(cdp + (high - low), 2)
    weak_resist = round(2 * cdp - low, 2)
    weak_support = round(2 * cdp - high, 2)
    strong_support = round(cdp - (high - low), 2)
    return {
        "強壓": strong_resist,
        "弱壓": weak_resist,
        "弱撐": weak_support,
        "強撐": strong_support
    }

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text.strip()

    if not text.isdigit():
        msg = "⚠️ 請輸入正確的股票代碼，例如：2330（台積電）"
    else:
        stock_info = fetch_stock_data(text)
        if stock_info:
            high, low, close = stock_info["high"], stock_info["low"], stock_info["close"]
            cdp_result = calculate_cdp_custom(high, low, close)
            msg = (
                f"📌 {text} 今日行情\n"
                f"📉 收盤：{close}\n"
                f"📈 高點：{high}\n"
                f"📉 低點：{low}\n"
                f"\n📊 明日撐壓\n"
                f"🔺 強壓：{cdp_result['強壓']}\n"
                f"🔻 弱壓：{cdp_result['弱壓']}\n"
                f"🔻 弱撐：{cdp_result['弱撐']}\n"
                f"🔽 強撐：{cdp_result['強撐']}"
            )
        else:
            msg = f"❓ 查無「{text}」的資料，可能資料尚未更新或代碼錯誤。"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=msg)
    )
