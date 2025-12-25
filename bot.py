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
# 2. THE ULTIMATE UNSHORTENER ENGINE (5 LAYERS)
# ---------------------------------------------------------
def log_to_channel(text):
    if not LOG_CHANNEL_ID: return
    try:
        bot.send_message(int(LOG_CHANNEL_ID), text)
    except: pass

def get_real_url(url):
    # --- LAYER 1: Standard Request (Direct Check) ---
    try:
        session = requests.Session()
        headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36",
            "Referer": "https://www.google.com/"
        }
        response = session.get(url, headers=headers, timeout=4, allow_redirects=True, verify=False)
        if response.url != url and "bit.ly" not in response.url and response.url.startswith("http"):
            return response.url
    except: pass

    # --- LAYER 2: ExpandURL API (New & Powerful) ---
    try:
        # Yeh seedha text return karta hai, koi scraping nahi chahiye
        api_url = f"http://expandurl.com/api/v1/?url={url}"
        r = requests.get(api_url, timeout=6)
        if r.status_code == 200 and r.text.startswith("http"):
            return r.text.strip()
    except: pass

    # --- LAYER 3: Unshorten.me API ---
    try:
        api_url = f"https://unshorten.me/json/{url}"
        r = requests.get(api_url, timeout=5).json()
        if r['success'] and r['resolved_url'] and r['resolved_url'].startswith("http"):
            return r['resolved_url']
    except: pass

    # --- LAYER 4: Proxy Scraper (CheckShortURL) ---
    try:
        check_url = f"http://checkshorturl.com/expand.php?u={url}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(check_url, headers=headers, timeout=8).text
        
        # Improved Regex to find valid http link
        match = re.search(r'Long URL.*?href="(http.*?)"', response, re.DOTALL)
        if match and match.group(1):
            return match.group(1)
    except: pass

    # --- LAYER 5: Fallback (Urllib) ---
    try:
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X)"}
        )
        with urllib.request.urlopen(req, timeout=4) as response:
            final_url = response.geturl()
            if final_url != url and "bit.ly" not in final_url:
                return final_url
    except: pass

    # Agar sab fail ho jaye, toh Original wapas karo (Lekin empty nahi)
    return url

def check_virus_keywords(url):
    bad_keywords = ['hack', 'free-money', 'steal', 'login', 'verify', 'account-update', 'ngrok', 'crypto']
    if not url: return False, None # Safety check for empty url
    
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
        bot.send_message(message.chat.id, "**Deep Link Scanner v5.0** (Bug Fixed)")
    except: pass

@bot.message_handler(func=lambda m: True)
def scan_link(message):
    text = message.text.strip()
    if not (text.startswith("http://") or text.startswith("https://")): return 

    try:
        status_msg = bot.send_message(message.chat.id, "🔍 **Digging Deep...**")
        
        # Engine Call
        real_url = get_real_url(text)
        
        # ANALYSIS LOGIC (Crucial Fix)
        if not real_url or real_url == text:
            # Agar URL change nahi hua ya empty aaya
            bot.edit_message_text(
                f"✅ **Scan Report**\n"
                f"🔗 **Link:** {text}\n"
                f"⚠️ **Note:** Could not unshorten (Protected/Direct Link).\n"
                f"🛡️ **Status:** Seemingly Safe",
                message.chat.id, status_msg.message_id,
                disable_web_page_preview=True
            )
            return

        # Agar Unshorten Success Hua:
        is_risky, keyword = check_virus_keywords(real_url)
        domain = urlparse(real_url).netloc
        
        if is_risky:
            bot.edit_message_text(
                f"⚠️ **SUSPICIOUS LINK DETECTED!**\n"
                f"🔴 Input: {text}\n"
                f"💀 Keyword: `{keyword}`\n"
                f"🛑 Status: UNSAFE",
                message.chat.id, status_msg.message_id
            )
        else:
            bot.edit_message_text(
                f"✅ **Link Revealed**\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"🔴 **Short:** {text}\n"
                f"🟢 **Real:**\n{real_url}\n\n"
                f"🌐 **Domain:** {domain}\n"
                f"🛡️ **Status:** ✅ Safe to Click",
                message.chat.id, status_msg.message_id,
                disable_web_page_preview=True
            )
            
        log_to_channel(f"✅ Success | User: {message.from_user.id} | Domain: {domain}")

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
