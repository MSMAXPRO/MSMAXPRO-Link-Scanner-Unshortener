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

# Connection to Unified Log Channel
LOG_CHANNEL_ID = os.environ.get('LOG_CHANNEL_ID') 
# Emergency Brake
MAINTENANCE_MODE = os.environ.get('MAINTENANCE_MODE', 'False')

# Offset for 1 Million Limit Correction
STARTING_OFFSET = 1700 

bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

# ---------------------------------------------------------
# 2. TRACKING & STATS (Ab Refresh Button ke saath)
# ---------------------------------------------------------

def track_activity(message):
    """Logs activity safely to Log Channel."""
    if not LOG_CHANNEL_ID: return
    try:
        channel_id_int = int(LOG_CHANNEL_ID)
        bot_name = bot.get_me().first_name
        # Log entry
        bot.send_message(channel_id_int, f"🕵️‍♂️ Hit from {bot_name} | User: {message.from_user.id}")
    except Exception as e:
        print(f"Tracking Error: {e}")
        pass

# [UPDATED] Stats Command with Refresh Button
@bot.message_handler(commands=['stats'])
def stats_command(message):
    try:
        if not LOG_CHANNEL_ID:
            bot.reply_to(message, "⚠️ Log Channel ID missing.")
            return

        channel_id_int = int(LOG_CHANNEL_ID)
        active_users = bot.get_chat_member_count(channel_id_int)
        
        # Sync Logic
        temp_msg = bot.send_message(channel_id_int, "Syncing Global Stats...")
        current_logs = temp_msg.message_id - 1
        total_requests = current_logs + STARTING_OFFSET
        bot.delete_message(channel_id_int, temp_msg.message_id)
        
        LIMIT = 1000000 
        remaining = LIMIT - total_requests
        percent = (total_requests / LIMIT) * 100
        
        text = (
            f"📊 **Global Network Stats (View from LinkScanner)**\n\n"
            f"👥 **Unique Users:** {active_users}\n"
            f"🔄 **Total Requests:** {total_requests:,}\n"
            f"⚠️ **Network Limit:** 1,000,000\n"
            f"✅ **Remaining:** {remaining:,}\n\n"
            f"📈 **Load:** {percent:.4f}%\n"
            f"🕒 Updated: `{datetime.now().strftime('%H:%M:%S')}`"
        )
        
        # Manual Refresh Button
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("🔄 Refresh Network Stats", callback_data="refresh_stats"))
        
        bot.reply_to(message, text, parse_mode="Markdown", reply_markup=markup)
    except Exception as e:
        bot.reply_to(message, f"⚠️ Error: {e}")

# [ADDED] Callback Handler for Refresh
@bot.callback_query_handler(func=lambda call: call.data == "refresh_stats")
def refresh_callback(call):
    try:
        # Pura logic dobara run karne ki bajaye hum seedha function call kar rahe hain
        # Lekin edit karne ke liye hum message delete karke naya bhej sakte hain ya edit kar sakte hain
        # Simple tareeka: User ko naya stats dikha do ya message edit karo (yahan hum edit try karte hain)
        
        if not LOG_CHANNEL_ID: return

        channel_id_int = int(LOG_CHANNEL_ID)
        active_users = bot.get_chat_member_count(channel_id_int)
        
        temp_msg = bot.send_message(channel_id_int, "Syncing...")
        current_logs = temp_msg.message_id - 1
        total_requests = current_logs + STARTING_OFFSET
        bot.delete_message(channel_id_int, temp_msg.message_id)
        
        LIMIT = 1000000
        remaining = LIMIT - total_requests
        percent = (total_requests / LIMIT) * 100
        
        text = (
            f"📊 **Global Network Stats (View from LinkScanner)**\n\n"
            f"👥 **Unique Users:** {active_users}\n"
            f"🔄 **Total Requests:** {total_requests:,}\n"
            f"⚠️ **Network Limit:** 1,000,000\n"
            f"✅ **Remaining:** {remaining:,}\n\n"
            f"📈 **Load:** {percent:.4f}%\n"
            f"🕒 Updated: `{datetime.now().strftime('%H:%M:%S')}`"
        )
        
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("🔄 Refresh Network Stats", callback_data="refresh_stats"))
        
        bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=markup)
        bot.answer_callback_query(call.id, "Stats Refreshed!")
    except: 
        bot.answer_callback_query(call.id, "Error Refreshing")

# ---------------------------------------------------------
# 3. UNSHORTENER LOGIC
# ---------------------------------------------------------
def unshorten_url(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.head(url, allow_redirects=True, headers=headers, timeout=9)
        return response.url, response.status_code
    except requests.exceptions.Timeout:
        return None, "Timeout"
    except Exception as e:
        return None, str(e)

def is_suspicious(url):
    bad_keywords = ['hack', 'free-money', 'steal', 'login-verify', 'ngrok']
    for word in bad_keywords:
        if word in url.lower(): return True
    return False

# ---------------------------------------------------------
# 4. BOT COMMANDS
# ---------------------------------------------------------

@bot.message_handler(func=lambda m: MAINTENANCE_MODE == 'True')
def maintenance_msg(message):
    bot.reply_to(message, "⚠️ **Maintenance Mode Active.**")
    return

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    track_activity(message) 
    bot.reply_to(message, 
        "🕵️‍♂️ **MSMAXPRO Link Scanner**\n\n"
        "Send me any Link to reveal its real destination.\n"
        "⚡ **Supports:** bit.ly, tinyurl, t.co, etc."
    )

@bot.message_handler(func=lambda message: True)
def scan_link(message):
    text = message.text.strip()
    if not (text.startswith("http://") or text.startswith("https://")): return 

    track_activity(message) 

    msg = bot.reply_to(message, "🔍 **Scanning...**")
    
    real_url, status = unshorten_url(text)
    
    if not real_url:
        bot.edit_message_text(f"❌ **Error:** Could not open link. ({status})", message.chat.id, msg.message_id)
        return

    safety_status = "✅ Safe to Click"
    if is_suspicious(real_url): safety_status = "⚠️ **SUSPICIOUS**"
    
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
# 5. SERVER SETUP
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
