import telebot
import os
import requests
import urllib.request
import re
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
# 2. ADVANCED LOGIC
# ---------------------------------------------------------
def log_to_channel(text):
    if not LOG_CHANNEL_ID: return
    try:
        bot.send_message(int(LOG_CHANNEL_ID), text)
    except: pass

def is_junk_url(url):
    """Checks if the result is a garbage scraper link (Twitter share, etc)"""
    junk = ['twitter.com/intent', 'facebook.com/sharer', 'linkedin.com/share', 'reddit.com/submit']
    for j in junk:
        if j in url.lower(): return True
    return False

def get_real_url(url):
    # --- LAYER 1: Standard Request ---
    try:
        session = requests.Session()
        headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36",
            "Referer": "https://www.google.com/"
        }
        response = session.get(url, headers=headers, timeout=4, allow_redirects=True, verify=False)
        if response.url != url and "bit.ly" not in response.url and not is_junk_url(response.url):
            return response.url
    except: pass

    # --- LAYER 2: ExpandURL API ---
    try:
        api_url = f"http://expandurl.com/api/v1/?url={url}"
        r = requests.get(api_url, timeout=5)
        if r.status_code == 200 and r.text.startswith("http") and not is_junk_url(r.text):
            return r.text.strip()
    except: pass

    # --- LAYER 3: Proxy Scraper (CheckShortURL) - FIXED ---
    try:
        check_url = f"http://checkshorturl.com/expand.php?u={url}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(check_url, headers=headers, timeout=8).text
        
        # New Strict Regex: Sirf Table ke andar wala link uthayega
        match = re.search(r'Long URL</td>\s*<td><a href="(.*?)"', response, re.DOTALL | re.IGNORECASE)
        if match and match.group(1):
            scraped_url = match.group(1)
            if not is_junk_url(scraped_url):
                return scraped_url
    except: pass

    # Fallback
    return url

def check_virus_keywords(url_input, url_output):
    """Checks BOTH input and output for virus words"""
    bad_keywords = ['hack', 'free-money', 'steal', 'login', 'verify', 'account-update', 'ngrok', 'crypto']
    
    # Check 1: Input Link (Isi ne pehle dhoka diya tha)
    for word in bad_keywords:
        if word in url_input.lower():
            return True, word, "Input Link"
            
    # Check 2: Real Destination
    if url_output and url_output != url_input:
        for word in bad_keywords:
            if word in url_output.lower():
                return True, word, "Destination Link"
                
    return False, None, None

# ---------------------------------------------------------
# 3. BOT HANDLERS
# ---------------------------------------------------------
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    try:
        bot.send_message(message.chat.id, "**Deep Link Scanner v6.0** (Safety First)")
    except: pass

@bot.message_handler(func=lambda m: True)
def scan_link(message):
    text = message.text.strip()
    if not (text.startswith("http://") or text.startswith("https://")): return 

    try:
        status_msg = bot.send_message(message.chat.id, "🔍 **Scanning Security...**")
        
        # 1. Unshorten
        real_url = get_real_url(text)
        
        # 2. Double Security Check (Input + Output)
        is_risky, keyword, source = check_virus_keywords(text, real_url)
        
        domain = urlparse(real_url).netloc
        
        if is_risky:
            # ⚠️ DANGER FOUND
            bot.edit_message_text(
                f"⚠️ **SUSPICIOUS LINK DETECTED!**\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"🔴 **Input:** {text}\n"
                f"💀 **Keyword:** `{keyword}` (Found in {source})\n"
                f"🛑 **Status:** UNSAFE (Do not click)",
                message.chat.id, status_msg.message_id,
                disable_web_page_preview=True
            )
        else:
            # ✅ SAFE
            if real_url == text:
                note = "Could not unshorten (Direct/Protected)"
            else:
                note = "Unshortened Successfully"

            bot.edit_message_text(
                f"✅ **Link Revealed**\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"🔗 **Real:** {real_url}\n"
                f"🌐 **Domain:** {domain}\n"
                f"ℹ️ **Note:** {note}\n"
                f"🛡️ **Status:** ✅ Safe to Click",
                message.chat.id, status_msg.message_id,
                disable_web_page_preview=True
            )
            
            log_to_channel(f"✅ Scan | User: {message.from_user.id} | Domain: {domain}")

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
