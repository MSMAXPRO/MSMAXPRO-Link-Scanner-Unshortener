import telebot
import os
import requests
from urllib.parse import urlparse
from flask import Flask, request, Response

# ---------------------------------------------------------
# 1. CONFIGURATION
# ---------------------------------------------------------
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
ADMIN_ID = os.environ.get('ADMIN_ID')
bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

# ---------------------------------------------------------
# 2. UNSHORTENER LOGIC
# ---------------------------------------------------------
def unshorten_url(url):
    try:
        # User agent is crucial to avoid being blocked by websites
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        
        # Timeout 9 seconds to fit within Vercel's limit
        response = requests.head(url, allow_redirects=True, headers=headers, timeout=9)
        
        real_url = response.url
        status = response.status_code
        
        return real_url, status
    except requests.exceptions.Timeout:
        return None, "Timeout (Site too slow)"
    except Exception as e:
        return None, str(e)

def is_suspicious(url):
    # Simple check for bad keywords (You can add more)
    # Note: 'hack' is added for testing purposes (e.g., hackthebox)
    bad_keywords = ['hack', 'free-money', 'steal', 'login-verify', 'ngrok']
    for word in bad_keywords:
        if word in url.lower():
            return True
    return False

# ---------------------------------------------------------
# 3. BOT COMMANDS
# ---------------------------------------------------------
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, 
        "🕵️‍♂️ **MSMAXPRO Link Scanner**\n\n"
        "Send me any Link, and I will reveal its real destination and check if it is Safe.\n\n"
        "⚡ **Supports:** bit.ly, tinyurl, t.co, etc."
    )

# Logic to scan every text message
@bot.message_handler(func=lambda message: True)
def scan_link(message):
    text = message.text.strip()
    
    # Check if the text looks like a URL
    if not (text.startswith("http://") or text.startswith("https://")):
        # Ignore non-link messages
        return 

    msg = bot.reply_to(message, "🔍 **Scanning Link...**")
    
    real_url, status = unshorten_url(text)
    
    if not real_url:
        bot.edit_message_text(f"❌ **Error:** Could not open link. ({status})", message.chat.id, msg.message_id)
        return

    # Safety Check
    safety_status = "✅ Safe to Click"
    if is_suspicious(real_url):
        safety_status = "⚠️ **SUSPICIOUS / RISKY**"
    
    # Extract Domain Name
    domain = urlparse(real_url).netloc

    output = (
        f"🕵️‍♂️ **LINK REVEALED**\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"🔴 **Short Link:** {text}\n"
        f"🟢 **Real Destination:**\n`{real_url}`\n\n"
        f"🌐 **Domain:** {domain}\n"
        f"🛡️ **Status:** {safety_status}"
    )
    
    # Disable web page preview to prevent accidental clicks on bad links
    bot.delete_message(message.chat.id, msg.message_id)
    bot.send_message(message.chat.id, output, parse_mode="Markdown", disable_web_page_preview=True)

# ---------------------------------------------------------
# 4. SERVER SETUP
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
