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
def log_to_channel(text):
    """Logs safely without crashing"""
    if not LOG_CHANNEL_ID: return
    try:
        bot.send_message(int(LOG_CHANNEL_ID), text)
    except: pass

def unshorten_url(url):
    try:
        session = requests.Session()
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Referer": "https://www.google.com/"
        }
        response = session.get(url, headers=headers, timeout=9, allow_redirects=True)
        if response.url != url:
            return response.url, "Success"
        return None, "No Redirect/Block"
    except Exception as e:
        return None, str(e)

# ---------------------------------------------------------
# 3. ROBUST COMMANDS (No Reply_To Loop)
# ---------------------------------------------------------
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    try:
        # Debug Log (Optional: Remove if annoying)
        # log_to_channel(f"⚠️ Hit: /start from {message.from_user.id}")
        
        # FIX: 'reply_to' ki jagah 'send_message' use kiya hai.
        # Yeh kabhi fail nahi hoga agar message ID purani bhi ho gayi to.
        bot.send_message(
            message.chat.id, 
            "🕵️‍♂️ **Deep Link Scanner is Online!**\n\n"
            "Send me any link (bit.ly, tinyurl) to scan it."
        )
    except Exception as e:
        log_to_channel(f"❌ Error in Start: {e}")

@bot.message_handler(func=lambda m: True)
def scan_link(message):
    text = message.text.strip()
    if not (text.startswith("http://") or text.startswith("https://")): return 

    try:
        # Step 1: Processing msg bhejo
        status_msg = bot.send_message(message.chat.id, "🔍 **Scanning Link...**")
        
        # Step 2: Logic Run karo
        real_url, status = unshorten_url(text)
        
        # Step 3: Result edit karo
        if not real_url:
            bot.edit_message_text(f"❌ **Scan Failed:** {status}", message.chat.id, status_msg.message_id)
        else:
            domain = urlparse(real_url).netloc
            bot.edit_message_text(
                f"✅ **Link Result:**\n\n"
                f"🔴 **Short:** {text}\n"
                f"🟢 **Real:** {real_url}\n"
                f"🌐 **Domain:** {domain}",
                message.chat.id, status_msg.message_id,
                disable_web_page_preview=True
            )
            
            # Successful Log
            log_to_channel(f"✅ Scan Success | User: {message.from_user.id} | Domain: {domain}")
            
    except Exception as e:
        # Agar edit fail ho jaye, to naya message bhej do
        bot.send_message(message.chat.id, f"❌ Error: {e}")
        log_to_channel(f"❌ Critical Error: {e}")

# ---------------------------------------------------------
# 4. SERVER RUN
# ---------------------------------------------------------
@app.route('/', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        try:
            json_string = request.get_data().decode('utf-8')
            update = telebot.types.Update.de_json(json_string)
            bot.process_new_updates([update])
        except Exception as e:
            print(f"Update Error: {e}")
        return '' # ALWAYS return 200 OK to stop loop
    return Response(status=403)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
