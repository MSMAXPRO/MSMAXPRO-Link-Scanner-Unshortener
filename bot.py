import telebot
import os
import requests
from urllib.parse import urlparse
from flask import Flask, request, Response
from datetime import datetime

# ---------------------------------------------------------
# 1. CONFIGURATION
# ---------------------------------------------------------
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
ADMIN_ID = os.environ.get('ADMIN_ID')
LOG_CHANNEL_ID = os.environ.get('LOG_CHANNEL_ID') 
MAINTENANCE_MODE = os.environ.get('MAINTENANCE_MODE', 'False')
STARTING_OFFSET = 1700 

bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

# ---------------------------------------------------------
# 2. UNSHORTENER ENGINE (Double Power)
# ---------------------------------------------------------
def unshorten_url(url):
    # Method 1: Session with Chrome Headers (Best for Bitly)
    try:
        session = requests.Session()
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Referer": "https://www.google.com/"
        }
        response = session.get(url, headers=headers, timeout=10, allow_redirects=True)
        
        if response.url != url:
            return response.url, "Success"
    except:
        pass
    
    # Method 2: Fallback (Simple Request)
    try:
        response = requests.get(url, timeout=5, allow_redirects=True)
        if response.url != url:
            return response.url, "Success"
    except Exception as e:
        return None, str(e)

    # Agar ab bhi same hai, toh fail maano
    return None, "Same URL (Block/No Redirect)"

def is_suspicious(url):
    bad_keywords = ['hack', 'free-money', 'steal', 'login-verify', 'ngrok', 'crypto']
    for word in bad_keywords:
        if word in url.lower(): return True
    return False

# ---------------------------------------------------------
# 3. TRACKING & STATS
# ---------------------------------------------------------
def track_activity(message):
    if not LOG_CHANNEL_ID: return
    try:
        bot.send_message(int(LOG_CHANNEL_ID), f"🕵️‍♂️ Hit from LinkScanner | User: {message.from_user.id}")
    except: pass

@bot.message_handler(commands=['stats'])
def stats_command(message):
    bot.reply_to(message, "📊 **System Status:** Online (v3.0 Running)")

# ---------------------------------------------------------
# 4. BOT HANDLERS
# ---------------------------------------------------------
@bot.message_handler(func=lambda m: MAINTENANCE_MODE == 'True')
def maintenance_msg(message):
    bot.reply_to(message, "⚠️ **Maintenance Mode Active.**")

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    track_activity(message) 
    # Version Tag se confirm hoga ki code update hua ya nahi
    bot.reply_to(message, 
        "🕵️‍♂️ **Deep Link Scanner v3.0 (Fixed)**\n"
        "━━━━━━━━━━━━━━━━\n"
        "Send me a link to scan. I will bypass Bitly protection!"
    )

@bot.message_handler(func=lambda message: True)
def scan_link(message):
    text = message.text.strip()
    if not (text.startswith("http://") or text.startswith("https://")): return 

    track_activity(message) 
    msg = bot.reply_to(message, "🔍 **Scanning (v3 Engine)...**")
    
    real_url, status = unshorten_url(text)
    
    # FAILURE CASE: Agar link unshorten nahi hua
    if not real_url:
        fail_text = (
            f"⚠️ **SCAN BLOCKED / FAILED**\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"🔴 **Link:** {text}\n"
            f"🔒 **Status:** Could not unshorten.\n"
            f"📝 **Reason:** {status}"
        )
        bot.edit_message_text(fail_text, message.chat.id, msg.message_id)
        return

    # SUCCESS CASE
    safety_status = "✅ Safe to Click"
    if is_suspicious(real_url): safety_status = "⚠️ **SUSPICIOUS / RISKY**"
    
    domain = urlparse(real_url).netloc

    output = (
        f"🕵️‍♂️ **LINK REVEALED**\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"🔴 **Short:** {text}\n"
        f"🟢 **Real:**\n`{real_url}`\n\n"
        f"🌐 **Domain:** {domain}\n"
        f"🛡️ **Status:** {safety_status}"
    )
    
    bot.delete_message(message.chat.id, msg.message_id)
    bot.send_message(message.chat.id, output, parse_mode="Markdown", disable_web_page_preview=True)

# ---------------------------------------------------------
# 5. SERVER RUN
# ---------------------------------------------------------
@app.route('/', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        bot.process_new_updates([telebot.types.Update.de_json(request.get_data().decode('utf-8'))])
        return ''
    return Response(status=403)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
