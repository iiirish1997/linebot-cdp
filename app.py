from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os
import requests
import pandas as pd
from io import StringIO

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
        if stock_id.startswith('6'):
            url = f"https://www.tpex.org.tw/web/stock/trading/intraday_trading/intraday_trading_result/stk_result.php?l=zh-tw&d=113/06/25&stkno={stock_id}&s=0,asc"
        else:
            url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY_AVG_ALL?response=csv"

        res = requests.get(url, timeout=10)
        res.encoding = 'utf-8'

        if stock_id.startswith('6'):
            data = res.json()
            if 'aaData' not in data or not data['aaData']:
                return None
            latest = data['aaData'][-1]
            return {
                "close": float(latest[2].replace(",", "")),
                "high": float(latest[3].replace(",", "")),
                "low": float(latest[4].replace(",", ""))
            }
        else:
            df = pd.read_csv(StringIO(res.text))
            df = df[df['證券代號'] == stock_id]
            if df.empty:
                return None
            row = df.iloc[-1]
            return {
                "close": float(row["收盤價"]),
                "high": float(row["最高價"]),
                "low": float(row["最低價"])
            }

    except Exception as e:
        print(f"抓資料錯誤: {e}")
        return None

def calc_cdp_formula(close, high, low):
    cdp = (high + low + 2 * close) / 4
    ah = cdp + (high - low)
    nh = 2 * cdp - low
    nl = 2 * cdp - high
    al = cdp - (high - low)
    return {
        "AH": round(ah, 1),
        "NH": round(nh, 1),
        "NL": round(nl, 1),
        "AL": round(al, 1)
    }

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
        f"📌 {stock_id} 今日行情
"
        f"📉 收盤：{stock_data['close']}
"
        f"📈 高點：{stock_data['high']}
"
        f"📉 低點：{stock_data['low']}

"
        f"📊 明日撐壓
"
        f"🔺 強壓：{result['AH']}
"
        f"🔻 弱壓：{result['NH']}
"
        f"🔻 弱撐：{result['NL']}
"
        f"🔽 強撐：{result['AL']}"
    )
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
