# app.py
import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from get_stock_data import get_stock_price, calculate_cdp

app = Flask(__name__)

line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

@app.route("/", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    stock_id = event.message.text.strip()
    price_data = get_stock_price(stock_id)

    if price_data:
        C = price_data["收盤價"]
        H = price_data["最高價"]
        L = price_data["最低價"]
        CDP, AH, NH, NL, AL = calculate_cdp(H, L, C)

        reply = f"\n📌 {stock_id} 今日行情\n📉 收盤：{C}\n📈 高點：{H}\n📉 低點：{L}\n\n📊 明日撐壓\n🔺 強壓：{AH}\n🔻 弱壓：{H}\n🔻 弱撐：{L}\n🔽 強撐：{AL}"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
    else:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="查無資料，請確認股票代號是否正確。"))

if __name__ == "__main__":
    app.run()
