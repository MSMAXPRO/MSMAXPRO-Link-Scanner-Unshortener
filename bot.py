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
# 2. SMART UNSHORTENER & SCANNER
# ---------------------------------------------------------
def log_to_channel(text):
    if not LOG_CHANNEL_ID: return
    try:
        bot.send_message(int(LOG_CHANNEL_ID), text)
    except: pass

def get_real_url(url):
    """
    Tries to follow redirects. 
    If no redirect happens (Direct link or Blocked), returns the original URL.
    """
    try:
        session = requests.Session()
        # Fake Mobile Headers to fool Bitly
        headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36",
            "Referer": "https://www.google.com/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
        }
        # Timeout badha diya aur verify=False kiya (SSL errors avoid karne ke liye)
        response = session.get(url, headers=headers, timeout=12, allow_redirects=True, verify=False)
        return response.url
    except Exception as e:
        # Agar network error aaye, tab bhi Original URL wapas karo taaki scan ho sake
        return url

def check_virus_keywords(url):
    """Checks for suspicious words in the FINAL URL"""
    bad_keywords = ['hack', 'free-money', 'steal', 'login', 'verify', 'account-update', 'ngrok', 'crypto']
    for word in bad_keywords:
        if word in url.lower():
            return True, word
    return False, None

# ---------------------------------------------------------
# 3. BOT HANDLERS
# ---------------------------------------------------------
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    try:
        bot.send_message(
            message.chat.id, 
            "🕵️‍♂️ **Deep Link Scanner is Ready!**\n\n"
            "Send me Bitly, TinyURL, or Direct Links."
        )
    except: pass

@bot.message_handler(func=lambda m: True)
def scan_link(message):
    text = message.text.strip()
    if not (text.startswith("http://") or text.startswith("https://")): return 

    try:
        status_msg = bot.send_message(message.chat.id, "🔍 **Analyzing Link...**")
        
        # Step 1: Get Real URL (Redirect or Original)
        real_url = get_real_url(text)
        
        # Step 2: Security Check
        is_risky, keyword = check_virus_keywords(real_url)
        
        domain = urlparse(real_url).netloc
        
        if is_risky:
            # ⚠️ DANGER ALERT
            bot.edit_message_text(
                f"⚠️ **SUSPICIOUS LINK DETECTED!**\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"🔴 **Input:** {text}\n"
                f"💀 **Keyword Found:** `{keyword}`\n"
                f"🛑 **Status:** UNSAFE (Do not click)",
                message.chat.id, status_msg.message_id
            )
        else:
            # ✅ SAFE REPORT
            bot.edit_message_text(
                f"✅ **Link Scan Report**\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"🔗 **Real Destination:**\n{real_url}\n\n"
                f"🌐 **Domain:** {domain}\n"
                f"🛡️ **Status:** Seems Safe",
                message.chat.id, status_msg.message_id,
                disable_web_page_preview=True
            )
            
        log_to_channel(f"✅ Scan Done | User: {message.from_user.id} | Domain: {domain}")

    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error: {e}")

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
        except: pass
        return ''
    return Response(status=403)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
