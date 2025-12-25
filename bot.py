import telebot
import os
import requests
from flask import Flask, request, Response
from urllib.parse import urlparse

# ---------------------------------------------------------
# 1. CONFIGURATION
# ---------------------------------------------------------
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
LOG_CHANNEL_ID = os.environ.get('LOG_CHANNEL_ID') 
MAINTENANCE_MODE = os.environ.get('MAINTENANCE_MODE', 'False')

bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

# ---------------------------------------------------------
# 2. HELPER FUNCTIONS
# ---------------------------------------------------------
def log_to_channel(message_text):
    """Safely send logs or errors to the channel"""
    if not LOG_CHANNEL_ID: return
    try:
        bot.send_message(int(LOG_CHANNEL_ID), message_text)
    except: pass

def unshorten_url(url):
    try:
        session = requests.Session()
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Referer": "https://www.google.com/"
        }
        response = session.get(url, headers=headers, timeout=10, allow_redirects=True)
        if response.url != url:
            return response.url, "Success"
        return None, "No Redirect Detected"
    except Exception as e:
        return None, str(e)

# ---------------------------------------------------------
# 3. BOT COMMANDS (With Error Catching)
# ---------------------------------------------------------
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    # Step 1: Log Try
    log_to_channel(f"⚠️ Debug: Start Command Received from {message.from_user.id}")
    
    try:
        # Step 2: Try to Reply
        bot.reply_to(message, 
            "🕵️‍♂️ **Deep Link Scanner is Online!**\n\n"
            "Send me any link to scan it."
        )
    except Exception as e:
        # Agar error aaya, toh channel mein batao
        log_to_channel(f"❌ Error replying to user: {e}")

@bot.message_handler(func=lambda m: True)
def scan_link(message):
    text = message.text.strip()
    if not (text.startswith("http://") or text.startswith("https://")): return 

    log_to_channel(f"⚠️ Debug: Scanning Link for {message.from_user.id}")

    try:
        msg = bot.reply_to(message, "🔍 **Scanning...**")
        real_url, status = unshorten_url(text)
        
        if not real_url:
            bot.edit_message_text(f"❌ Scan Failed: {status}", message.chat.id, msg.message_id)
        else:
            domain = urlparse(real_url).netloc
            bot.edit_message_text(
                f"✅ **Result:**\nShort: {text}\nReal: {real_url}\nDomain: {domain}",
                message.chat.id, msg.message_id
            )
    except Exception as e:
        log_to_channel(f"❌ Error in Scan: {e}")

# ---------------------------------------------------------
# 4. SERVER RUN
# ---------------------------------------------------------
@app.route('/', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    return Response(status=403)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
