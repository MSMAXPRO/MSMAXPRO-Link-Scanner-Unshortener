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
# 2. SECURITY LOGIC (Strict)
# ---------------------------------------------------------
def log_to_channel(text):
    if not LOG_CHANNEL_ID: return
    try:
        bot.send_message(int(LOG_CHANNEL_ID), text)
    except: pass

def check_virus_keywords(url):
    """Checks for dangerous words instantly"""
    if not url: return False, None
    bad_keywords = ['hack', 'free-money', 'steal', 'login', 'verify', 'account-update', 'ngrok', 'crypto', 'wallet']
    for word in bad_keywords:
        if word in url.lower():
            return True, word
    return False, None

def is_junk_url(url):
    """Filters out Garbage Scraper Results"""
    junk = ['twitter.com/intent', 'facebook.com/sharer', 'linkedin.com/share', 'checkshorturl.com']
    for j in junk:
        if j in url.lower(): return True
    return False

# ---------------------------------------------------------
# 3. UNSHORTENER ENGINE (Fixed Regex)
# ---------------------------------------------------------
def get_real_url(url):
    # --- LAYER 1: ExpandURL API ---
    try:
        api_url = f"http://expandurl.com/api/v1/?url={url}"
        r = requests.get(api_url, timeout=5)
        if r.status_code == 200 and r.text.startswith("http") and not is_junk_url(r.text):
            return r.text.strip()
    except: pass

    # --- LAYER 2: Proxy Scraper (Corrected Regex) ---
    try:
        check_url = f"http://checkshorturl.com/expand.php?u={url}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(check_url, headers=headers, timeout=8).text
        
        # FIX: Sirf Table ke andar wala Long URL uthayega
        match = re.search(r'Long URL</td>\s*<td><a href="([^"]+)"', response, re.IGNORECASE)
        if match and match.group(1):
            scraped_url = match.group(1)
            if not is_junk_url(scraped_url):
                return scraped_url
    except: pass

    # --- LAYER 3: Standard Request (Direct) ---
    try:
        session = requests.Session()
        headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36",
            "Referer": "https://www.google.com/"
        }
        response = session.get(url, headers=headers, timeout=4, allow_redirects=True, verify=False)
        if response.url != url and "bit.ly" not in response.url:
            return response.url
    except: pass

    # Fallback
    return url

# ---------------------------------------------------------
# 4. BOT HANDLERS
# ---------------------------------------------------------
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    try:
        bot.send_message(message.chat.id, "**Deep Link Scanner v7.0** (Instant Block)")
    except: pass

@bot.message_handler(func=lambda m: True)
def scan_link(message):
    text = message.text.strip()
    if not (text.startswith("http://") or text.startswith("https://")): return 

    try:
        # STEP 1: INSTANT SECURITY CHECK (Pehle hi rok do)
        is_risky, keyword = check_virus_keywords(text)
        if is_risky:
            bot.reply_to(message, 
                f"⚠️ **SUSPICIOUS LINK DETECTED!**\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"🔴 **Link:** {text}\n"
                f"💀 **Keyword:** `{keyword}`\n"
                f"🛑 **Status:** **UNSAFE** (Analysis Stopped)"
            )
            return  # Yahi ruk jao, aage mat badho

        status_msg = bot.send_message(message.chat.id, "🔍 **Scanning...**")
        
        # STEP 2: Unshorten (Agar Safe hai tabhi)
        real_url = get_real_url(text)
        
        # STEP 3: Deep Check (Result Link Check)
        is_risky, keyword = check_virus_keywords(real_url)
        domain = urlparse(real_url).netloc
        
        if is_risky:
            bot.edit_message_text(
                f"⚠️ **HIDDEN THREAT DETECTED!**\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"🔴 **Original:** {text}\n"
                f"💀 **Redirects to:** {real_url}\n"
                f"🛑 **Reason:** Contains keyword `{keyword}`",
                message.chat.id, status_msg.message_id
            )
        else:
            # Result Formatting
            if real_url == text:
                note = "Could not unshorten (Direct/Protected)"
            else:
                note = "Successfully Unshortened"

            bot.edit_message_text(
                f"✅ **Scan Report**\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"🔗 **Real URL:**\n{real_url}\n\n"
                f"🌐 **Domain:** {domain}\n"
                f"ℹ️ **Note:** {note}\n"
                f"🛡 **Status:** ✅ Safe to Click",
                message.chat.id, status_msg.message_id,
                disable_web_page_preview=True
            )
            
            log_to_channel(f"✅ Scan | User: {message.from_user.id} | Domain: {domain}")

    except Exception as e:
        bot.send_message(message.chat.id, f"Error: {e}")

# ---------------------------------------------------------
# 5. SERVER RUN
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
