from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import requests
from bs4 import BeautifulSoup
import re
import os

app = Flask(__name__)

# 從環境變數取得 LINE Bot 資訊
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)


def get_stock_data_yahoo(stock_id):
    url = f\"https://tw.stock.yahoo.com/quote/{stock_id}.TW\"
    headers = {\"User-Agent\": \"Mozilla/5.0\"}
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, \"html.parser\")

    pattern = re.compile(r\"\\u9ad8\\u4ef6\\u50f9.+?>(\\d+\\.\\d+)<\")  # 高點
    high = low = close = None

    try:
        price_tags = soup.find_all(\"span\")
        prices = [tag.text.strip() for tag in price_tags if re.match(r\"^\\d+(\\.\\d+)?$\", tag.text.strip())]
        high = float(prices[3])
        low = float(prices[4])
        close = float(prices[5])
        return high, low, close
    except:
        return None, None, None


def calculate_cdp(h, l, c):
    cdp = (h + l + 2 * c) / 4
    ah = round(cdp + (cdp - l), 2)  # 強壓
    nh = round(cdp + (h - l), 2)    # 弱壓
    nl = round(cdp - (h - l), 2)    # 弱撐
    al = round(cdp - (cdp - h), 2)  # 強撐
    return ah, nh, nl, al


@app.route(\"/callback\", methods=['POST'])
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
    msg = event.message.text.strip().upper()

    if msg.startswith(\"撐壓\"):
        parts = msg.split()
        if len(parts) == 2 and parts[1].isdigit():
            stock_id = parts[1]
            high, low, close = get_stock_data_yahoo(stock_id)

            if high and low and close:
                ah, nh, nl, al = calculate_cdp(high, low, close)
                reply = (
                    f\"{stock_id}\\n\"
                    f\"強壓：{ah}\\n\"
                    f\"弱壓：{nh}\\n\"
                    f\"弱撐：{nl}\\n\"
                    f\"強撐：{al}\"
                )
            else:
                reply = f\"查詢失敗：無法取得 {stock_id} 的股價資料\"

            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=reply)
            )
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=\"請輸入正確格式，例如：撐壓 2330\")
            )


if __name__ == \"__main__":
    app.run()
