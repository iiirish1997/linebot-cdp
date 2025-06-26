import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from linebot.exceptions import InvalidSignatureError
from get_stock_data import get_stock_price

app = Flask(__name__)
line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

@app.route("/", methods=["GET"])
def home():
    return "CDP Bot Running"

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    stock_id = event.message.text.strip()
    if not stock_id.isdigit():
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage("請輸入正確的股票代號（例如：2330）")
        )
        return

    result = get_stock_price(stock_id)
    if result:
        reply = f"""📌 {stock_id} 今日行情
📉 收盤：{result['C']}
📈 高點：{result['H']}
📉 低點：{result['L']}

📊 明日撐壓
🔺 強壓：{result['AH']}
🔻 弱壓：{result['H']}
🔻 弱撐：{result['L']}
🔽 強撐：{result['AL']}"""
    else:
        reply = "❌ 資料擷取失敗，請稍後再試或確認股票代號是否正確。"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(reply)
    )

if __name__ == "__main__":
    app.run()
