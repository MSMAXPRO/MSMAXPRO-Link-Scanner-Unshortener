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
# 2. ADVANCED UNSHORTENER (Anti-Bot Bypass)
# ---------------------------------------------------------
def unshorten_url(url):
    try:
        # Session banate hain taaki cookies store hon
        session = requests.Session()
        
        # Bilkul Real Chrome Browser ke Headers
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Referer": "https://www.google.com/",
            "Upgrade-Insecure-Requests": "1"
        }
        
        # Allow Redirects True rakha hai
        response = session.get(url, headers=headers, timeout=10, allow_redirects=True)
        
        # Check: Kya URL badla?
        if response.url == url:
            # Agar same raha, toh shayaad redirect fail hua
            return None, "No Redirect Detected (Protected Link)"
            
        return response.url, response.status_code
        
    except Exception as e:
        return None, str(e)

def is_suspicious(url):
    bad_keywords = ['hack', 'free-money', 'steal', 'login-verify', 'ngrok', 'crypto-gift']
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
    # (Same old stats logic kept simple for brevity)
    bot.reply_to(message, "📊 **System Status:** Online & Scanning")

# ---------------------------------------------------------
# 4. BOT HANDLERS
# ---------------------------------------------------------
@bot.message_handler(func=lambda m: MAINTENANCE_MODE == 'True')
def maintenance_msg(message):
    bot.reply_to(message, "⚠️ **Maintenance Mode Active.**")

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    track_activity(message) 
    bot.reply_to(message, 
        "🕵️‍♂️ **Deep Link Scanner**\n\n"
        "Send me any shortened link (bit.ly, tinyurl) and I will dig out the real destination."
    )

@bot.message_handler(func=lambda message: True)
def scan_link(message):
    text = message.text.strip()
    if not (text.startswith("http://") or text.startswith("https://")): return 

    track_activity(message) 
    msg = bot.reply_to(message, "🔍 **Bypassing Protection & Scanning...**")
    
    real_url, status = unshorten_url(text)
    
    # CASE 1: Scan Fail hua
    if not real_url:
        fail_text = (
            f"⚠️ **SCAN BLOCKED**\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"🔴 **Link:** {text}\n"
            f"❌ **Reason:** Server blocked the bot or No Redirect found.\n"
            f"🔒 This link might be protected."
        )
        bot.edit_message_text(fail_text, message.chat.id, msg.message_id)
        return

    # CASE 2: Scan Success
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
