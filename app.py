
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os
import requests
from bs4 import BeautifulSoup
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

def is_tse(code):
    return code.startswith(('1', '2', '3', '4', '5', '6', '9'))

def fetch_tse_data():
    today = datetime.today().strftime('%Y%m%d')
    url = f"https://www.twse.com.tw/exchangeReport/MI_INDEX?response=json&date={today}&type=ALL"
    res = requests.get(url, verify=False)
    data = res.json()
    stock_data = {}

    if "data9" in data:
        for row in data["data9"]:
            code = row[0].strip()
            name = row[1].strip()
            try:
                high = float(row[4].replace(",", ""))
                low = float(row[5].replace(",", ""))
                close = float(row[6].replace(",", ""))
                stock_data[code] = {"name": name, "high": high, "low": low, "close": close}
                stock_data[name] = stock_data[code]
            except:
                continue
    return stock_data

def fetch_otc_data(code):
    url = f"https://goodinfo.tw/tw/StockDetail.asp?STOCK_ID={code}"
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")
    try:
        table = soup.find("table", class_="b1 p4_2 r10 box_shadow")
        tds = table.find_all("td")
        high, low, close = None, None, None
        for idx, td in enumerate(tds):
            if "最高" in td.text:
                high = float(tds[idx + 1].text.strip())
            elif "最低" in td.text:
                low = float(tds[idx + 1].text.strip())
            elif "收盤" in td.text:
                close = float(tds[idx + 1].text.strip())
        if high and low and close:
            return {"name": code, "high": high, "low": low, "close": close}
    except:
        return None

def calculate_cdp(high, low, close):
    cdp = (high + low + 2 * close) / 4
    ah = cdp + (high - low)
    nh = 2 * cdp - low
    nl = 2 * cdp - high
    al = cdp - (high - low)
    return {
        "AH": round(ah, 2),
        "NH": round(nh, 2),
        "NL": round(nl, 2),
        "AL": round(al, 2)
    }

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text.strip()
    stock_data = fetch_tse_data() if is_tse(text) else {}
    info = stock_data.get(text) or fetch_otc_data(text)

    if not info:
        msg = f"❓ 查無 [{text}] 的資料，可能資料尚未更新或代碼錯誤。"
    else:
        high, low, close = info["high"], info["low"], info["close"]
        cdp = calculate_cdp(high, low, close)
        msg = (
            f"📌 {text} 今日行情
"
            f"📉 收盤：{close}
"
            f"📈 高點：{high}
"
            f"📉 低點：{low}

"
            f"📊 明日撐壓
"
            f"🔺 強壓：{cdp['AH']}
"
            f"🔻 弱壓：{cdp['NH']}
"
            f"🔻 弱撐：{cdp['NL']}
"
            f"🔽 強撐：{cdp['AL']}"
        )

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=msg)
    )
