
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os
from twstock import Stock

app = Flask(__name__)

line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

@app.route("/", methods=["GET"])
def home():
    return "CDP bot with twstock is running."

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
        stock = Stock(stock_id)
        stock.fetch_31()

        if not stock.price or not stock.high or not stock.low or not stock.close:
            return None

        return {
            "close": stock.close[-1],
            "high": stock.high[-1],
            "low": stock.low[-1]
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
    print(f"使用者輸入：{stock_id}")

    if not stock_id.isdigit():
        return

    stock_data = fetch_stock_data(stock_id)

    if not stock_data:
        reply = "⚠️ 無法取得資料，可能代碼錯誤或尚未更新。"
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

    try:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
        print("回覆成功")
    except Exception as e:
        print(f"回覆錯誤：{e}")
