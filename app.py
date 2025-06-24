from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os

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

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text.strip()
    if text.startswith("CDP "):
        try:
            price = float(text.split(" ")[1])
            h = round(price * 1.02, 2)
            l = round(price * 0.98, 2)
            tc = round((h + l + price) / 3, 2)
            ah = round(tc + (h - l), 2)
            al = round(tc - (h - l), 2)
            msg = f"🔍 根據輸入價格 {price}\nCDP參考區間：\n・AH：{ah}\n・H：{h}\n・TC：{tc}\n・L：{l}\n・AL：{al}"
        except:
            msg = "格式錯誤，請輸入：CDP 價格（例如：CDP 100）"
    else:
        msg = "請輸入「CDP 價格」來計算（例如：CDP 100）"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=msg)
    )
