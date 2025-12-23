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
        # User agent lagana zaroori hai taaki website block na kare
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        
        # Timeout 9 second rakha hai taaki Vercel crash na ho
        response = requests.head(url, allow_redirects=True, headers=headers, timeout=9)
        
        real_url = response.url
        status = response.status_code
        
        return real_url, status
    except requests.exceptions.Timeout:
        return None, "Timeout (Site too slow)"
    except Exception as e:
        return None, str(e)

def is_suspicious(url):
    # Simple check for bad domains (Aap is list ko bada kar sakte hain)
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
        "Mujhe koi bhi Link bhejo, main bataunga ki wo kahan le ja raha hai aur Safe hai ya nahi.\n\n"
        "⚡ **Supports:** bit.ly, tinyurl, t.co, etc."
    )

# Har text message ko check karega ki wo Link hai ya nahi
@bot.message_handler(func=lambda message: True)
def scan_link(message):
    text = message.text.strip()
    
    # Check agar ye URL jaisa dikhta hai
    if not (text.startswith("http://") or text.startswith("https://")):
        # Agar http nahi hai toh user ko ignore karo ya bata do
        return 

    msg = bot.reply_to(message, "🔍 **Scanning Link...**")
    
    real_url, status = unshorten_url(text)
    
    if not real_url:
        bot.edit_message_text(f"❌ **Error:** Link khul nahi raha. ({status})", message.chat.id, msg.message_id)
        return

    # Safety Check
    safety_status = "✅ Safe to Click"
    if is_suspicious(real_url):
        safety_status = "⚠️ **SUSPICIOUS / RISKY**"
    
    # Domain Name nikalo
    domain = urlparse(real_url).netloc

    output = (
        f"🕵️‍♂️ **LINK REVEALED**\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"🔴 **Short Link:** {text}\n"
        f"🟢 **Real Destination:**\n`{real_url}`\n\n"
        f"🌐 **Domain:** {domain}\n"
        f"🛡️ **Status:** {safety_status}"
    )
    
    # Disable web page preview taaki user galti se click na kare agar virus ho
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
