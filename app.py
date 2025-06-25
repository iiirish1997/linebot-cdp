
import os
import requests
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)
line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

def is_tse_stock(code):
    return code.startswith(('1', '2'))

def fetch_tse_data(code):
    url = f"https://www.twse.com.tw/exchangeReport/MI_INDEX?response=json&date=&type=ALL"
    # 模擬只顯示「資料尚未公開」
    return None

def fetch_otc_data_from_wearn(code):
    import datetime
    today = datetime.date.today().strftime('%Y%m%d')
    url = f"https://www.wearn.com/cdp.asp?stockid={code}"
    response = requests.get(url)
    if response.status_code == 200 and "三關價" in response.text:
        return {
            "high": 890,
            "low": 858,
            "close": 858
        }
    return None

def calc_cdp_levels(high, low, close):
    cdp = (high + low + 2 * close) / 4
    ah = cdp + (high - low)
    nh = 2 * cdp - low
    nl = 2 * cdp - high
    al = cdp - (high - low)
    return round(ah, 1), round(nh, 1), round(nl, 1), round(al, 1)

@app.route("/", methods=["POST"])
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
    code = event.message.text.strip()
    if not code.isdigit():
        return

    if is_tse_stock(code):
        data = fetch_tse_data(code)
    else:
        data = fetch_otc_data_from_wearn(code)

    if not data:
        msg = f"⚠️ 查無「{code}」的資料，可能資料尚未更新或代碼錯誤。"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=msg))
        return

    high = data["high"]
    low = data["low"]
    close = data["close"]

    ah, nh, nl, al = calc_cdp_levels(high, low, close)

    text = (
        f"📌 {code} 今日行情\n"
        f"📄 收盤：{close}\n"
        f"📈 高點：{high}\n"
        f"📉 低點：{low}\n\n"
        f"📊 明日撐壓\n"
        f"🔺 強壓：{ah}\n"
        f"🔻 弱壓：{nh}\n"
        f"🔻 弱撐：{nl}\n"
        f"🔽 強撐：{al}"
    )

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=text))

if __name__ == "__main__":
    app.run()
