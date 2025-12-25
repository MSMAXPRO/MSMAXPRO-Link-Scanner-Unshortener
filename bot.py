import telebot
import os
import requests
import urllib.request
import json
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
# 2. HYBRID ENGINE (With External API Backup)
# ---------------------------------------------------------
def log_to_channel(text):
    if not LOG_CHANNEL_ID: return
    try:
        bot.send_message(int(LOG_CHANNEL_ID), text)
    except: pass

def get_real_url(url):
    # --- LAYER 1: Standard Request (Fastest) ---
    try:
        session = requests.Session()
        headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36",
            "Referer": "https://www.google.com/"
        }
        response = session.get(url, headers=headers, timeout=5, allow_redirects=True, verify=False)
        if response.url != url and "bit.ly" not in response.url:
            return response.url
    except: pass

    # --- LAYER 2: Urllib (Python Built-in) ---
    try:
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1"}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            final_url = response.geturl()
            if final_url != url and "bit.ly" not in final_url:
                return final_url
    except: pass

    # --- LAYER 3: External API Bypass (The Bitly Killer) ---
    # Jab khud se na khule, toh dusre server se poocho
    try:
        api_url = f"https://unshorten.me/json/{url}"
        r = requests.get(api_url, timeout=8).json()
        if r['success'] and r['resolved_url']:
            return r['resolved_url']
    except: pass

    # Agar sab fail ho jaye
    return url

def check_virus_keywords(url):
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
        bot.send_message(message.chat.id, "**Deep Link Scanner Online!** (API Supported)")
    except: pass

@bot.message_handler(func=lambda m: True)
def scan_link(message):
    text = message.text.strip()
    if not (text.startswith("http://") or text.startswith("https://")): return 

    try:
        status_msg = bot.send_message(message.chat.id, "🔍 **Bypassing Protection...**")
        
        # Call the Hybrid Engine
        real_url = get_real_url(text)
        
        # Analysis
        is_risky, keyword = check_virus_keywords(real_url)
        domain = urlparse(real_url).netloc
        
        if is_risky:
            bot.edit_message_text(
                f"⚠️ **SUSPICIOUS LINK!**\n"
                f"🔴 Input: {text}\n"
                f"💀 Keyword: `{keyword}`\n"
                f"🛑 Status: UNSAFE",
                message.chat.id, status_msg.message_id
            )
        else:
            # Check success
            if real_url == text:
                status_text = "⚠️ Server Blocked (Could not unshorten)"
            else:
                status_text = "✅ Safe to Click"

            bot.edit_message_text(
                f"✅ **Scan Report**\n"
                f"🔗 **Real:** {real_url}\n"
                f"🌐 **Domain:** {domain}\n"
                f"🛡️ **Status:** {status_text}",
                message.chat.id, status_msg.message_id,
                disable_web_page_preview=True
            )
            
            log_to_channel(f"✅ Scan Success | User: {message.from_user.id} | Domain: {domain}")

    except Exception as e:
        bot.send_message(message.chat.id, f"Error: {e}")

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
