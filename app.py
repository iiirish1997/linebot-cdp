from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os
import requests
from bs4 import BeautifulSoup
import datetime

app = Flask(__name__)

line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

def get_stock_data_twse(stock_id):
    today = datetime.datetime.now()
    date_str = f"{today.year - 1911}{today.strftime('%m%d')}"
    url = f'https://www.twse.com.tw/exchangeReport/MI_INDEX?response=json&date={today.strftime("%Y%m%d")}&type=ALL'
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    response = requests.get(url, headers=headers)
    try:
        data = response.json()
        for row in data['data9']:
            if row[0].strip() == stock_id:
                try:
                    close = float(row[8].replace(',', ''))
                    high = float(row[4].replace(',', ''))
                    low = float(row[5].replace(',', ''))
                    return close, high, low
                except:
                    return None
        return None
    except:
        return None

def calculate_cdp(close, high, low):
    cdp = (high + low + 2 * close) / 4
    ah = cdp + (high - low)
    nh = 2 * cdp - low
    nl = 2 * cdp - high
    al = cdp - (high - low)
    return round(ah, 1), round(nh, 1), round(nl, 1), round(al, 1)

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
    text = event.message.text.strip()
    if text.isdigit():
        stock_id = text
        stock_data = get_stock_data_twse(stock_id)
        if stock_data:
            close, high, low = stock_data
            ah, nh, nl, al = calculate_cdp(close, high, low)
            message = f"""📌 {stock_id} 今日行情
📉 收盤：{close}
📈 高點：{high}
📉 低點：{low}

📊 明日撐壓
🔺 強壓：{ah}
🔻 弱壓：{high}
🔻 弱撐：{low}
🔽 強撐：{al}"""
        else:
            message = f"⚠️ 今日資料尚未公布，請於收盤後（15:00 後）再試。"
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=message)
        )

if __name__ == "__main__":
    app.run()
