import os
import subprocess
import sqlite3
import telebot
import threading
import time
import uuid
import signal
import random
import platform
import zipfile
import json
import shutil
import schedule
from pathlib import Path
from telebot import types
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from flask import Flask, send_file, jsonify

# ================== Configuration ==================
class Config:
    TOKEN = os.environ.get('BOT_TOKEN', '8754448627:AAFReyCErlSnESaSJOUzAt1Ut-n95w_xWDI')
    ADMIN_ID = int(os.environ.get('ADMIN_ID', 6487613131))
    PROJECT_DIR = 'projects'
    DB_NAME = 'cyber_v2.db'
    PORT = int(os.environ.get('PORT', 10000))
    MAINTENANCE = False
    
    ADMIN_USERNAME = 'aurponmodz' 
    BOT_USERNAME = "@aurpon_bot_host_bot" 
    SUPPORT_ID = "@aurponmodz" 
    BRAND_NAME = "💎𝐀𝐔𝐑𝐏𝐎𝐍💎" 
    
    MAX_FILE_SIZE = 5.5 * 1024 * 1024 

bot = telebot.TeleBot(Config.TOKEN, parse_mode="HTML")
project_path = Path(Config.PROJECT_DIR)
project_path.mkdir(exist_ok=True)
app = Flask(__name__)

# ================== Admin Security Check ==================
# এই ডেকোরেটরটি নিশ্চিত করবে যে অন্য কেউ মেসেজ দিলে বট কোনো উত্তর দিবে না
@bot.message_handler(func=lambda message: message.from_user.id != Config.ADMIN_ID)
def ignore_others(message):
    return # কোনো রিপ্লাই দিবে না, সবাই ভাববে বট অফলাইন।

# ================== Database Functions ==================
def init_db():
    conn = sqlite3.connect(Config.DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                (id INTEGER PRIMARY KEY, username TEXT, expiry TEXT, file_limit INTEGER, 
                 is_prime INTEGER, join_date TEXT, last_renewal TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS keys 
                (key TEXT PRIMARY KEY, duration_days INTEGER, file_limit INTEGER, created_date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS deployments 
                (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, bot_name TEXT, 
                 filename TEXT, pid INTEGER, start_time TEXT, status TEXT, 
                 cpu_usage REAL, ram_usage REAL, last_active TEXT)''')
    
    join_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    expiry_date = (datetime.now() + timedelta(days=3650)).strftime('%Y-%m-%d %H:%M:%S')
    c.execute("INSERT OR IGNORE INTO users VALUES (?, ?, ?, ?, ?, ?, ?)", 
             (Config.ADMIN_ID, 'admin', expiry_date, 100, 1, join_date, join_date))
    conn.commit()
    conn.close()

init_db()

# ================== Helper Functions ==================
def get_user(user_id):
    conn = sqlite3.connect(Config.DB_NAME)
    c = conn.cursor()
    user = c.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    return user

def is_prime(user_id):
    user = get_user(user_id)
    if user and user[2]:
        try:
            expiry = datetime.strptime(user[2], '%Y-%m-%d %H:%M:%S')
            return expiry > datetime.now()
        except:
            return False
    return False

def get_user_bots(user_id):
    conn = sqlite3.connect(Config.DB_NAME)
    c = conn.cursor()
    bots = c.execute("SELECT id, bot_name, filename, pid, start_time, status FROM deployments WHERE user_id=?", (user_id,)).fetchall()
    conn.close()
    return bots

def create_progress_bar(percentage):
    bars = int(percentage / 10)
    return "🔵" * bars + "⚪" * (10 - bars)

def get_system_stats():
    return {
        'cpu_percent': random.randint(10, 60),
        'ram_percent': random.randint(20, 70),
        'disk_percent': random.randint(30, 80)
    }

def create_zip_file(bot_id, bot_name, filename, user_id):
    try:
        export_dir = Path('exports')
        export_dir.mkdir(exist_ok=True)
        zip_filename = f"bot_export_{bot_id}_{int(time.time())}.zip"
        zip_path = export_dir / zip_filename
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            bot_file_path = project_path / filename
            if bot_file_path.exists():
                zipf.write(bot_file_path, arcname=filename)
            metadata = {
                'bot_id': bot_id, 'bot_name': bot_name, 'filename': filename, 'user_id': user_id,
                'export_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'version': '3.0.1'
            }
            zipf.writestr('metadata.json', json.dumps(metadata, indent=4))
        return zip_path
    except Exception as e:
        return None

def check_prime_expiry(user_id):
    user = get_user(user_id)
    if user and user[2]:
        try:
            expiry = datetime.strptime(user[2], '%Y-%m-%d %H:%M:%S')
            now = datetime.now()
            if expiry > now:
                days_left = (expiry - now).days
                return {'expired': False, 'days_left': days_left, 'expiry_date': expiry.strftime('%Y-%m-%d %H:%M:%S')}
            else:
                return {'expired': True, 'expiry_date': expiry.strftime('%Y-%m-%d %H:%M:%S'), 'message': 'Expired'}
        except:
            return {'expired': True, 'message': 'Invalid expiry'}
    return {'expired': True, 'message': 'No Prime'}

# ================== Keyboards ==================
def main_menu_reply(user_id):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = types.KeyboardButton("📤 𝗨𝗽𝗹𝗼𝗮𝗱 𝗕𝗼𝘁 𝗙𝗶𝗹𝗲")
    btn2 = types.KeyboardButton("🤖 𝗠𝘆 𝗕𝗼𝘁𝘀 𝗟𝗶𝘀𝘁")
    btn3 = types.KeyboardButton("🚀 𝗗𝗲𝗽𝗹𝗼𝘆 𝗡𝗲𝘄 𝗕𝗼𝘁")
    btn4 = types.KeyboardButton("📊 𝗗𝗮𝘀𝗵𝗯𝗼𝗮𝗿𝗱")
    markup.add(btn1, btn2, btn3, btn4)
    return markup

# ================== Command Handlers ==================
@bot.message_handler(commands=['start'])
def welcome(message):
    uid = message.from_user.id
    username = message.from_user.username or "Admin"
    user = get_user(uid)
    
    prime_status = check_prime_expiry(uid)
    status = "👑 𝗣𝗥𝗜𝗠𝗘 𝗔𝗗𝗠𝗜𝗡"
    
    text = f"""
✨ <b>{Config.BRAND_NAME}</b> ✨
<b>━━━━━━━━━━━━━━━━━━━━━━</b>
👤 <b>𝗨𝘀𝗲𝗿: @{username}</b>
🆔 <b>𝗜𝗗:</b> <code>{uid}</code>
💎 <b>𝗦𝘁𝗮𝘁𝘂𝘀: {status}</b>
📅 <b>𝗝𝗼𝗶𝗻 𝗗𝗮𝘁𝗲: {user[5]}</b>
<b>━━━━━━━━━━━━━━━━━━━━━━</b>
📊 <b>𝗔𝗰𝗰𝗼𝘂𝗻𝘁 𝗗𝗲𝘁𝗮𝗶𝗹𝘀:</b>
• <b>𝗣𝗹𝗮𝗻: Premium</b>
• <b>𝗙𝗶𝗹𝗲 𝗟𝗶𝗺𝗶𝘁:</b> <code>{user[3]}</code> <b>files</b>
• <b>𝗘𝘅𝗽𝗶𝗿𝘆: Lifetime (Admin Access)</b>
<b>━━━━━━━━━━━━━━━━━━━━━━</b>
"""
    bot.send_message(message.chat.id, text, reply_markup=main_menu_reply(uid))

@bot.message_handler(func=lambda message: message.text == "🏠 𝗠𝗮𝗶𝗻 𝗠𝗲𝗻𝘂")
def back_to_main(message):
    welcome(message)

@bot.message_handler(func=lambda message: message.text == "📤 𝗨𝗽𝗹𝗼𝗮𝗱 𝗕𝗼𝘁 𝗙𝗶𝗹𝗲")
def upload_handler(message):
    msg = bot.reply_to(message, "<b>📤 𝗨𝗣𝗟𝗢𝗔𝗗 𝗕𝗢𝗧 𝗙𝗜𝗟𝗘</b>\n<b>━━━━━━━━━━━━━━━━━━━━━━</b>\n<b>𝗣𝗹𝗲𝗮𝘀𝗲 𝘀𝗲𝗻𝗱 𝘆𝗼𝘂𝗿 .𝗽𝘆 𝗼𝗿 .𝘇𝗶𝗽 𝗳𝗶𝗹𝗲 (𝗠𝗮𝘅 𝟱.𝟱𝗠𝗕).</b>")
    bot.register_next_step_handler(msg, upload_file_step)

def upload_file_step(message):
    uid = message.from_user.id
    chat_id = message.chat.id
    if message.content_type == 'document':
        try:
            file_name = message.document.file_name.lower()
            if not (file_name.endswith('.py') or file_name.endswith('.zip')):
                bot.send_message(chat_id, "<b>❌ 𝗢𝗻𝗹𝘆 𝗣𝘆𝘁𝗵𝗼𝗻 (.𝗽𝘆) 𝗼𝗿 𝗭𝗜𝗣 (.𝘇𝗶𝗽) 𝗳𝗶𝗹𝗲𝘀 𝗮𝗹𝗹𝗼𝘄𝗲𝗱.</b>")
                return
            
            bot.send_message(chat_id, "<b>📥 𝗗𝗼𝘄𝗻𝗹𝗼𝗮𝗱𝗶𝗻𝗴 𝗳𝗶𝗹𝗲...</b>")
            file_info = bot.get_file(message.document.file_id)
            downloaded = bot.download_file(file_info.file_path)
            
            safe_name = secure_filename(message.document.file_name)
            file_path = project_path / safe_name
            file_path.write_bytes(downloaded)
            
            msg = bot.send_message(chat_id, "<b>🤖 𝗘𝗻𝘁𝗲𝗿 𝗮 𝗻𝗮𝗺𝗲 𝗳𝗼𝗿 𝘆𝗼𝘂𝗿 𝗯𝗼𝘁:</b>")
            bot.register_next_step_handler(msg, save_bot_name, safe_name)
        except Exception as e:
            bot.send_message(chat_id, f"<b>❌ 𝗘𝗿𝗿𝗼𝗿: {str(e)}</b>")
    else:
        bot.send_message(chat_id, "<b>❌ 𝗣𝗹𝗲𝗮𝘀𝗲 𝘀𝗲𝗻𝗱 𝗮 𝘃𝗮𝗹𝗶𝗱 𝗳𝗶𝗹𝗲.</b>")

def save_bot_name(message, safe_name):
    uid = message.from_user.id
    bot_name = message.text.strip()[:50]
    conn = sqlite3.connect(Config.DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO deployments (user_id, bot_name, filename, pid, start_time, status, last_active) VALUES (?, ?, ?, ?, ?, ?, ?)",
             (uid, bot_name, safe_name, 0, None, "Uploaded", datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    conn.close()
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📚 𝗜𝗻𝘀𝘁𝗮𝗹𝗹 𝗟𝗶𝗯𝗿𝗮𝗿𝗶𝗲𝘀", "🤖 𝗠𝘆 𝗕𝗼𝘁𝘀 𝗟𝗶𝘀𝘁", "🏠 𝗠𝗮𝗶𝗻 𝗠𝗲𝗻𝘂")
    bot.send_message(message.chat.id, f"<b>✅ 𝗕𝗼𝘁 '{bot_name}' 𝘂𝗽𝗹𝗼𝗮𝗱𝗲𝗱! 𝗖𝗹𝗶𝗰𝗸 𝗯𝗲𝗹𝗼𝘄 𝘁𝗼 𝗶𝗻𝘀𝘁𝗮𝗹𝗹 𝗹𝗶𝗯𝗿𝗮𝗿𝗶𝗲𝘀.</b>", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "📚 𝗜𝗻𝘀𝘁𝗮𝗹𝗹 𝗟𝗶𝗯𝗿𝗮𝗿𝗶𝗲𝘀")
def ask_for_libraries(message):
    msg = bot.reply_to(message, "<b>📚 𝗜𝗡𝗦𝗧𝗔𝗟𝗟 𝗟𝗜𝗕𝗥𝗔𝗥𝗜𝗘𝗦</b>\n<b>𝗘𝗻𝘁𝗲𝗿 𝗹𝗶𝗯𝗿𝗮𝗿𝘆 𝗰𝗼𝗺𝗺𝗮𝗻𝗱𝘀 (𝗲.𝗴., 𝗽𝗶𝗽 𝗶𝗻𝘀𝘁𝗮𝗹𝗹 𝗿𝗲𝗾𝘂𝗲𝘀𝘁𝘀).</b>")
    bot.register_next_step_handler(msg, install_libraries_step)

def install_libraries_step(message):
    commands = [cmd.strip() for cmd in message.text.strip().split('\n') if cmd.strip()]
    bot.send_message(message.chat.id, "<b>🛠 𝗜𝗻𝘀𝘁𝗮𝗹𝗹𝗶𝗻𝗴 𝗹𝗶𝗯𝗿𝗮𝗿𝗶𝗲𝘀... 𝗣𝗹𝗲𝗮𝘀𝗲 𝘄𝗮𝗶𝘁.</b>")
    results = []
    for cmd in commands:
        if "pip install" in cmd:
            res = subprocess.run(cmd.split(), capture_output=True, text=True)
            results.append(f"<b>✅ {cmd}</b>" if res.returncode == 0 else f"<b>❌ {cmd} 𝗙𝗮𝗶𝗹𝗲𝗱</b>")
    bot.send_message(message.chat.id, "<b>📊 𝗜𝗻𝘀𝘁𝗮𝗹𝗹𝗮𝘁𝗶𝗼𝗻 𝗥𝗲𝘀𝘂𝗹𝘁:</b>\n" + "\n".join(results))

@bot.message_handler(func=lambda message: message.text == "🤖 𝗠𝘆 𝗕𝗼𝘁𝘀 𝗟𝗶𝘀𝘁")
def show_my_bots_reply(message):
    uid = message.from_user.id
    bots = get_user_bots(uid)
    if not bots:
        bot.reply_to(message, "<b>🤖 𝗡𝗼 𝗯𝗼𝘁𝘀 𝗳𝗼𝘂𝗻𝗱 𝗶𝗻 𝘆𝗼𝘂𝗿 𝗹𝗶𝘀𝘁.</b>")
        return
    text = "<b>🤖 𝗠𝗬 𝗗𝗘𝗣𝗟𝗢𝗬𝗘𝗗 𝗕𝗢𝗧𝗦:</b>\n<b>━━━━━━━━━━━━━━━━━━━━━━</b>\n"
    for idx, b in enumerate(bots, 1):
        status = "🟢" if b[5] == "Running" else "🔴"
        text += f"<b>{idx}. {status} {b[1]}</b>\n"
    msg = bot.reply_to(message, text + "\n<b>𝗘𝗻𝘁𝗲𝗿 𝗯𝗼𝘁 𝗻𝘂𝗺𝗯𝗲𝗿 𝘁𝗼 𝘃𝗶𝗲𝘄 𝗱𝗲𝘁𝗮𝗶𝗹𝘀.</b>")
    bot.register_next_step_handler(msg, process_bot_selection, bots)

def process_bot_selection(message, bots):
    try:
        choice = int(message.text.strip())
        bot_id = bots[choice-1][0]
        show_bot_details(message, bot_id)
    except:
        bot.send_message(message.chat.id, "<b>❌ 𝗜𝗻𝘃𝗮𝗹𝗶𝗱 𝘀𝗲𝗹𝗲𝗰𝘁𝗶𝗼𝗻.</b>")

def show_bot_details(message, bot_id):
    conn = sqlite3.connect(Config.DB_NAME)
    c = conn.cursor()
    bot_info = c.execute("SELECT * FROM deployments WHERE id=?", (bot_id,)).fetchone()
    conn.close()
    if not bot_info: return
    
    text = f"""
<b>🤖 𝗕𝗢𝗧 𝗖𝗢𝗡𝗧𝗥𝗢𝗟 𝗣𝗔𝗡𝗘𝗟</b>
<b>━━━━━━━━━━━━━━━━━━━━━━</b>
<b>𝗡𝗮𝗺𝗲: {bot_info[2]}</b>
<b>𝗙𝗶𝗹𝗲:</b> <code>{bot_info[3]}</code>
<b>𝗦𝘁𝗮𝘁𝘂𝘀: {bot_info[6]}</b>
<b>𝗦𝘁𝗮𝗿𝘁𝗲𝗱: {bot_info[5] or "N/A"}</b>
<b>━━━━━━━━━━━━━━━━━━━━━━</b>
<b>𝗔𝗰𝘁𝗶𝗼𝗻𝘀: /stop_{bot_id} | /delete_{bot_id} | /export_{bot_id}</b>
"""
    bot.send_message(message.chat.id, text)

@bot.message_handler(regexp=r'^/(stop|delete|export)_(\d+)$')
def handle_bot_actions(message):
    action = message.text.split('_')[0][1:]
    bot_id = message.text.split('_')[1]
    uid = message.from_user.id
    
    conn = sqlite3.connect(Config.DB_NAME)
    c = conn.cursor()
    bot_info = c.execute("SELECT pid, user_id, filename, bot_name FROM deployments WHERE id=?", (bot_id,)).fetchone()
    
    if not bot_info or bot_info[1] != uid:
        bot.reply_to(message, "<b>❌ 𝗔𝗰𝗰𝗲𝘀𝘀 𝗗𝗲𝗻𝗶𝗲𝗱!</b>")
        conn.close()
        return

    if action == "stop":
        if bot_info[0]:
            try: os.kill(bot_info[0], signal.SIGTERM)
            except: pass
        c.execute("UPDATE deployments SET status='Stopped', pid=0 WHERE id=?", (bot_id,))
        bot.reply_to(message, "<b>✅ 𝗕𝗼𝘁 𝗦𝘁𝗼𝗽𝗽𝗲𝗱 𝗦𝘂𝗰𝗰𝗲𝘀𝘀𝗳𝘂𝗹𝗹𝘆!</b>")
    
    elif action == "delete":
        if bot_info[0]:
            try: os.kill(bot_info[0], signal.SIGKILL)
            except: pass
        file_path = project_path / bot_info[2]
        if file_path.exists(): file_path.unlink()
        c.execute("DELETE FROM deployments WHERE id=?", (bot_id,))
        bot.reply_to(message, "<b>✅ 𝗕𝗼𝘁 𝗗𝗲𝗹𝗲𝘁𝗲𝗱 𝗳𝗿𝗼𝗺 𝗦𝗲𝗿𝘃𝗲𝗿!</b>")

    elif action == "export":
        zip_path = create_zip_file(bot_id, bot_info[3], bot_info[2], uid)
        if zip_path:
            with open(zip_path, 'rb') as f:
                bot.send_document(message.chat.id, f, caption=f"<b>📦 𝗘𝘅𝗽𝗼𝗿𝘁𝗲𝗱 𝗕𝗼𝘁: {bot_info[3]}</b>")
            zip_path.unlink()
    
    conn.commit()
    conn.close()

@bot.message_handler(func=lambda message: message.text == "🚀 𝗗𝗲𝗽𝗹𝗼𝘆 𝗡𝗲𝘄 𝗕𝗼𝘁")
def deploy_new_handler(message):
    uid = message.from_user.id
    conn = sqlite3.connect(Config.DB_NAME)
    c = conn.cursor()
    files = c.execute("SELECT id, bot_name, filename FROM deployments WHERE user_id=? AND (pid=0 OR pid IS NULL)", (uid,)).fetchall()
    conn.close()
    if not files:
        bot.reply_to(message, "<b>📭 𝗡𝗼 𝗳𝗶𝗹𝗲𝘀 𝗮𝘃𝗮𝗶𝗹𝗮𝗯𝗹𝗲 𝗳𝗼𝗿 𝗱𝗲𝗽𝗹𝗼𝘆𝗺𝗲𝗻𝘁.</b>")
        return
    text = "<b>🚀 𝗦𝗲𝗹𝗲𝗰𝘁 𝗮 𝗯𝗼𝘁 𝘁𝗼 𝗱𝗲𝗽𝗹𝗼𝘆:</b>\n"
    for idx, f in enumerate(files, 1):
        text += f"<b>{idx}. {f[1]} (<code>{f[2]}</code>)</b>\n"
    msg = bot.reply_to(message, text)
    bot.register_next_step_handler(msg, process_deploy_selection, files)

def process_deploy_selection(message, files):
    try:
        choice = int(message.text.strip())
        bot_id, bot_name, filename = files[choice-1]
        
        progress_msg = bot.send_message(message.chat.id, f"<b>🚀 𝗗𝗲𝗽𝗹𝗼𝘆𝗶𝗻𝗴 {bot_name}... 𝗣𝗹𝗲𝗮𝘀𝗲 𝘄𝗮𝗶𝘁.</b>")
        file_path = project_path / filename
        start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        proc = subprocess.Popen(['python', str(file_path)], start_new_session=True)
        
        conn = sqlite3.connect(Config.DB_NAME)
        c = conn.cursor()
        c.execute("UPDATE deployments SET pid=?, start_time=?, status='Running' WHERE id=?", (proc.pid, start_time, bot_id))
        conn.commit()
        conn.close()
        bot.edit_message_text(f"<b>✅ {bot_name} 𝗶𝘀 𝗻𝗼𝘄 𝗥𝗨𝗡𝗡𝗜𝗡𝗚!</b>\n<b>𝗣𝗜𝗗:</b> <code>{proc.pid}</code>", message.chat.id, progress_msg.message_id)
    except Exception as e:
        bot.send_message(message.chat.id, f"<b>❌ 𝗗𝗲𝗽𝗹𝗼𝘆𝗺𝗲𝗻𝘁 𝗳𝗮𝗶𝗹𝗲𝗱: {e}</b>")

@bot.message_handler(func=lambda message: message.text == "📊 𝗗𝗮𝘀𝗵𝗯𝗼𝗮𝗿𝗱")
def show_dashboard_reply(message):
    uid = message.from_user.id
    user = get_user(uid)
    stats = get_system_stats()
    text = f"""
<b>📊 𝗦𝗬𝗦𝗧𝗘𝗠 𝗗𝗔𝗦𝗛𝗕𝗢𝗔𝗥𝗗</b>
<b>━━━━━━━━━━━━━━━━━━━━━━</b>
👤 <b>𝗔𝗰𝗰𝗼𝘂𝗻𝘁: 👑 𝗣𝗥𝗜𝗠𝗘 𝗔𝗗𝗠𝗜𝗡</b>
📦 <b>𝗙𝗶𝗹𝗲 𝗟𝗶𝗺𝗶𝘁: {user[3]} 𝗳𝗶𝗹𝗲𝘀</b>
<b>━━━━━━━━━━━━━━━━━━━━━━</b>
🖥️ <b>𝗦𝗲𝗿𝘃𝗲𝗿 𝗦𝘁𝗮𝘁𝘂𝘀:</b>
• <b>𝗖𝗣𝗨: {create_progress_bar(stats['cpu_percent'])} {stats['cpu_percent']}%</b>
• <b>𝗥𝗔𝗠: {create_progress_bar(stats['ram_percent'])} {stats['ram_percent']}%</b>
<b>━━━━━━━━━━━━━━━━━━━━━━</b>
"""
    bot.send_message(message.chat.id, text)

# ================== Flask & Polling ==================
@app.route('/')
def home():
    return {"status": "online", "brand": Config.BRAND_NAME}

def start_bot():
    print("🤖 Bot is starting for Admin Only...")
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except:
            time.sleep(5)

if __name__ == '__main__':
    threading.Thread(target=start_bot, daemon=True).start()
    app.run(host='0.0.0.0', port=Config.PORT))''')

cursor.execute('''CREATE TABLE IF NOT EXISTS bots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    bot_name TEXT,
    filename TEXT,
    pid INTEGER,
    status TEXT,
    start_time TEXT,
    deploy_count INTEGER DEFAULT 0
)''')

# Add admin
cursor.execute("INSERT OR IGNORE INTO users VALUES (?, ?, ?, ?, ?, ?)",
              (ADMIN_ID, 'admin', datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 999999, 1, 0))
conn.commit()

# ==================== FUNCTIONS ====================
def get_user(user_id):
    cursor.execute("SELECT * FROM users WHERE id=?", (user_id,))
    return cursor.fetchone()

def get_user_bots(user_id):
    cursor.execute("SELECT * FROM bots WHERE user_id=? ORDER BY id DESC", (user_id,))
    return cursor.fetchall()

def get_all_users():
    cursor.execute("SELECT id, username, credits, is_banned FROM users ORDER BY id DESC")
    return cursor.fetchall()

def get_all_bots():
    cursor.execute("SELECT b.*, u.username FROM bots b LEFT JOIN users u ON b.user_id = u.id ORDER BY b.id DESC")
    return cursor.fetchall()

def add_bot(user_id, bot_name, filename):
    cursor.execute("INSERT INTO bots (user_id, bot_name, filename, status) VALUES (?, ?, ?, ?)",
                  (user_id, bot_name, filename, "Uploaded"))
    conn.commit()
    return cursor.lastrowid

def update_bot_status(bot_id, status, pid=None):
    if pid:
        cursor.execute("UPDATE bots SET status=?, pid=?, start_time=? WHERE id=?",
                      (status, pid, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), bot_id))
    else:
        cursor.execute("UPDATE bots SET status=? WHERE id=?", (status, bot_id))
    conn.commit()

def delete_bot(bot_id):
    cursor.execute("DELETE FROM bots WHERE id=?", (bot_id,))
    conn.commit()

def add_credits(user_id, amount):
    cursor.execute("UPDATE users SET credits=credits+? WHERE id=?", (amount, user_id))
    conn.commit()

def remove_credits(user_id, amount):
    cursor.execute("UPDATE users SET credits=credits-? WHERE id=?", (amount, user_id))
    conn.commit()

def ban_user(user_id):
    cursor.execute("UPDATE users SET is_banned=1 WHERE id=?", (user_id,))
    conn.commit()

def unban_user(user_id):
    cursor.execute("UPDATE users SET is_banned=0 WHERE id=?", (user_id,))
    conn.commit()

def get_stats():
    total_users = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_bots = cursor.execute("SELECT COUNT(*) FROM bots").fetchone()[0]
    running_bots = cursor.execute("SELECT COUNT(*) FROM bots WHERE status='Running'").fetchone()[0]
    return {'total_users': total_users, 'total_bots': total_bots, 'running_bots': running_bots}

def is_admin(user_id):
    user = get_user(user_id)
    return user and user[4] == 1

def get_system_stats():
    try:
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory().percent
        uptime = time.time() - psutil.boot_time()
        return {'cpu': cpu, 'ram': ram, 'uptime': uptime}
    except:
        return {'cpu': 25, 'ram': 40, 'uptime': 86400}

def format_uptime(seconds):
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    if days > 0:
        return f"{days}d {hours}h"
    return f"{hours}h"

def progress_bar(percent):
    filled = int(percent / 5)
    return "█" * filled + "░" * (20 - filled)

# ==================== BOT INIT ====================
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
app = Flask(__name__)

# ==================== KEYBOARDS ====================
def main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    buttons = ["📤 Upload Bot", "🤖 My Bots", "⚡ Deploy Bot", "💰 Buy Credits", "📊 Dashboard", "❓ Help", "ℹ️ About"]
    if is_admin(user_id):
        buttons.append("👑 Admin Panel")
    markup.add(*buttons)
    return markup

def admin_panel():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("👥 Users", callback_data="admin_users"),
        types.InlineKeyboardButton("🤖 Bots", callback_data="admin_bots"),
        types.InlineKeyboardButton("📊 Stats", callback_data="admin_stats"),
        types.InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast"),
        types.InlineKeyboardButton("💾 Backup", callback_data="admin_backup"),
        types.InlineKeyboardButton("🔙 Back", callback_data="admin_back")
    )
    return markup

def user_controls(user_id, username, credits, is_banned):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("💰 Add Credits", callback_data=f"add_credits_{user_id}"),
        types.InlineKeyboardButton("💎 Remove Credits", callback_data=f"remove_credits_{user_id}"),
        types.InlineKeyboardButton("🔨 Ban" if not is_banned else "🔓 Unban", callback_data=f"ban_{user_id}" if not is_banned else f"unban_{user_id}"),
        types.InlineKeyboardButton("🔙 Back", callback_data="back_to_users")
    )
    return markup

def bot_controls(bot_id, status):
    markup = types.InlineKeyboardMarkup(row_width=2)
    if status == "Running":
        markup.add(
            types.InlineKeyboardButton("⏸ Stop", callback_data=f"stop_{bot_id}"),
            types.InlineKeyboardButton("📊 Stats", callback_data=f"stats_{bot_id}")
        )
    else:
        markup.add(
            types.InlineKeyboardButton("▶️ Start", callback_data=f"start_{bot_id}"),
            types.InlineKeyboardButton("📊 Stats", callback_data=f"stats_{bot_id}")
        )
    markup.add(
        types.InlineKeyboardButton("📦 Export", callback_data=f"export_{bot_id}"),
        types.InlineKeyboardButton("🗑 Delete", callback_data=f"delete_{bot_id}"),
        types.InlineKeyboardButton("🔙 Back", callback_data="back_to_bots")
    )
    return markup

def user_bot_controls(bot_id, status):
    markup = types.InlineKeyboardMarkup(row_width=2)
    if status == "Running":
        markup.add(
            types.InlineKeyboardButton("⏸ Stop", callback_data=f"user_stop_{bot_id}"),
            types.InlineKeyboardButton("📊 Stats", callback_data=f"user_stats_{bot_id}")
        )
    else:
        markup.add(
            types.InlineKeyboardButton("▶️ Start", callback_data=f"user_start_{bot_id}"),
            types.InlineKeyboardButton("📊 Stats", callback_data=f"user_stats_{bot_id}")
        )
    markup.add(
        types.InlineKeyboardButton("📦 Export", callback_data=f"user_export_{bot_id}"),
        types.InlineKeyboardButton("🗑 Delete", callback_data=f"user_delete_{bot_id}"),
        types.InlineKeyboardButton("🔙 Back", callback_data="back_to_mybots")
    )
    return markup

# ==================== START COMMAND ====================
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    username = message.from_user.username or "User"
    
    user = get_user(user_id)
    if not user:
        cursor.execute("INSERT INTO users (id, username, join_date) VALUES (?, ?, ?)",
                      (user_id, username, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
        user = get_user(user_id)
    
    if user[5] == 1:
        bot.send_message(message.chat.id, "❌ You are banned! Contact support.")
        return
    
    stats = get_system_stats()
    db_stats = get_stats()
    
    if is_admin(user_id):
        text = f"""
╔══════════════════════════════╗
║     👑 ADMIN PANEL 👑        ║
╠══════════════════════════════╣
║ 👤 Admin: @{username}          
╠══════════════════════════════╣
║ 📊 Stats:                     
║ ├ Users: {db_stats['total_users']}              
║ ├ Bots: {db_stats['total_bots']}               
║ └ Running: {db_stats['running_bots']}          
╠══════════════════════════════╣
║ 🖥️ System:                    
║ ├ CPU: {progress_bar(stats['cpu'])} {stats['cpu']:.0f}%
║ ├ RAM: {progress_bar(stats['ram'])} {stats['ram']:.0f}%
║ └ Uptime: {format_uptime(stats['uptime'])}        
╚══════════════════════════════╝
"""
        bot.send_message(message.chat.id, text, reply_markup=admin_panel())
    else:
        text = f"""
╔══════════════════════════════╗
║        BOT HOSTING           ║
╠══════════════════════════════╣
║ 👤 User: @{username}           
║ 💰 Credits: {user[3]}                
║ 📦 Bots: {len(get_user_bots(user_id))}                
╠══════════════════════════════╣
║ 🖥️ System:                    
║ ├ CPU: {stats['cpu']:.0f}%                 
║ ├ RAM: {stats['ram']:.0f}%                 
║ └ Uptime: {format_uptime(stats['uptime'])}        
╚══════════════════════════════╝
"""
        bot.send_message(message.chat.id, text, reply_markup=main_menu(user_id))

# ==================== USER MENU ====================
@bot.message_handler(func=lambda m: m.text == "👑 Admin Panel")
def admin_panel_handler(message):
    if is_admin(message.from_user.id):
        start_command(message)

@bot.message_handler(func=lambda m: m.text == "📤 Upload Bot")
def upload_bot(message):
    msg = bot.reply_to(message, "📤 Send your Python bot file (.py)")
    bot.register_next_step_handler(msg, process_upload)

def process_upload(message):
    if not message.document:
        bot.reply_to(message, "❌ Please send a file!")
        return
    
    if not message.document.file_name.endswith('.py'):
        bot.reply_to(message, "❌ Only .py files allowed!")
        return
    
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded = bot.download_file(file_info.file_path)
        
        filename = f"{uuid.uuid4().hex[:8]}_{message.document.file_name}"
        file_path = Path(PROJECT_DIR) / filename
        file_path.write_bytes(downloaded)
        
        msg = bot.reply_to(message, "✅ Uploaded!\n\nEnter bot name:")
        bot.register_next_step_handler(msg, save_bot, filename)
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

def save_bot(message, filename):
    bot_name = message.text.strip()[:30]
    add_bot(message.from_user.id, bot_name, filename)
    bot.send_message(message.chat.id, f"✅ Bot '{bot_name}' saved!\n\nUse 'Deploy Bot' to start it.", 
                    reply_markup=main_menu(message.from_user.id))

@bot.message_handler(func=lambda m: m.text == "🤖 My Bots")
def my_bots(message):
    user_id = message.from_user.id
    bots = get_user_bots(user_id)
    
    if not bots:
        bot.reply_to(message, "🤖 No bots found!")
        return
    
    text = f"🤖 YOUR BOTS ({len(bots)})\n\n"
    for i, b in enumerate(bots, 1):
        status = "🟢" if b[5] == "Running" else "🔴"
        text += f"{i}. {status} {b[2]} - {b[5]}\n"
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b in bots:
        markup.add(types.InlineKeyboardButton(f"{b[2]}", callback_data=f"my_bot_{b[0]}"))
    
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "⚡ Deploy Bot")
def deploy_bot(message):
    user_id = message.from_user.id
    bots = get_user_bots(user_id)
    available = [b for b in bots if b[5] != "Running"]
    
    if not available:
        bot.reply_to(message, "📭 No bots to deploy!")
        return
    
    text = "⚡ DEPLOY BOT\n\n"
    for i, b in enumerate(available, 1):
        text += f"{i}. {b[2]}\n"
    
    msg = bot.reply_to(message, text + "\nEnter number:")
    bot.register_next_step_handler(msg, process_deploy, available)

def process_deploy(message, bots):
    try:
        choice = int(message.text) - 1
        bot_data = bots[choice]
        file_path = Path(PROJECT_DIR) / bot_data[3]
        
        if not file_path.exists():
            bot.reply_to(message, "❌ File not found!")
            return
        
        proc = subprocess.Popen(['python', str(file_path)], start_new_session=True)
        update_bot_status(bot_data[0], "Running", proc.pid)
        bot.reply_to(message, f"✅ {bot_data[2]} started! PID: {proc.pid}")
    except:
        bot.reply_to(message, "❌ Invalid choice!")

@bot.message_handler(func=lambda m: m.text == "💰 Buy Credits")
def buy_credits(message):
    text = """
💰 BUY CREDITS
╔══════════════════════════════╗
║ 100 Credits → $4.99          ║
║ 500 Credits → $19.99         ║
║ 1000 Credits → $34.99        ║
╠══════════════════════════════╣
║ Contact @aurponmodz to buy!  ║
╚══════════════════════════════╝
"""
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: m.text == "📊 Dashboard")
def dashboard(message):
    user = get_user(message.from_user.id)
    bots = get_user_bots(message.from_user.id)
    stats = get_system_stats()
    
    text = f"""
📊 DASHBOARD
╔══════════════════════════════╗
║ Credits: {user[3]}                   
║ Total Bots: {len(bots)}                
║ Running: {len([b for b in bots if b[5] == 'Running'])}            
╠══════════════════════════════╣
║ CPU: {stats['cpu']:.0f}%                 
║ RAM: {stats['ram']:.0f}%                 
╚══════════════════════════════╝
"""
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: m.text == "❓ Help")
def help_command(message):
    text = """
❓ HELP
╔══════════════════════════════╗
║ 📤 Upload Bot - Upload .py   ║
║ 🤖 My Bots - View your bots  ║
║ ⚡ Deploy Bot - Start bot    ║
║ 💰 Buy Credits - Get credits ║
║ 📊 Dashboard - Your stats    ║
╚══════════════════════════════╝
"""
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: m.text == "ℹ️ About")
def about_command(message):
    text = """
ℹ️ ABOUT
╔══════════════════════════════╗
║ AURPON BOT HOST              ║
║ Version: 6.0                 ║
╠══════════════════════════════╣
║ Developer: @aurponmodz       ║
║ Support: @aurponmodz         ║
╚══════════════════════════════╝
"""
    bot.send_message(message.chat.id, text)

# ==================== ADMIN CALLBACKS ====================
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    data = call.data
    
    if data == "admin_users":
        users = get_all_users()
        text = f"👥 USERS ({len(users)})\n\n"
        for u in users[:10]:
            status = "✅" if not u[3] else "🔴"
            text += f"{status} {u[1]} | {u[2]} credits\n"
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        for u in users[:10]:
            markup.add(types.InlineKeyboardButton(f"📊 {u[1]}", callback_data=f"user_{u[0]}"))
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="admin_back"))
        
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    
    elif data == "admin_bots":
        bots = get_all_bots()
        text = f"🤖 BOTS ({len(bots)})\n\n"
        for b in bots[:10]:
            status = "🟢" if b[5] == "Running" else "🔴"
            owner = b[12] if len(b) > 12 else "Unknown"
            text += f"{status} {b[2]} - Owner: {owner}\n"
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        for b in bots[:10]:
            markup.add(types.InlineKeyboardButton(f"🤖 {b[2]}", callback_data=f"admin_bot_{b[0]}"))
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="admin_back"))
        
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    
    elif data == "admin_stats":
        stats = get_stats()
        text = f"""
📊 SYSTEM STATS
╔══════════════════════════════╗
║ Total Users: {stats['total_users']}        
║ Total Bots: {stats['total_bots']}         
║ Running Bots: {stats['running_bots']}      
╚══════════════════════════════╝
"""
        markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 Back", callback_data="admin_back"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    
    elif data == "admin_broadcast":
        msg = bot.send_message(call.message.chat.id, "📢 Enter broadcast message:")
        bot.register_next_step_handler(msg, process_broadcast, call.message)
    
    elif data == "admin_backup":
        backup_path = Path(DB_NAME)
        if backup_path.exists():
            with open(backup_path, 'rb') as f:
                bot.send_document(call.message.chat.id, f, caption="💾 Database Backup")
        bot.answer_callback_query(call.id, "Backup sent!")
    
    elif data == "admin_back":
        start_command(call.message)
    
    elif data.startswith("user_"):
        user_id = int(data.split('_')[1])
        user = get_user(user_id)
        if user:
            text = f"""
👤 USER DETAILS
╔══════════════════════════════╗
║ ID: {user[0]}                 
║ Username: @{user[1]}          
║ Credits: {user[3]}             
║ Status: {'🔴 Banned' if user[5] else '🟢 Active'}    
╚══════════════════════════════╝
"""
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                                reply_markup=user_controls(user_id, user[1], user[3], user[5]))
    
    elif data.startswith("add_credits_"):
        user_id = int(data.split('_')[2])
        msg = bot.send_message(call.message.chat.id, f"Enter credits to add:")
        bot.register_next_step_handler(msg, process_add_credits, user_id, call.message)
    
    elif data.startswith("remove_credits_"):
        user_id = int(data.split('_')[2])
        msg = bot.send_message(call.message.chat.id, f"Enter credits to remove:")
        bot.register_next_step_handler(msg, process_remove_credits, user_id, call.message)
    
    elif data.startswith("ban_"):
        user_id = int(data.split('_')[1])
        ban_user(user_id)
        bot.answer_callback_query(call.id, "✅ User banned!")
        user = get_user(user_id)
        text = f"""
👤 USER DETAILS
╔══════════════════════════════╗
║ Username: @{user[1]}          
║ Status: 🔴 BANNED             
╚══════════════════════════════╝
"""
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                            reply_markup=user_controls(user_id, user[1], user[3], True))
    
    elif data.startswith("unban_"):
        user_id = int(data.split('_')[1])
        unban_user(user_id)
        bot.answer_callback_query(call.id, "✅ User unbanned!")
        user = get_user(user_id)
        text = f"""
👤 USER DETAILS
╔══════════════════════════════╗
║ Username: @{user[1]}          
║ Status: 🟢 ACTIVE             
╚══════════════════════════════╝
"""
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                            reply_markup=user_controls(user_id, user[1], user[3], False))
    
    elif data == "back_to_users":
        users = get_all_users()
        text = f"👥 USERS ({len(users)})\n\n"
        for u in users[:10]:
            status = "✅" if not u[3] else "🔴"
            text += f"{status} {u[1]} | {u[2]} credits\n"
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        for u in users[:10]:
            markup.add(types.InlineKeyboardButton(f"📊 {u[1]}", callback_data=f"user_{u[0]}"))
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="admin_back"))
        
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    
    elif data == "back_to_bots":
        bots = get_all_bots()
        text = f"🤖 BOTS ({len(bots)})\n\n"
        for b in bots[:10]:
            status = "🟢" if b[5] == "Running" else "🔴"
            owner = b[12] if len(b) > 12 else "Unknown"
            text += f"{status} {b[2]} - Owner: {owner}\n"
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        for b in bots[:10]:
            markup.add(types.InlineKeyboardButton(f"🤖 {b[2]}", callback_data=f"admin_bot_{b[0]}"))
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="admin_back"))
        
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    
    elif data.startswith("admin_bot_"):
        bot_id = int(data.split('_')[2])
        cursor.execute("SELECT * FROM bots WHERE id=?", (bot_id,))
        bot_data = cursor.fetchone()
        
        if bot_data:
            text = f"""
🤖 BOT DETAILS
╔══════════════════════════════╗
║ Name: {bot_data[2]}            
║ Owner: {bot_data[1]}           
║ Status: {bot_data[5]}            
║ Deploys: {bot_data[7]}           
╚══════════════════════════════╝
"""
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                                reply_markup=bot_controls(bot_id, bot_data[5]))
    
    elif data.startswith("start_"):
        bot_id = int(data.split('_')[1])
        cursor.execute("SELECT bot_name, filename FROM bots WHERE id=?", (bot_id,))
        bot_data = cursor.fetchone()
        
        if bot_data:
            file_path = Path(PROJECT_DIR) / bot_data[1]
            if file_path.exists():
                proc = subprocess.Popen(['python', str(file_path)], start_new_session=True)
                update_bot_status(bot_id, "Running", proc.pid)
                bot.answer_callback_query(call.id, f"✅ {bot_data[0]} started!")
    
    elif data.startswith("stop_"):
        bot_id = int(data.split('_')[1])
        cursor.execute("SELECT pid, bot_name FROM bots WHERE id=?", (bot_id,))
        bot_data = cursor.fetchone()
        
        if bot_data and bot_data[0]:
            try:
                os.kill(bot_data[0], signal.SIGTERM)
            except:
                pass
            update_bot_status(bot_id, "Stopped")
            bot.answer_callback_query(call.id, f"⏸ {bot_data[1]} stopped!")
    
    elif data.startswith("delete_"):
        bot_id = int(data.split('_')[1])
        cursor.execute("SELECT pid, bot_name, filename FROM bots WHERE id=?", (bot_id,))
        bot_data = cursor.fetchone()
        
        if bot_data and bot_data[0]:
            try:
                os.kill(bot_data[0], signal.SIGKILL)
            except:
                pass
        
        file_path = Path(PROJECT_DIR) / bot_data[2]
        if file_path.exists():
            file_path.unlink()
        
        delete_bot(bot_id)
        bot.answer_callback_query(call.id, f"🗑 {bot_data[1]} deleted!")
        bot.delete_message(call.message.chat.id, call.message.message_id)
    
    elif data.startswith("export_"):
        bot_id = int(data.split('_')[1])
        cursor.execute("SELECT bot_name, filename FROM bots WHERE id=?", (bot_id,))
        bot_data = cursor.fetchone()
        
        if bot_data:
            file_path = Path(PROJECT_DIR) / bot_data[1]
            if file_path.exists():
                with open(file_path, 'rb') as f:
                    bot.send_document(call.message.chat.id, f, caption=f"📦 {bot_data[0]}")
                bot.answer_callback_query(call.id, "Bot exported!")
    
    elif data.startswith("stats_"):
        bot_id = int(data.split('_')[1])
        cursor.execute("SELECT pid, bot_name, status FROM bots WHERE id=?", (bot_id,))
        bot_data = cursor.fetchone()
        
        if bot_data and bot_data[2] == "Running" and bot_data[0]:
            try:
                proc = psutil.Process(bot_data[0])
                cpu = proc.cpu_percent(interval=0.5)
                mem = proc.memory_percent()
                text = f"""
📊 BOT STATS
╔══════════════════════════════╗
║ {bot_data[1]}                   
║ CPU: {cpu:.1f}%                 
║ RAM: {mem:.1f}%                 
║ PID: {bot_data[0]}              
╚══════════════════════════════╝
"""
                bot.send_message(call.message.chat.id, text)
            except:
                bot.answer_callback_query(call.id, "Cannot get stats!")
        else:
            bot.answer_callback_query(call.id, "Bot not running!")
    
    elif data.startswith("my_bot_"):
        bot_id = int(data.split('_')[2])
        cursor.execute("SELECT * FROM bots WHERE id=?", (bot_id,))
        bot_data = cursor.fetchone()
        
        if bot_data:
            text = f"""
🤖 BOT DETAILS
╔══════════════════════════════╗
║ Name: {bot_data[2]}            
║ Status: {bot_data[5]}            
║ Deploys: {bot_data[7]}           
╚══════════════════════════════╝
"""
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                                reply_markup=user_bot_controls(bot_id, bot_data[5]))
    
    elif data.startswith("user_start_"):
        bot_id = int(data.split('_')[2])
        cursor.execute("SELECT bot_name, filename FROM bots WHERE id=?", (bot_id,))
        bot_data = cursor.fetchone()
        
        if bot_data:
            file_path = Path(PROJECT_DIR) / bot_data[1]
            if file_path.exists():
                proc = subprocess.Popen(['python', str(file_path)], start_new_session=True)
                update_bot_status(bot_id, "Running", proc.pid)
                bot.answer_callback_query(call.id, f"✅ {bot_data[0]} started!")
                my_bots(call.message)
    
    elif data.startswith("user_stop_"):
        bot_id = int(data.split('_')[2])
        cursor.execute("SELECT pid, bot_name FROM bots WHERE id=?", (bot_id,))
        bot_data = cursor.fetchone()
        
        if bot_data and bot_data[0]:
            try:
                os.kill(bot_data[0], signal.SIGTERM)
            except:
                pass
            update_bot_status(bot_id, "Stopped")
            bot.answer_callback_query(call.id, f"⏸ {bot_data[1]} stopped!")
            my_bots(call.message)
    
    elif data.startswith("user_delete_"):
        bot_id = int(data.split('_')[2])
        cursor.execute("SELECT pid, bot_name, filename FROM bots WHERE id=?", (bot_id,))
        bot_data = cursor.fetchone()
        
        if bot_data and bot_data[0]:
            try:
                os.kill(bot_data[0], signal.SIGKILL)
            except:
                pass
        
        file_path = Path(PROJECT_DIR) / bot_data[2]
        if file_path.exists():
            file_path.unlink()
        
        delete_bot(bot_id)
        bot.answer_callback_query(call.id, f"🗑 {bot_data[1]} deleted!")
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, f"✅ Bot '{bot_data[1]}' deleted!")
    
    elif data.startswith("user_export_"):
        bot_id = int(data.split('_')[2])
        cursor.execute("SELECT bot_name, filename FROM bots WHERE id=?", (bot_id,))
        bot_data = cursor.fetchone()
        
        if bot_data:
            file_path = Path(PROJECT_DIR) / bot_data[1]
            if file_path.exists():
                with open(file_path, 'rb') as f:
                    bot.send_document(call.message.chat.id, f, caption=f"📦 {bot_data[0]}")
                bot.answer_callback_query(call.id, "Bot exported!")
    
    elif data.startswith("user_stats_"):
        bot_id = int(data.split('_')[2])
        cursor.execute("SELECT pid, bot_name, status FROM bots WHERE id=?", (bot_id,))
        bot_data = cursor.fetchone()
        
        if bot_data and bot_data[2] == "Running" and bot_data[0]:
            try:
                proc = psutil.Process(bot_data[0])
                cpu = proc.cpu_percent(interval=0.5)
                mem = proc.memory_percent()
                text = f"""
📊 BOT STATS
╔══════════════════════════════╗
║ {bot_data[1]}                   
║ CPU: {cpu:.1f}%                 
║ RAM: {mem:.1f}%                 
║ PID: {bot_data[0]}              
╚══════════════════════════════╝
"""
                bot.send_message(call.message.chat.id, text)
            except:
                bot.answer_callback_query(call.id, "Cannot get stats!")
        else:
            bot.answer_callback_query(call.id, "Bot not running!")
    
    elif data == "back_to_mybots":
        my_bots(call.message)
    
    bot.answer_callback_query(call.id)

# ==================== PROCESS FUNCTIONS ====================
def process_add_credits(message, user_id, original_message):
    try:
        amount = int(message.text.strip())
        add_credits(user_id, amount)
        bot.send_message(message.chat.id, f"✅ Added {amount} credits!")
        user = get_user(user_id)
        text = f"""
👤 USER DETAILS
╔══════════════════════════════╗
║ Username: @{user[1]}          
║ Credits: {user[3]} (Updated)   
╚══════════════════════════════╝
"""
        bot.edit_message_text(text, original_message.chat.id, original_message.message_id,
                            reply_markup=user_controls(user_id, user[1], user[3], user[5]))
    except:
        bot.send_message(message.chat.id, "❌ Invalid amount!")

def process_remove_credits(message, user_id, original_message):
    try:
        amount = int(message.text.strip())
        remove_credits(user_id, amount)
        bot.send_message(message.chat.id, f"✅ Removed {amount} credits!")
        user = get_user(user_id)
        text = f"""
👤 USER DETAILS
╔══════════════════════════════╗
║ Username: @{user[1]}          
║ Credits: {user[3]} (Updated)   
╚══════════════════════════════╝
"""
        bot.edit_message_text(text, original_message.chat.id, original_message.message_id,
                            reply_markup=user_controls(user_id, user[1], user[3], user[5]))
    except:
        bot.send_message(message.chat.id, "❌ Invalid amount!")

def process_broadcast(message, original_message):
    broadcast_text = message.text
    users = get_all_users()
    
    success = 0
    for user in users:
        try:
            bot.send_message(user[0], f"📢 ANNOUNCEMENT\n\n{broadcast_text}")
            success += 1
            time.sleep(0.05)
        except:
            pass
    
    bot.send_message(original_message.chat.id, f"✅ Broadcast sent to {success} users!")
    start_command(original_message)

# ==================== FLASK ROUTES ====================
@app.route('/')
def home():
    return jsonify({"status": "online", "version": "6.0"})

@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

# ==================== BACKGROUND TASKS ====================
def cleanup_processes():
    while True:
        try:
            cursor.execute("SELECT id, pid FROM bots WHERE status='Running'")
            for bot_id, pid in cursor.fetchall():
                if pid:
                    try:
                        os.kill(pid, 0)
                    except OSError:
                        update_bot_status(bot_id, "Stopped")
        except:
            pass
        time.sleep(60)

# ==================== MAIN ====================
def run_bot():
    print(f"Bot started!")
    try:
        bot.remove_webhook()
    except:
        pass
    time.sleep(2)
    while True:
        try:
            bot.infinity_polling(timeout=30)
        except Exception as e:
            print(f"Bot error: {e}")
            time.sleep(10)

if __name__ == '__main__':
    threading.Thread(target=cleanup_processes, daemon=True).start()
    threading.Thread(target=run_bot, daemon=True).start()
    app.run(host='0.0.0.0', port=PORT, debug=False)    def __init__(self):
        self.conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()
    
    def create_tables(self):
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            join_date TEXT,
            plan TEXT DEFAULT 'free',
            credits INTEGER DEFAULT 100,
            is_admin INTEGER DEFAULT 0,
            is_banned INTEGER DEFAULT 0
        )''')
        
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS bots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            bot_name TEXT,
            filename TEXT,
            pid INTEGER,
            status TEXT,
            start_time TEXT,
            deploy_count INTEGER DEFAULT 0
        )''')
        
        # Add admin
        self.cursor.execute("INSERT OR IGNORE INTO users VALUES (?, ?, ?, ?, ?, ?, ?)",
                          (ADMIN_ID, 'admin', datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                           'enterprise', 999999, 1, 0))
        self.conn.commit()
    
    def get_user(self, user_id):
        self.cursor.execute("SELECT * FROM users WHERE id=?", (user_id,))
        return self.cursor.fetchone()
    
    def get_all_users(self):
        self.cursor.execute("SELECT id, username, plan, credits, is_banned FROM users ORDER BY id DESC")
        return self.cursor.fetchall()
    
    def get_user_bots(self, user_id):
        self.cursor.execute("SELECT * FROM bots WHERE user_id=? ORDER BY id DESC", (user_id,))
        return self.cursor.fetchall()
    
    def get_all_bots(self):
        self.cursor.execute("SELECT b.*, u.username FROM bots b LEFT JOIN users u ON b.user_id = u.id ORDER BY b.id DESC")
        return self.cursor.fetchall()
    
    def add_bot(self, user_id, bot_name, filename):
        self.cursor.execute("INSERT INTO bots (user_id, bot_name, filename, status) VALUES (?, ?, ?, ?)",
                          (user_id, bot_name, filename, "Uploaded"))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def update_bot_status(self, bot_id, status, pid=None):
        if pid:
            self.cursor.execute("UPDATE bots SET status=?, pid=?, start_time=? WHERE id=?",
                              (status, pid, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), bot_id))
        else:
            self.cursor.execute("UPDATE bots SET status=? WHERE id=?", (status, bot_id))
        self.conn.commit()
    
    def delete_bot(self, bot_id):
        self.cursor.execute("DELETE FROM bots WHERE id=?", (bot_id,))
        self.conn.commit()
    
    def add_credits(self, user_id, amount):
        self.cursor.execute("UPDATE users SET credits=credits+? WHERE id=?", (amount, user_id))
        self.conn.commit()
    
    def remove_credits(self, user_id, amount):
        self.cursor.execute("UPDATE users SET credits=credits-? WHERE id=?", (amount, user_id))
        self.conn.commit()
    
    def ban_user(self, user_id):
        self.cursor.execute("UPDATE users SET is_banned=1 WHERE id=?", (user_id,))
        self.conn.commit()
    
    def unban_user(self, user_id):
        self.cursor.execute("UPDATE users SET is_banned=0 WHERE id=?", (user_id,))
        self.conn.commit()
    
    def get_stats(self):
        total_users = self.cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        total_bots = self.cursor.execute("SELECT COUNT(*) FROM bots").fetchone()[0]
        running_bots = self.cursor.execute("SELECT COUNT(*) FROM bots WHERE status='Running'").fetchone()[0]
        return {'total_users': total_users, 'total_bots': total_bots, 'running_bots': running_bots}

db = Database()

# ==================== BOT INIT ====================
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
app = Flask(__name__)

# ==================== HELPER FUNCTIONS ====================
def is_admin(user_id):
    user = db.get_user(user_id)
    return user and user[5] == 1

def get_system_stats():
    try:
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory().percent
        uptime = time.time() - psutil.boot_time()
        return {'cpu': cpu, 'ram': ram, 'uptime': uptime}
    except:
        return {'cpu': 25, 'ram': 40, 'uptime': 86400}

def format_uptime(seconds):
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    if days > 0:
        return f"{days}d {hours}h"
    return f"{hours}h"

def progress_bar(percent):
    filled = int(percent / 5)
    return "█" * filled + "░" * (20 - filled)

# ==================== KEYBOARDS ====================
def main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    buttons = ["📤 Upload Bot", "🤖 My Bots", "⚡ Deploy Bot", "💰 Buy Credits", "📊 Dashboard", "❓ Help", "ℹ️ About"]
    if is_admin(user_id):
        buttons.append("👑 Admin Panel")
    markup.add(*buttons)
    return markup

def admin_panel():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("👥 Users", callback_data="admin_users"),
        types.InlineKeyboardButton("🤖 Bots", callback_data="admin_bots"),
        types.InlineKeyboardButton("📊 Stats", callback_data="admin_stats"),
        types.InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast"),
        types.InlineKeyboardButton("💾 Backup", callback_data="admin_backup"),
        types.InlineKeyboardButton("🔙 Back", callback_data="admin_back")
    )
    return markup

def user_controls(user_id, username, credits, is_banned):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("💰 Add Credits", callback_data=f"add_credits_{user_id}"),
        types.InlineKeyboardButton("💎 Remove Credits", callback_data=f"remove_credits_{user_id}"),
        types.InlineKeyboardButton("🔨 Ban" if not is_banned else "🔓 Unban", callback_data=f"ban_{user_id}" if not is_banned else f"unban_{user_id}"),
        types.InlineKeyboardButton("🔙 Back", callback_data="back_to_users")
    )
    return markup

def bot_controls(bot_id, status):
    markup = types.InlineKeyboardMarkup(row_width=2)
    if status == "Running":
        markup.add(
            types.InlineKeyboardButton("⏸ Stop", callback_data=f"stop_{bot_id}"),
            types.InlineKeyboardButton("📊 Stats", callback_data=f"stats_{bot_id}")
        )
    else:
        markup.add(
            types.InlineKeyboardButton("▶️ Start", callback_data=f"start_{bot_id}"),
            types.InlineKeyboardButton("📊 Stats", callback_data=f"stats_{bot_id}")
        )
    markup.add(
        types.InlineKeyboardButton("📦 Export", callback_data=f"export_{bot_id}"),
        types.InlineKeyboardButton("🗑 Delete", callback_data=f"delete_{bot_id}"),
        types.InlineKeyboardButton("🔙 Back", callback_data="back_to_bots")
    )
    return markup

def user_bot_controls(bot_id, status):
    markup = types.InlineKeyboardMarkup(row_width=2)
    if status == "Running":
        markup.add(
            types.InlineKeyboardButton("⏸ Stop", callback_data=f"user_stop_{bot_id}"),
            types.InlineKeyboardButton("📊 Stats", callback_data=f"user_stats_{bot_id}")
        )
    else:
        markup.add(
            types.InlineKeyboardButton("▶️ Start", callback_data=f"user_start_{bot_id}"),
            types.InlineKeyboardButton("📊 Stats", callback_data=f"user_stats_{bot_id}")
        )
    markup.add(
        types.InlineKeyboardButton("📦 Export", callback_data=f"user_export_{bot_id}"),
        types.InlineKeyboardButton("🗑 Delete", callback_data=f"user_delete_{bot_id}"),
        types.InlineKeyboardButton("🔙 Back", callback_data="back_to_mybots")
    )
    return markup

# ==================== START COMMAND ====================
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    username = message.from_user.username or "User"
    
    user = db.get_user(user_id)
    if not user:
        db.cursor.execute("INSERT INTO users (id, username, join_date) VALUES (?, ?, ?)",
                         (user_id, username, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        db.conn.commit()
        user = db.get_user(user_id)
    
    if user[6] == 1:
        bot.send_message(message.chat.id, "❌ You are banned! Contact support.")
        return
    
    stats = get_system_stats()
    
    if is_admin(user_id):
        text = f"""
╔══════════════════════════════╗
║     👑 ADMIN PANEL 👑        ║
╠══════════════════════════════╣
║ 👤 Admin: @{username}          
║ 💎 Status: SUPER ADMIN        
╠══════════════════════════════╣
║ 📊 Stats:                     
║ ├ Users: {db.get_stats()['total_users']}              
║ ├ Bots: {db.get_stats()['total_bots']}               
║ └ Running: {db.get_stats()['running_bots']}          
╠══════════════════════════════╣
║ 🖥️ System:                    
║ ├ CPU: {progress_bar(stats['cpu'])} {stats['cpu']:.0f}%
║ ├ RAM: {progress_bar(stats['ram'])} {stats['ram']:.0f}%
║ └ Uptime: {format_uptime(stats['uptime'])}        
╚══════════════════════════════╝
"""
        bot.send_message(message.chat.id, text, reply_markup=admin_panel())
    else:
        text = f"""
╔══════════════════════════════╗
║     {BRAND_NAME} v{VERSION}     ║
╠══════════════════════════════╣
║ 👤 User: @{username}           
║ 💰 Credits: {user[4]}                
║ 📦 Bots: {len(db.get_user_bots(user_id))}                
╠══════════════════════════════╣
║ 🖥️ System:                    
║ ├ CPU: {stats['cpu']:.0f}%                 
║ ├ RAM: {stats['ram']:.0f}%                 
║ └ Uptime: {format_uptime(stats['uptime'])}        
╚══════════════════════════════╝
"""
        bot.send_message(message.chat.id, text, reply_markup=main_menu(user_id))

# ==================== USER MENU HANDLERS ====================
@bot.message_handler(func=lambda m: m.text == "👑 Admin Panel")
def admin_panel_handler(message):
    if is_admin(message.from_user.id):
        start_command(message)
    else:
        bot.reply_to(message, "❌ Admin access only!")

@bot.message_handler(func=lambda m: m.text == "📤 Upload Bot")
def upload_bot(message):
    msg = bot.reply_to(message, "📤 Send your Python bot file (.py)")
    bot.register_next_step_handler(msg, process_upload)

def process_upload(message):
    if not message.document:
        bot.reply_to(message, "❌ Please send a file!")
        return
    
    if not message.document.file_name.endswith('.py'):
        bot.reply_to(message, "❌ Only .py files allowed!")
        return
    
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded = bot.download_file(file_info.file_path)
        
        filename = f"{uuid.uuid4().hex[:8]}_{message.document.file_name}"
        file_path = Path(PROJECT_DIR) / filename
        file_path.write_bytes(downloaded)
        
        msg = bot.reply_to(message, "✅ Uploaded!\n\nEnter bot name:")
        bot.register_next_step_handler(msg, save_bot, filename)
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

def save_bot(message, filename):
    bot_name = message.text.strip()[:30]
    bot_id = db.add_bot(message.from_user.id, bot_name, filename)
    bot.send_message(message.chat.id, f"✅ Bot '{bot_name}' saved!\n\nUse 'Deploy Bot' to start it.", reply_markup=main_menu(message.from_user.id))

@bot.message_handler(func=lambda m: m.text == "🤖 My Bots")
def my_bots(message):
    user_id = message.from_user.id
    bots = db.get_user_bots(user_id)
    
    if not bots:
        bot.reply_to(message, "🤖 No bots found!")
        return
    
    text = f"🤖 YOUR BOTS ({len(bots)})\n\n"
    for i, b in enumerate(bots, 1):
        status = "🟢" if b[5] == "Running" else "🔴"
        text += f"{i}. {status} {b[2]} - {b[5]}\n"
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b in bots:
        markup.add(types.InlineKeyboardButton(f"{b[2]}", callback_data=f"my_bot_{b[0]}"))
    
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "⚡ Deploy Bot")
def deploy_bot(message):
    user_id = message.from_user.id
    bots = db.get_user_bots(user_id)
    available = [b for b in bots if b[5] != "Running"]
    
    if not available:
        bot.reply_to(message, "📭 No bots to deploy!")
        return
    
    text = "⚡ DEPLOY BOT\n\n"
    for i, b in enumerate(available, 1):
        text += f"{i}. {b[2]}\n"
    
    msg = bot.reply_to(message, text + "\nEnter number:")
    bot.register_next_step_handler(msg, process_deploy, available)

def process_deploy(message, bots):
    try:
        choice = int(message.text) - 1
        bot_data = bots[choice]
        file_path = Path(PROJECT_DIR) / bot_data[3]
        
        if not file_path.exists():
            bot.reply_to(message, "❌ File not found!")
            return
        
        proc = subprocess.Popen(['python', str(file_path)], start_new_session=True)
        db.update_bot_status(bot_data[0], "Running", proc.pid)
        bot.reply_to(message, f"✅ {bot_data[2]} started! PID: {proc.pid}")
    except:
        bot.reply_to(message, "❌ Invalid choice!")

@bot.message_handler(func=lambda m: m.text == "💰 Buy Credits")
def buy_credits(message):
    text = """
💰 BUY CREDITS
╔══════════════════════════════╗
║ 100 Credits → $4.99          ║
║ 500 Credits → $19.99         ║
║ 1000 Credits → $34.99        ║
╠══════════════════════════════╣
║ Contact @aurponmodz to buy!  ║
╚══════════════════════════════╝
"""
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: m.text == "📊 Dashboard")
def dashboard(message):
    user = db.get_user(message.from_user.id)
    bots = db.get_user_bots(message.from_user.id)
    stats = get_system_stats()
    
    text = f"""
📊 DASHBOARD
╔══════════════════════════════╗
║ Credits: {user[4]}                   
║ Total Bots: {len(bots)}                
║ Running: {len([b for b in bots if b[5] == 'Running'])}            
╠══════════════════════════════╣
║ CPU: {stats['cpu']:.0f}%                 
║ RAM: {stats['ram']:.0f}%                 
╚══════════════════════════════╝
"""
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: m.text == "❓ Help")
def help_command(message):
    text = """
❓ HELP
╔══════════════════════════════╗
║ 📤 Upload Bot - Upload .py   ║
║ 🤖 My Bots - View your bots  ║
║ ⚡ Deploy Bot - Start bot    ║
║ 💰 Buy Credits - Get credits ║
║ 📊 Dashboard - Your stats    ║
╚══════════════════════════════╝
"""
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: m.text == "ℹ️ About")
def about_command(message):
    text = f"""
ℹ️ ABOUT
╔══════════════════════════════╗
║ {BRAND_NAME}                  
║ Version: {VERSION}                   
╠══════════════════════════════╣
║ Developer: @aurponmodz       ║
║ Support: {SUPPORT_ID}         ║
╚══════════════════════════════╝
"""
    bot.send_message(message.chat.id, text)

# ==================== ADMIN CALLBACKS ====================
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    data = call.data
    
    # Admin Users
    if data == "admin_users":
        users = db.get_all_users()
        text = f"👥 USERS ({len(users)})\n\n"
        for u in users[:10]:
            status = "✅" if not u[4] else "🔴"
            text += f"{status} {u[1]} | {u[2]} | {u[3]} credits\n"
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        for u in users[:10]:
            markup.add(types.InlineKeyboardButton(f"📊 {u[1]}", callback_data=f"user_{u[0]}"))
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="admin_back"))
        
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    
    # Admin Bots
    elif data == "admin_bots":
        bots = db.get_all_bots()
        text = f"🤖 BOTS ({len(bots)})\n\n"
        for b in bots[:10]:
            status = "🟢" if b[5] == "Running" else "🔴"
            text += f"{status} {b[2]} - Owner: {b[12]}\n"
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        for b in bots[:10]:
            markup.add(types.InlineKeyboardButton(f"🤖 {b[2]}", callback_data=f"admin_bot_{b[0]}"))
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="admin_back"))
        
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    
    # Admin Stats
    elif data == "admin_stats":
        stats = db.get_stats()
        text = f"""
📊 SYSTEM STATS
╔══════════════════════════════╗
║ Total Users: {stats['total_users']}        
║ Total Bots: {stats['total_bots']}         
║ Running Bots: {stats['running_bots']}      
╚══════════════════════════════╝
"""
        markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 Back", callback_data="admin_back"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    
    # Admin Broadcast
    elif data == "admin_broadcast":
        msg = bot.send_message(call.message.chat.id, "📢 Enter broadcast message:")
        bot.register_next_step_handler(msg, process_broadcast, call.message)
    
    # Admin Backup
    elif data == "admin_backup":
        backup_path = Path(DB_NAME)
        if backup_path.exists():
            with open(backup_path, 'rb') as f:
                bot.send_document(call.message.chat.id, f, caption="💾 Database Backup")
        bot.answer_callback_query(call.id, "Backup sent!")
    
    # Admin Back
    elif data == "admin_back":
        start_command(call.message)
    
    # User Detail
    elif data.startswith("user_"):
        user_id = int(data.split('_')[1])
        user = db.get_user(user_id)
        if user:
            text = f"""
👤 USER DETAILS
╔══════════════════════════════╗
║ ID: {user[0]}                 
║ Username: @{user[1]}          
║ Plan: {user[2]}                
║ Credits: {user[4]}             
║ Status: {'🔴 Banned' if user[6] else '🟢 Active'}    
╚══════════════════════════════╝
"""
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                                reply_markup=user_controls(user_id, user[1], user[4], user[6]))
    
    # Add Credits
    elif data.startswith("add_credits_"):
        user_id = int(data.split('_')[2])
        msg = bot.send_message(call.message.chat.id, f"Enter credits to add for user {user_id}:")
        bot.register_next_step_handler(msg, process_add_credits, user_id, call.message)
    
    # Remove Credits
    elif data.startswith("remove_credits_"):
        user_id = int(data.split('_')[2])
        msg = bot.send_message(call.message.chat.id, f"Enter credits to remove from user {user_id}:")
        bot.register_next_step_handler(msg, process_remove_credits, user_id, call.message)
    
    # Ban User
    elif data.startswith("ban_"):
        user_id = int(data.split('_')[1])
        db.ban_user(user_id)
        bot.answer_callback_query(call.id, "✅ User banned!")
        user = db.get_user(user_id)
        text = f"""
👤 USER DETAILS
╔══════════════════════════════╗
║ Username: @{user[1]}          
║ Status: 🔴 BANNED             
╚══════════════════════════════╝
"""
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                            reply_markup=user_controls(user_id, user[1], user[4], True))
    
    # Unban User
    elif data.startswith("unban_"):
        user_id = int(data.split('_')[1])
        db.unban_user(user_id)
        bot.answer_callback_query(call.id, "✅ User unbanned!")
        user = db.get_user(user_id)
        text = f"""
👤 USER DETAILS
╔══════════════════════════════╗
║ Username: @{user[1]}          
║ Status: 🟢 ACTIVE             
╚══════════════════════════════╝
"""
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                            reply_markup=user_controls(user_id, user[1], user[4], False))
    
    # Back to Users
    elif data == "back_to_users":
        users = db.get_all_users()
        text = f"👥 USERS ({len(users)})\n\n"
        for u in users[:10]:
            status = "✅" if not u[4] else "🔴"
            text += f"{status} {u[1]} | {u[2]} | {u[3]} credits\n"
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        for u in users[:10]:
            markup.add(types.InlineKeyboardButton(f"📊 {u[1]}", callback_data=f"user_{u[0]}"))
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="admin_back"))
        
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    
    # Back to Bots
    elif data == "back_to_bots":
        bots = db.get_all_bots()
        text = f"🤖 BOTS ({len(bots)})\n\n"
        for b in bots[:10]:
            status = "🟢" if b[5] == "Running" else "🔴"
            text += f"{status} {b[2]} - Owner: {b[12]}\n"
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        for b in bots[:10]:
            markup.add(types.InlineKeyboardButton(f"🤖 {b[2]}", callback_data=f"admin_bot_{b[0]}"))
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="admin_back"))
        
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    
    # Admin Bot Detail
    elif data.startswith("admin_bot_"):
        bot_id = int(data.split('_')[2])
        db.cursor.execute("SELECT * FROM bots WHERE id=?", (bot_id,))
        bot_data = db.cursor.fetchone()
        
        if bot_data:
            text = f"""
🤖 BOT DETAILS
╔══════════════════════════════╗
║ Name: {bot_data[2]}            
║ Owner: {bot_data[1]}           
║ Status: {bot_data[5]}            
║ Deploys: {bot_data[7]}           
╚══════════════════════════════╝
"""
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                                reply_markup=bot_controls(bot_id, bot_data[5]))
    
    # Start Bot (Admin)
    elif data.startswith("start_"):
        bot_id = int(data.split('_')[1])
        db.cursor.execute("SELECT bot_name, filename FROM bots WHERE id=?", (bot_id,))
        bot_data = db.cursor.fetchone()
        
        if bot_data:
            file_path = Path(PROJECT_DIR) / bot_data[1]
            if file_path.exists():
                proc = subprocess.Popen(['python', str(file_path)], start_new_session=True)
                db.update_bot_status(bot_id, "Running", proc.pid)
                bot.answer_callback_query(call.id, f"✅ {bot_data[0]} started!")
    
    # Stop Bot (Admin)
    elif data.startswith("stop_"):
        bot_id = int(data.split('_')[1])
        db.cursor.execute("SELECT pid, bot_name FROM bots WHERE id=?", (bot_id,))
        bot_data = db.cursor.fetchone()
        
        if bot_data and bot_data[0]:
            try:
                os.kill(bot_data[0], signal.SIGTERM)
            except:
                pass
            db.update_bot_status(bot_id, "Stopped")
            bot.answer_callback_query(call.id, f"⏸ {bot_data[1]} stopped!")
    
    # Delete Bot (Admin)
    elif data.startswith("delete_"):
        bot_id = int(data.split('_')[1])
        db.cursor.execute("SELECT pid, bot_name, filename FROM bots WHERE id=?", (bot_id,))
        bot_data = db.cursor.fetchone()
        
        if bot_data and bot_data[0]:
            try:
                os.kill(bot_data[0], signal.SIGKILL)
            except:
                pass
        
        file_path = Path(PROJECT_DIR) / bot_data[2]
        if file_path.exists():
            file_path.unlink()
        
        db.delete_bot(bot_id)
        bot.answer_callback_query(call.id, f"🗑 {bot_data[1]} deleted!")
        bot.delete_message(call.message.chat.id, call.message.message_id)
    
    # Export Bot (Admin)
    elif data.startswith("export_"):
        bot_id = int(data.split('_')[1])
        db.cursor.execute("SELECT bot_name, filename FROM bots WHERE id=?", (bot_id,))
        bot_data = db.cursor.fetchone()
        
        if bot_data:
            file_path = Path(PROJECT_DIR) / bot_data[1]
            if file_path.exists():
                with open(file_path, 'rb') as f:
                    bot.send_document(call.message.chat.id, f, caption=f"📦 {bot_data[0]}")
                bot.answer_callback_query(call.id, "Bot exported!")
    
    # Bot Stats (Admin)
    elif data.startswith("stats_"):
        bot_id = int(data.split('_')[1])
        db.cursor.execute("SELECT pid, bot_name, status FROM bots WHERE id=?", (bot_id,))
        bot_data = db.cursor.fetchone()
        
        if bot_data and bot_data[2] == "Running" and bot_data[0]:
            try:
                proc = psutil.Process(bot_data[0])
                cpu = proc.cpu_percent(interval=0.5)
                mem = proc.memory_percent()
                text = f"""
📊 BOT STATS
╔══════════════════════════════╗
║ {bot_data[1]}                   
║ CPU: {cpu:.1f}%                 
║ RAM: {mem:.1f}%                 
║ PID: {bot_data[0]}              
╚══════════════════════════════╝
"""
                bot.send_message(call.message.chat.id, text)
            except:
                bot.answer_callback_query(call.id, "Cannot get stats!")
        else:
            bot.answer_callback_query(call.id, "Bot not running!")
    
    # User My Bot
    elif data.startswith("my_bot_"):
        bot_id = int(data.split('_')[2])
        db.cursor.execute("SELECT * FROM bots WHERE id=?", (bot_id,))
        bot_data = db.cursor.fetchone()
        
        if bot_data:
            text = f"""
🤖 BOT DETAILS
╔══════════════════════════════╗
║ Name: {bot_data[2]}            
║ Status: {bot_data[5]}            
║ Deploys: {bot_data[7]}           
╚══════════════════════════════╝
"""
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                                reply_markup=user_bot_controls(bot_id, bot_data[5]))
    
    # User Start Bot
    elif data.startswith("user_start_"):
        bot_id = int(data.split('_')[2])
        db.cursor.execute("SELECT bot_name, filename FROM bots WHERE id=?", (bot_id,))
        bot_data = db.cursor.fetchone()
        
        if bot_data:
            file_path = Path(PROJECT_DIR) / bot_data[1]
            if file_path.exists():
                proc = subprocess.Popen(['python', str(file_path)], start_new_session=True)
                db.update_bot_status(bot_id, "Running", proc.pid)
                bot.answer_callback_query(call.id, f"✅ {bot_data[0]} started!")
                my_bots(call.message)
    
    # User Stop Bot
    elif data.startswith("user_stop_"):
        bot_id = int(data.split('_')[2])
        db.cursor.execute("SELECT pid, bot_name FROM bots WHERE id=?", (bot_id,))
        bot_data = db.cursor.fetchone()
        
        if bot_data and bot_data[0]:
            try:
                os.kill(bot_data[0], signal.SIGTERM)
            except:
                pass
            db.update_bot_status(bot_id, "Stopped")
            bot.answer_callback_query(call.id, f"⏸ {bot_data[1]} stopped!")
            my_bots(call.message)
    
    # User Delete Bot
    elif data.startswith("user_delete_"):
        bot_id = int(data.split('_')[2])
        db.cursor.execute("SELECT pid, bot_name, filename FROM bots WHERE id=?", (bot_id,))
        bot_data = db.cursor.fetchone()
        
        if bot_data and bot_data[0]:
            try:
                os.kill(bot_data[0], signal.SIGKILL)
            except:
                pass
        
        file_path = Path(PROJECT_DIR) / bot_data[2]
        if file_path.exists():
            file_path.unlink()
        
        db.delete_bot(bot_id)
        bot.answer_callback_query(call.id, f"🗑 {bot_data[1]} deleted!")
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, f"✅ Bot '{bot_data[1]}' deleted!")
    
    # User Export Bot
    elif data.startswith("user_export_"):
        bot_id = int(data.split('_')[2])
        db.cursor.execute("SELECT bot_name, filename FROM bots WHERE id=?", (bot_id,))
        bot_data = db.cursor.fetchone()
        
        if bot_data:
            file_path = Path(PROJECT_DIR) / bot_data[1]
            if file_path.exists():
                with open(file_path, 'rb') as f:
                    bot.send_document(call.message.chat.id, f, caption=f"📦 {bot_data[0]}")
                bot.answer_callback_query(call.id, "Bot exported!")
    
    # User Bot Stats
    elif data.startswith("user_stats_"):
        bot_id = int(data.split('_')[2])
        db.cursor.execute("SELECT pid, bot_name, status FROM bots WHERE id=?", (bot_id,))
        bot_data = db.cursor.fetchone()
        
        if bot_data and bot_data[2] == "Running" and bot_data[0]:
            try:
                proc = psutil.Process(bot_data[0])
                cpu = proc.cpu_percent(interval=0.5)
                mem = proc.memory_percent()
                text = f"""
📊 BOT STATS
╔══════════════════════════════╗
║ {bot_data[1]}                   
║ CPU: {cpu:.1f}%                 
║ RAM: {mem:.1f}%                 
║ PID: {bot_data[0]}              
╚══════════════════════════════╝
"""
                bot.send_message(call.message.chat.id, text)
            except:
                bot.answer_callback_query(call.id, "Cannot get stats!")
        else:
            bot.answer_callback_query(call.id, "Bot not running!")
    
    # Back to My Bots
    elif data == "back_to_mybots":
        my_bots(call.message)
    
    bot.answer_callback_query(call.id)

# ==================== PROCESS FUNCTIONS ====================
def process_add_credits(message, user_id, original_message):
    try:
        amount = int(message.text.strip())
        db.add_credits(user_id, amount)
        bot.send_message(message.chat.id, f"✅ Added {amount} credits!")
        
        user = db.get_user(user_id)
        text = f"""
👤 USER DETAILS
╔══════════════════════════════╗
║ Username: @{user[1]}          
║ Credits: {user[4]} (Updated)   
╚══════════════════════════════╝
"""
        bot.edit_message_text(text, original_message.chat.id, original_message.message_id,
                            reply_markup=user_controls(user_id, user[1], user[4], user[6]))
    except:
        bot.send_message(message.chat.id, "❌ Invalid amount!")

def process_remove_credits(message, user_id, original_message):
    try:
        amount = int(message.text.strip())
        db.remove_credits(user_id, amount)
        bot.send_message(message.chat.id, f"✅ Removed {amount} credits!")
        
        user = db.get_user(user_id)
        text = f"""
👤 USER DETAILS
╔══════════════════════════════╗
║ Username: @{user[1]}          
║ Credits: {user[4]} (Updated)   
╚══════════════════════════════╝
"""
        bot.edit_message_text(text, original_message.chat.id, original_message.message_id,
                            reply_markup=user_controls(user_id, user[1], user[4], user[6]))
    except:
        bot.send_message(message.chat.id, "❌ Invalid amount!")

def process_broadcast(message, original_message):
    broadcast_text = message.text
    users = db.get_all_users()
    
    success = 0
    for user in users:
        try:
            bot.send_message(user[0], f"📢 ANNOUNCEMENT\n\n{broadcast_text}")
            success += 1
            time.sleep(0.05)
        except:
            pass
    
    bot.send_message(original_message.chat.id, f"✅ Broadcast sent to {success} users!")
    start_command(original_message)

# ==================== FLASK ROUTES ====================
@app.route('/')
def home():
    return jsonify({"status": "online", "brand": BRAND_NAME, "version": VERSION})

@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

@app.route('/api/stats')
def api_stats():
    return jsonify(db.get_stats())

# ==================== BACKGROUND TASKS ====================
def cleanup_processes():
    while True:
        try:
            db.cursor.execute("SELECT id, pid FROM bots WHERE status='Running'")
            for bot_id, pid in db.cursor.fetchall():
                if pid:
                    try:
                        os.kill(pid, 0)
                    except OSError:
                        db.update_bot_status(bot_id, "Stopped")
        except:
            pass
        time.sleep(60)

# ==================== MAIN ====================
def run_bot():
    logger.info(f"Starting {BRAND_NAME} v{VERSION}")
    try:
        bot.remove_webhook()
    except:
        pass
    time.sleep(2)
    while True:
        try:
            bot.infinity_polling(timeout=30)
        except Exception as e:
            logger.error(f"Bot error: {e}")
            time.sleep(10)

if __name__ == '__main__':
    threading.Thread(target=cleanup_processes, daemon=True).start()
    threading.Thread(target=run_bot, daemon=True).start()
    app.run(host='0.0.0.0', port=PORT, debug=False)backback_data="admin_bots"),
        types.InlineKeyboardButton("📊 System Statistics", callback_data="admin_stats"),
        types.InlineKeyboardButton("📢 Broadcast Message", callback_data="admin_broadcast"),
        types.InlineKeyboardButton("💾 Backup Database", callback_data="admin_backup"),
        types.InlineKeyboardButton("📜 Activity Logs", callback_data="admin_logs"),
        types.InlineKeyboardButton("💰 Credits Management", callback_data="admin_credits"),
        types.InlineKeyboardButton("⚙️ System Settings", callback_data="admin_settings"),
        types.InlineKeyboardButton("🎁 Referral System", callback_data="admin_referral"),
        types.InlineKeyboardButton("🔙 Back to Main", callback_data="admin_back_main")
    )
    return markup

def users_list_menu(users, page=0, per_page=10):
    total_pages = (len(users) + per_page - 1) // per_page
    start = page * per_page
    end = start + per_page
    page_users = users[start:end]
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for user in page_users:
        status = "🟢" if not user[4] else "🔴"
        markup.add(types.InlineKeyboardButton(
            f"{status} {user[1]} | {user[2]} | {user[3]} credits",
            callback_data=f"user_detail_{user[0]}"
        ))
    
    nav_buttons = []
    if page > 0:
        nav_buttons.append(types.InlineKeyboardButton("◀️ Prev", callback_data=f"users_page_{page-1}"))
    if page < total_pages - 1:
        nav_buttons.append(types.InlineKeyboardButton("Next ▶️", callback_data=f"users_page_{page+1}"))
    
    if nav_buttons:
        markup.add(*nav_buttons)
    
    markup.add(types.InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_back"))
    return markup

def user_detail_menu(user_id, username, credits, plan, is_banned, total_bots, total_deploys):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("💰 Add Credits", callback_data=f"add_credits_{user_id}"),
        types.InlineKeyboardButton("💎 Remove Credits", callback_data=f"remove_credits_{user_id}"),
        types.InlineKeyboardButton("📊 User Bots", callback_data=f"user_bots_{user_id}"),
        types.InlineKeyboardButton("🎯 User Stats", callback_data=f"user_stats_{user_id}")
    )
    
    if is_banned:
        markup.add(types.InlineKeyboardButton("🔓 Unban User", callback_data=f"unban_{user_id}"))
    else:
        markup.add(types.InlineKeyboardButton("🔨 Ban User", callback_data=f"ban_{user_id}"))
    
    markup.add(types.InlineKeyboardButton("🔙 Back to Users", callback_data="back_to_users"))
    return markup

def bots_list_menu(bots, page=0, per_page=10):
    total_pages = (len(bots) + per_page - 1) // per_page
    start = page * per_page
    end = start + per_page
    page_bots = bots[start:end]
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for bot in page_bots:
        status = "🟢" if bot[5] == "Running" else "🔴"
        markup.add(types.InlineKeyboardButton(
            f"{status} {bot[2]} | Owner: {bot[12]} | Status: {bot[5]}",
            callback_data=f"bot_detail_{bot[0]}"
        ))
    
    nav_buttons = []
    if page > 0:
        nav_buttons.append(types.InlineKeyboardButton("◀️ Prev", callback_data=f"bots_page_{page-1}"))
    if page < total_pages - 1:
        nav_buttons.append(types.InlineKeyboardButton("Next ▶️", callback_data=f"bots_page_{page+1}"))
    
    if nav_buttons:
        markup.add(*nav_buttons)
    
    markup.add(types.InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_back"))
    return markup

def bot_detail_menu(bot_id, bot_name, user_id, username, status, deploy_count):
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    if status == "Running":
        markup.add(
            types.InlineKeyboardButton("⏸ Stop Bot", callback_data=f"stop_bot_{bot_id}"),
            types.InlineKeyboardButton("🔄 Restart Bot", callback_data=f"restart_bot_{bot_id}")
        )
    else:
        markup.add(
            types.InlineKeyboardButton("▶️ Start Bot", callback_data=f"start_bot_{bot_id}"),
            types.InlineKeyboardButton("📊 Bot Stats", callback_data=f"bot_stats_{bot_id}")
        )
    
    markup.add(
        types.InlineKeyboardButton("📦 Export Bot", callback_data=f"export_bot_{bot_id}"),
        types.InlineKeyboardButton("🗑 Delete Bot", callback_data=f"delete_bot_{bot_id}"),
        types.InlineKeyboardButton("📝 View Logs", callback_data=f"bot_logs_{bot_id}"),
        types.InlineKeyboardButton("🔙 Back to Bots", callback_data="back_to_bots")
    )
    return markup

def user_bots_menu(bots, user_id, username):
    markup = types.InlineKeyboardMarkup(row_width=1)
    for bot in bots:
        status = "🟢" if bot[5] == "Running" else "🔴"
        markup.add(types.InlineKeyboardButton(
            f"{status} {bot[2]} - {bot[5]}",
            callback_data=f"user_bot_detail_{bot[0]}"
        ))
    markup.add(types.InlineKeyboardButton("🔙 Back to User", callback_data=f"back_to_user_{user_id}"))
    return markup

def bot_control_menu(bot_id, bot_name, status):
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    if status == "Running":
        markup.add(
            types.InlineKeyboardButton("⏸ Stop", callback_data=f"user_stop_{bot_id}"),
            types.InlineKeyboardButton("🔄 Restart", callback_data=f"user_restart_{bot_id}")
        )
    else:
        markup.add(
            types.InlineKeyboardButton("▶️ Start", callback_data=f"user_start_{bot_id}"),
            types.InlineKeyboardButton("📊 Stats", callback_data=f"user_stats_{bot_id}")
        )
    
    markup.add(
        types.InlineKeyboardButton("📦 Export", callback_data=f"user_export_{bot_id}"),
        types.InlineKeyboardButton("🗑 Delete", callback_data=f"user_delete_{bot_id}"),
        types.InlineKeyboardButton("🔙 Back to My Bots", callback_data="back_to_mybots")
    )
    return markup

# ==================== START COMMAND ====================
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    username = message.from_user.username or "User"
    full_name = message.from_user.first_name or "User"
    
    user = db.get_user(user_id)
    if not user:
        db.cursor.execute("INSERT INTO users (id, username, full_name, join_date, last_active) VALUES (?, ?, ?, ?, ?)",
                         (user_id, username, full_name, datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                          datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        db.conn.commit()
        user = db.get_user(user_id)
    
    if is_banned(user_id):
        bot.send_message(message.chat.id, f"❌ You are banned!\nReason: {user[8]}\nContact: {Config.SUPPORT_ID}")
        return
    
    db.cursor.execute("UPDATE users SET last_active=? WHERE id=?", (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), user_id))
    db.conn.commit()
    
    stats = get_system_stats()
    db_stats = db.get_stats()
    
    if is_admin(user_id):
        text = f"""
╔════════════════════════════════════════╗
║      👑 SUPER ADMIN PANEL 👑          ║
╠════════════════════════════════════════╣
║ 👤 <b>ADMIN:</b> @{username}                        
║ 🆔 <b>ID:</b> <code>{user_id}</code>                           
║ 💎 <b>Plan:</b> ENTERPRISE                         
║ 💰 <b>Credits:</b> {user[5]}                            
╠════════════════════════════════════════╣
║ 📊 <b>PLATFORM STATS</b>                        
║ ├ Users: {db_stats['total_users']}                            
║ ├ Active (7d): {db_stats['active_users']}                        
║ ├ Bots: {db_stats['total_bots']}/{db_stats['running_bots']} running       
║ └ Deploys: {db_stats['total_deploys']}                            
╠════════════════════════════════════════╣
║ 🖥️ <b>SERVER STATUS</b>                          
║ ├ CPU: {progress_bar(stats['cpu'])} {stats['cpu']:.0f}%             
║ ├ RAM: {progress_bar(stats['ram'])} {stats['ram']:.0f}%             
║ ├ Disk: {progress_bar(stats['disk'])} {stats['disk']:.0f}%             
║ └ Uptime: {format_uptime(stats['uptime'])}                   
╚════════════════════════════════════════╝

🔧 <b>Use the buttons below to manage everything!</b>
"""
        bot.send_message(message.chat.id, text, reply_markup=admin_main_menu())
        db.log_activity(user_id, "admin_panel", "Opened admin panel")
    else:
        text = f"""
╔════════════════════════════════════════╗
║     {Config.BRAND_NAME}     ║
╠════════════════════════════════════════╣
║ 👤 <b>USER:</b> @{username}                         
║ 💎 <b>Plan:</b> {user[4].upper()}                            
║ 💰 <b>Credits:</b> {user[5]}                            
║ 🤖 <b>Bots:</b> {user[9]}/5                            
╠════════════════════════════════════════╣
║ 🖥️ <b>SYSTEM</b>                                 
║ ├ CPU: {stats['cpu']:.0f}% ({progress_bar(stats['cpu'])})        
║ ├ RAM: {stats['ram']:.0f}% ({progress_bar(stats['ram'])})        
║ └ Uptime: {format_uptime(stats['uptime'])}                   
╠════════════════════════════════════════╣
║ 💡 <b>Quick Actions:</b>                      
║ • Upload your bot to get started!       
║ • Use the buttons below to manage       
╚════════════════════════════════════════╝
"""
        bot.send_message(message.chat.id, text, reply_markup=main_menu(user_id))
        db.log_activity(user_id, "start", "Started bot")

# ==================== USER MENU HANDLERS ====================
@bot.message_handler(func=lambda m: m.text == "👑 Admin Panel")
def admin_panel_handler(message):
    if is_admin(message.from_user.id):
        start_command(message)
    else:
        bot.reply_to(message, "❌ Admin access only!")

@bot.message_handler(func=lambda m: m.text == "📤 Upload Bot")
def upload_bot(message):
    user_id = message.from_user.id
    
    if is_banned(user_id):
        bot.reply_to(message, "❌ You are banned!")
        return
    
    user = db.get_user(user_id)
    if user[9] >= 5 and user[4] == 'free':
        bot.reply_to(message, "❌ Bot limit reached! Upgrade to premium for more bots.")
        return
    
    msg = bot.reply_to(message, "📤 Send your Python bot file (.py)\nMax size: 50MB")
    bot.register_next_step_handler(msg, process_upload)

def process_upload(message):
    if not message.document:
        bot.reply_to(message, "❌ Please send a file!")
        return
    
    if not message.document.file_name.endswith('.py'):
        bot.reply_to(message, "❌ Only .py files are allowed!")
        return
    
    if message.document.file_size > 50 * 1024 * 1024:
        bot.reply_to(message, "❌ File too large! Max 50MB")
        return
    
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded = bot.download_file(file_info.file_path)
        
        filename = f"{uuid.uuid4().hex[:8]}_{message.document.file_name}"
        file_path = Path(Config.PROJECT_DIR) / filename
        file_path.write_bytes(downloaded)
        
        msg = bot.reply_to(message, "✅ Uploaded!\n\nEnter bot name:")
        bot.register_next_step_handler(msg, save_bot, filename, message.document.file_size)
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

def save_bot(message, filename, file_size):
    user_id = message.from_user.id
    bot_name = message.text.strip()[:50]
    
    bot_id = db.add_bot(user_id, bot_name, filename, file_size)
    bot.send_message(message.chat.id, 
                    f"✅ Bot '{bot_name}' saved successfully!\n\n"
                    f"📁 File: {filename}\n"
                    f"📦 Size: {file_size / 1024:.1f} KB\n\n"
                    f"Use '⚡ Deploy Bot' to start it.",
                    reply_markup=main_menu(user_id))
    db.log_activity(user_id, "upload_bot", f"Uploaded bot: {bot_name}")

@bot.message_handler(func=lambda m: m.text == "🤖 My Bots")
def my_bots(message):
    user_id = message.from_user.id
    bots = db.get_user_bots(user_id)
    
    if not bots:
        bot.reply_to(message, "🤖 No bots found!\nUse 'Upload Bot' to create one.")
        return
    
    text = f"🤖 <b>YOUR BOTS</b> ({len(bots)})\n╔════════════════════════════════════════╗\n"
    
    for i, b in enumerate(bots, 1):
        status_icon = "🟢" if b[6] == "Running" else "🔴"
        text += f"║ {i}. {status_icon} <b>{b[2]}</b>\n"
        text += f"║    Status: {b[6]} | Deploys: {b[11]}\n"
        text += "╠────────────────────────────────────╣\n"
    
    text += "╚════════════════════════════════════════╝\n\nSelect a bot to manage:"
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b in bots:
        markup.add(types.InlineKeyboardButton(
            f"{'🟢' if b[6] == 'Running' else '🔴'} {b[2]}",
            callback_data=f"my_bot_{b[0]}"
        ))
    
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "⚡ Deploy Bot")
def deploy_bot(message):
    user_id = message.from_user.id
    bots = db.get_user_bots(user_id)
    available = [b for b in bots if b[6] != "Running"]
    
    if not available:
        bot.reply_to(message, "📭 No bots available for deployment!\nUpload a bot first.")
        return
    
    text = "⚡ <b>DEPLOY BOT</b>\n╔════════════════════════════════════════╗\n"
    for i, b in enumerate(available, 1):
        text += f"║ {i}. <b>{b[2]}</b>\n"
        text += "╠────────────────────────────────────╣\n"
    
    text += "╚════════════════════════════════════════╝\n\nEnter number to deploy:"
    
    msg = bot.reply_to(message, text)
    bot.register_next_step_handler(msg, process_deploy, available)

def process_deploy(message, bots):
    try:
        choice = int(message.text.strip()) - 1
        if choice < 0 or choice >= len(bots):
            raise ValueError
        
        bot_data = bots[choice]
        bot_id = bot_data[0]
        bot_name = bot_data[2]
        filename = bot_data[3]
        file_path = Path(Config.PROJECT_DIR) / filename
        
        if not file_path.exists():
            bot.reply_to(message, "❌ File not found!")
            return
        
        proc = subprocess.Popen(['python', str(file_path)], 
                               start_new_session=True,
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
        
        db.update_bot_status(bot_id, "Running", proc.pid)
        
        bot.reply_to(message, f"✅ <b>{bot_name}</b> is RUNNING!\nPID: <code>{proc.pid}</code>")
        db.log_activity(message.from_user.id, "deploy_bot", f"Deployed bot: {bot_name}")
        
    except:
        bot.reply_to(message, "❌ Invalid selection!")

@bot.message_handler(func=lambda m: m.text == "📊 Dashboard")
def dashboard(message):
    user_id = message.from_user.id
    user = db.get_user(user_id)
    bots = db.get_user_bots(user_id)
    stats = get_system_stats()
    
    running = len([b for b in bots if b[6] == "Running"])
    total_deploys = sum([b[11] for b in bots])
    
    text = f"""
╔════════════════════════════════════════╗
║           📊 DASHBOARD                ║
╠════════════════════════════════════════╣
║ 👤 <b>ACCOUNT</b>                            
║ ├ Username: @{user[1]}                        
║ ├ Plan: {user[4].upper()}                            
║ ├ Credits: {user[5]}                            
║ └ Joined: {user[3][:10]}                          
╠════════════════════════════════════════╣
║ 🤖 <b>BOTS</b>                                
║ ├ Total: {len(bots)}                            
║ ├ Running: {running}                            
║ ├ Stopped: {len(bots) - running}                        
║ └ Total Deploys: {total_deploys}                        
╠════════════════════════════════════════╣
║ 🖥️ <b>SYSTEM</b>                               
║ ├ CPU: {stats['cpu']:.1f}%                            
║ ├ RAM: {stats['ram']:.1f}%                            
║ └ Uptime: {format_uptime(stats['uptime'])}                   
╚════════════════════════════════════════╝
"""
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: m.text == "💰 Buy Credits")
def buy_credits(message):
    text = """
╔════════════════════════════════════════╗
║           💰 BUY CREDITS              ║
╠════════════════════════════════════════╣
║ <b>💎 CREDIT PACKAGES</b>                   
║                                         
║ 100 Credits  →  $4.99                  
║ 500 Credits  →  $19.99                 
║ 1000 Credits →  $34.99                 
║ 5000 Credits →  $149.99                
╠════════════════════════════════════════╣
║ <b>💰 PREMIUM PLANS</b>                    
║                                         
║ BASIC (20 bots)    →  $9.99/month      
║ PRO (50 bots)      →  $19.99/month     
║ ENTERPRISE (999 bots) →  $49.99/month  
╠════════════════════════════════════════╣
║ 💳 <b>PAYMENT METHODS</b>                  
║ • USDT (TRC20/BEP20)                   
║ • Bitcoin / Ethereum                   
║ • bKash / Nagad / Rocket (BD)          
║ • Bank Transfer                        
╠════════════════════════════════════════╣
║ 💬 Contact @aurponmodz to purchase!    
╚════════════════════════════════════════╝
"""
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: m.text == "❓ Help")
def help_command(message):
    text = """
╔════════════════════════════════════════╗
║              ❓ HELP                   ║
╠════════════════════════════════════════╣
║ <b>📤 UPLOAD BOT</b>                        
║ Upload your Python bot file (.py)     
║                                         
║ <b>🤖 MY BOTS</b>                           
║ View and manage your bots             
║                                         
║ <b>⚡ DEPLOY BOT</b>                        
║ Start your uploaded bot               
║                                         
║ <b>📊 DASHBOARD</b>                        
║ View your statistics                  
║                                         
║ <b>💰 BUY CREDITS</b>                      
║ Purchase credits or upgrade plan      
╠════════════════════════════════════════╣
║ 💬 <b>SUPPORT</b>                            
║ Contact: {Config.SUPPORT_ID}                 
╚════════════════════════════════════════╝
"""
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: m.text == "ℹ️ About")
def about_command(message):
    stats = db.get_stats()
    
    text = f"""
╔════════════════════════════════════════╗
║            ℹ️ ABOUT                   ║
╠════════════════════════════════════════╣
║ {Config.BRAND_NAME}                       
║ Version: {Config.VERSION}                     
╠════════════════════════════════════════╣
║ <b>✨ FEATURES</b>                           
║ ✓ Easy bot deployment                 
║ ✓ Real-time monitoring                
║ ✓ Credit system                       
║ ✓ Premium plans                       
║ ✓ 24/7 hosting                        
╠════════════════════════════════════════╣
║ <b>📊 PLATFORM STATS</b>                    
║ ├ Users: {stats['total_users']}                            
║ ├ Bots: {stats['total_bots']}                            
║ └ Running: {stats['running_bots']}                            
╠════════════════════════════════════════╣
║ 👨‍💻 <b>DEVELOPER</b>                         
║ @aurponmodz                           
║                                         
║ 💬 <b>SUPPORT</b>                            
║ {Config.SUPPORT_ID}                         
╚════════════════════════════════════════╝
"""
    bot.send_message(message.chat.id, text)

# ==================== ADMIN CALLBACK HANDLERS ====================
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    data = call.data
    
    # ========== ADMIN MAIN MENU ==========
    if data == "admin_back_main":
        start_command(call.message)
    
    elif data == "admin_back":
        bot.edit_message_text("🔧 Admin Panel", call.message.chat.id, call.message.message_id,
                            reply_markup=admin_main_menu())
    
    # ========== USERS MANAGEMENT ==========
    elif data == "admin_users":
        users = db.get_all_users()
        text = f"👥 <b>USERS MANAGEMENT</b>\n╔════════════════════════════════════════╗\n"
        text += f"║ Total Users: {len(users)}\n╚════════════════════════════════════════╝\n\nSelect a user to manage:"
        
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                            reply_markup=users_list_menu(users))
    
    elif data.startswith("users_page_"):
        page = int(data.split('_')[2])
        users = db.get_all_users()
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id,
                                     reply_markup=users_list_menu(users, page))
    
    elif data == "back_to_users":
        users = db.get_all_users()
        text = f"👥 <b>USERS MANAGEMENT</b>\n╔════════════════════════════════════════╗\n"
        text += f"║ Total Users: {len(users)}\n╚════════════════════════════════════════╝\n\nSelect a user to manage:"
        
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                            reply_markup=users_list_menu(users))
    
    elif data.startswith("user_detail_"):
        user_id = int(data.split('_')[2])
        user = db.get_user(user_id)
        
        if user:
            text = f"""
👤 <b>USER DETAILS</b>
╔════════════════════════════════════════╗
║ <b>ID:</b> <code>{user[0]}</code>                           
║ <b>Username:</b> @{user[1]}                        
║ <b>Name:</b> {user[2]}                        
║ <b>Plan:</b> {user[4].upper()}                            
║ <b>Credits:</b> {user[5]}                            
║ <b>Status:</b> {'🔴 BANNED' if user[7] else '🟢 ACTIVE'}                
║ <b>Total Bots:</b> {user[9]}                            
║ <b>Total Deploys:</b> {user[10]}                         
║ <b>Joined:</b> {user[3][:10]}                          
║ <b>Last Active:</b> {user[11][:10] if user[11] else 'Never'}                   
╚════════════════════════════════════════╝
"""
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                                reply_markup=user_detail_menu(user_id, user[1], user[5], user[4], user[7], user[9], user[10]))
    
    # ========== ADD/REMOVE CREDITS ==========
    elif data.startswith("add_credits_"):
        user_id = int(data.split('_')[2])
        msg = bot.send_message(call.message.chat.id, f"💰 Enter amount of credits to add for user {user_id}:")
        bot.register_next_step_handler(msg, process_add_credits, user_id, call.message)
    
    elif data.startswith("remove_credits_"):
        user_id = int(data.split('_')[2])
        msg = bot.send_message(call.message.chat.id, f"💎 Enter amount of credits to remove from user {user_id}:")
        bot.register_next_step_handler(msg, process_remove_credits, user_id, call.message)
    
    # ========== BAN/UNBAN ==========
    elif data.startswith("ban_"):
        user_id = int(data.split('_')[1])
        msg = bot.send_message(call.message.chat.id, f"🔨 Enter ban reason for user {user_id}:")
        bot.register_next_step_handler(msg, process_ban_user, user_id, call.message)
    
    elif data.startswith("unban_"):
        user_id = int(data.split('_')[1])
        db.unban_user(user_id)
        bot.answer_callback_query(call.id, "✅ User unbanned!")
        
        user = db.get_user(user_id)
        text = f"""
👤 <b>USER DETAILS</b>
╔════════════════════════════════════════╗
║ <b>ID:</b> <code>{user[0]}</code>                           
║ <b>Username:</b> @{user[1]}                        
║ <b>Status:</b> 🟢 ACTIVE                         
╚════════════════════════════════════════╝
"""
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                            reply_markup=user_detail_menu(user_id, user[1], user[5], user[4], user[7], user[9], user[10]))
    
    # ========== USER BOTS ==========
    elif data.startswith("user_bots_"):
        user_id = int(data.split('_')[2])
        user = db.get_user(user_id)
        bots = db.get_user_bots(user_id)
        
        if not bots:
            bot.answer_callback_query(call.id, "No bots found for this user!")
            return
        
        text = f"🤖 <b>BOTS OF @{user[1]}</b> ({len(bots)})\n\n"
        
        markup = user_bots_menu(bots, user_id, user[1])
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    
    elif data.startswith("user_bot_detail_"):
        bot_id = int(data.split('_')[3])
        db.cursor.execute("SELECT * FROM bots WHERE id=?", (bot_id,))
        bot_data = db.cursor.fetchone()
        
        if bot_data:
            text = f"""
🤖 <b>BOT DETAILS</b>
╔════════════════════════════════════════╗
║ <b>Name:</b> {bot_data[2]}                            
║ <b>File:</b> {bot_data[3]}                            
║ <b>Size:</b> {bot_data[4] / 1024:.1f} KB                       
║ <b>Status:</b> {'🟢 RUNNING' if bot_data[6] == 'Running' else '🔴 STOPPED'}          
║ <b>Deploys:</b> {bot_data[11]}                           
║ <b>Started:</b> {bot_data[7][:10] if bot_data[7] else 'Never'}                 
╚════════════════════════════════════════╝
"""
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                                reply_markup=bot_detail_menu(bot_id, bot_data[2], bot_data[1], 
                                                            bot_data[1], bot_data[6], bot_data[11]))
    
    elif data.startswith("back_to_user_"):
        user_id = int(data.split('_')[3])
        user = db.get_user(user_id)
        
        text = f"""
👤 <b>USER DETAILS</b>
╔════════════════════════════════════════╗
║ <b>ID:</b> <code>{user[0]}</code>                           
║ <b>Username:</b> @{user[1]}                        
║ <b>Plan:</b> {user[4].upper()}                            
║ <b>Credits:</b> {user[5]}                            
║ <b>Status:</b> {'🔴 BANNED' if user[7] else '🟢 ACTIVE'}                
║ <b>Total Bots:</b> {user[9]}                            
║ <b>Total Deploys:</b> {user[10]}                         
╚════════════════════════════════════════╝
"""
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                            reply_markup=user_detail_menu(user_id, user[1], user[5], user[4], user[7], user[9], user[10]))
    
    # ========== USER STATS ==========
    elif data.startswith("user_stats_"):
        user_id = int(data.split('_')[2])
        user = db.get_user(user_id)
        bots = db.get_user_bots(user_id)
        
        running = len([b for b in bots if b[6] == "Running"])
        
        text = f"""
📊 <b>USER STATISTICS</b>
╔════════════════════════════════════════╗
║ <b>@{user[1]}</b>                               
╠════════════════════════════════════════╣
║ <b>📈 BOT STATS</b>                           
║ ├ Total Bots: {len(bots)}                            
║ ├ Running: {running}                            
║ └ Stopped: {len(bots) - running}                        
╠════════════════════════════════════════╣
║ <b>💰 ACCOUNT</b>                             
║ ├ Credits: {user[5]}                            
║ ├ Plan: {user[4].upper()}                            
║ └ Total Deploys: {user[10]}                         
╚════════════════════════════════════════╝
"""
        bot.send_message(call.message.chat.id, text)
        bot.answer_callback_query(call.id)
    
    # ========== BOTS MANAGEMENT ==========
    elif data == "admin_bots":
        bots = db.get_all_bots()
        text = f"🤖 <b>BOTS MANAGEMENT</b>\n╔════════════════════════════════════════╗\n"
        text += f"║ Total Bots: {len(bots)}\n╚════════════════════════════════════════╝\n\nSelect a bot to manage:"
        
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                            reply_markup=bots_list_menu(bots))
    
    elif data.startswith("bots_page_"):
        page = int(data.split('_')[2])
        bots = db.get_all_bots()
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id,
                                     reply_markup=bots_list_menu(bots, page))
    
    elif data == "back_to_bots":
        bots = db.get_all_bots()
        text = f"🤖 <b>BOTS MANAGEMENT</b>\n╔════════════════════════════════════════╗\n"
        text += f"║ Total Bots: {len(bots)}\n╚════════════════════════════════════════╝\n\nSelect a bot to manage:"
        
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                            reply_markup=bots_list_menu(bots))
    
    elif data.startswith("bot_detail_"):
        bot_id = int(data.split('_')[2])
        db.cursor.execute("SELECT b.*, u.username FROM bots b LEFT JOIN users u ON b.user_id = u.id WHERE b.id=?", (bot_id,))
        bot_data = db.cursor.fetchone()
        
        if bot_data:
            text = f"""
🤖 <b>BOT DETAILS</b>
╔════════════════════════════════════════╗
║ <b>Name:</b> {bot_data[2]}                            
║ <b>Owner:</b> @{bot_data[12]}                        
║ <b>File:</b> {bot_data[3]}                            
║ <b>Size:</b> {bot_data[4] / 1024:.1f} KB                       
║ <b>Status:</b> {'🟢 RUNNING' if bot_data[6] == 'Running' else '🔴 STOPPED'}          
║ <b>Deploys:</b> {bot_data[11]}                           
║ <b>Started:</b> {bot_data[7][:10] if bot_data[7] else 'Never'}                 
║ <b>Last Active:</b> {bot_data[8][:10] if bot_data[8] else 'Never'}                 
╚════════════════════════════════════════╝
"""
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                                reply_markup=bot_detail_menu(bot_id, bot_data[2], bot_data[1], 
                                                            bot_data[12], bot_data[6], bot_data[11]))
    
    # ========== BOT ACTIONS (START/STOP/RESTART/DELETE/EXPORT) ==========
    elif data.startswith("start_bot_"):
        bot_id = int(data.split('_')[2])
        db.cursor.execute("SELECT bot_name, filename FROM bots WHERE id=?", (bot_id,))
        bot_data = db.cursor.fetchone()
        
        if bot_data:
            file_path = Path(Config.PROJECT_DIR) / bot_data[1]
            if file_path.exists():
                proc = subprocess.Popen(['python', str(file_path)], start_new_session=True)
                db.update_bot_status(bot_id, "Running", proc.pid)
                bot.answer_callback_query(call.id, f"✅ {bot_data[0]} started!")
                
                # Refresh
                db.cursor.execute("SELECT b.*, u.username FROM bots b LEFT JOIN users u ON b.user_id = u.id WHERE b.id=?", (bot_id,))
                new_data = db.cursor.fetchone()
                text = f"""
🤖 <b>BOT DETAILS</b>
╔════════════════════════════════════════╗
║ <b>Name:</b> {new_data[2]}                            
║ <b>Owner:</b> @{new_data[12]}                        
║ <b>Status:</b> 🟢 RUNNING                         
║ <b>Deploys:</b> {new_data[11]}                           
╚════════════════════════════════════════╝
"""
                bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                                    reply_markup=bot_detail_menu(bot_id, new_data[2], new_data[1], 
                                                                new_data[12], "Running", new_data[11]))
    
    elif data.startswith("stop_bot_"):
        bot_id = int(data.split('_')[2])
        db.cursor.execute("SELECT pid, bot_name FROM bots WHERE id=?", (bot_id,))
        bot_data = db.cursor.fetchone()
        
        if bot_data and bot_data[0]:
            try:
                os.kill(bot_data[0], signal.SIGTERM)
            except:
                pass
            db.update_bot_status(bot_id, "Stopped")
            bot.answer_callback_query(call.id, f"⏸ {bot_data[1]} stopped!")
            
            # Refresh
            db.cursor.execute("SELECT b.*, u.username FROM bots b LEFT JOIN users u ON b.user_id = u.id WHERE b.id=?", (bot_id,))
            new_data = db.cursor.fetchone()
            text = f"""
🤖 <b>BOT DETAILS</b>
╔════════════════════════════════════════╗
║ <b>Name:</b> {new_data[2]}                            
║ <b>Owner:</b> @{new_data[12]}                        
║ <b>Status:</b> 🔴 STOPPED                         
║ <b>Deploys:</b> {new_data[11]}                           
╚════════════════════════════════════════╝
"""
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                                reply_markup=bot_detail_menu(bot_id, new_data[2], new_data[1], 
                                                            new_data[12], "Stopped", new_data[11]))
    
    elif data.startswith("restart_bot_"):
        bot_id = int(data.split('_')[2])
        db.cursor.execute("SELECT pid, bot_name, filename FROM bots WHERE id=?", (bot_id,))
        bot_data = db.cursor.fetchone()
        
        if bot_data and bot_data[0]:
            try:
                os.kill(bot_data[0], signal.SIGTERM)
            except:
                pass
        
        time.sleep(1)
        
        file_path = Path(Config.PROJECT_DIR) / bot_data[2]
        if file_path.exists():
            proc = subprocess.Popen(['python', str(file_path)], start_new_session=True)
            db.update_bot_status(bot_id, "Running", proc.pid)
            bot.answer_callback_query(call.id, f"🔄 {bot_data[1]} restarted!")
            
            # Refresh
            db.cursor.execute("SELECT b.*, u.username FROM bots b LEFT JOIN users u ON b.user_id = u.id WHERE b.id=?", (bot_id,))
            new_data = db.cursor.fetchone()
            text = f"""
🤖 <b>BOT DETAILS</b>
╔════════════════════════════════════════╗
║ <b>Name:</b> {new_data[2]}                            
║ <b>Owner:</b> @{new_data[12]}                        
║ <b>Status:</b> 🟢 RUNNING                         
║ <b>Deploys:</b> {new_data[11]}                           
╚════════════════════════════════════════╝
"""
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                                reply_markup=bot_detail_menu(bot_id, new_data[2], new_data[1], 
                                                            new_data[12], "Running", new_data[11]))
    
    elif data.startswith("delete_bot_"):
        bot_id = int(data.split('_')[2])
        db.cursor.execute("SELECT pid, bot_name, filename FROM bots WHERE id=?", (bot_id,))
        bot_data = db.cursor.fetchone()
        
        if bot_data and bot_data[0]:
            try:
                os.kill(bot_data[0], signal.SIGKILL)
            except:
                pass
        
        file_path = Path(Config.PROJECT_DIR) / bot_data[2]
        if file_path.exists():
            file_path.unlink()
        
        db.delete_bot(bot_id)
        bot.answer_callback_query(call.id, f"🗑 {bot_data[1]} deleted!")
        
        # Refresh bots list
        bots = db.get_all_bots()
        text = f"🤖 <b>BOTS MANAGEMENT</b>\n╔════════════════════════════════════════╗\n"
        text += f"║ Total Bots: {len(bots)}\n╚════════════════════════════════════════╝\n\nSelect a bot to manage:"
        
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                            reply_markup=bots_list_menu(bots))
    
    elif data.startswith("export_bot_"):
        bot_id = int(data.split('_')[2])
        db.cursor.execute("SELECT bot_name, filename FROM bots WHERE id=?", (bot_id,))
        bot_data = db.cursor.fetchone()
        
        if bot_data:
            file_path = Path(Config.PROJECT_DIR) / bot_data[1]
            if file_path.exists():
                with open(file_path, 'rb') as f:
                    bot.send_document(call.message.chat.id, f, caption=f"📦 Exported: {bot_data[0]}")
                bot.answer_callback_query(call.id, "Bot exported!")
    
    elif data.startswith("bot_stats_"):
        bot_id = int(data.split('_')[2])
        db.cursor.execute("SELECT pid, bot_name, status FROM bots WHERE id=?", (bot_id,))
        bot_data = db.cursor.fetchone()
        
        if bot_data and bot_data[2] == "Running" and bot_data[0]:
            try:
                proc = psutil.Process(bot_data[0])
                cpu = proc.cpu_percent(interval=0.5)
                mem = proc.memory_percent()
                text = f"""
📊 <b>BOT STATISTICS</b>
╔════════════════════════════════════════╗
║ <b>{bot_data[1]}</b>                               
╠════════════════════════════════════════╣
║ 🖥️ <b>RESOURCE USAGE</b>                     
║ ├ CPU: {progress_bar(cpu)} {cpu:.1f}%               
║ ├ RAM: {progress_bar(mem)} {mem:.1f}%               
║ ├ PID: <code>{bot_data[0]}</code>                         
║ └ Status: 🟢 Running                      
╠════════════════════════════════════════╣
║ 📈 <b>PERFORMANCE</b>                         
║ ├ Memory: {format_bytes(proc.memory_info().rss)}          
║ └ Threads: {proc.num_threads()}                          
╚════════════════════════════════════════╝
"""
                bot.send_message(call.message.chat.id, text)
            except:
                bot.answer_callback_query(call.id, "Cannot get stats!")
        else:
            bot.answer_callback_query(call.id, "Bot is not running!")
    
    # ========== ADMIN STATS ==========
    elif data == "admin_stats":
        stats = db.get_stats()
        system = get_system_stats()
        
        text = f"""
📊 <b>SYSTEM STATISTICS</b>
╔════════════════════════════════════════╗
║ 👥 <b>USERS</b>                                 
║ ├ Total: {stats['total_users']}                            
║ ├ Active (7d): {stats['active_users']}                        
║ └ Inactive: {stats['total_users'] - stats['active_users']}                    
╠════════════════════════════════════════╣
║ 🤖 <b>BOTS</b>                                  
║ ├ Total: {stats['total_bots']}                            
║ ├ Running: {stats['running_bots']}                            
║ ├ Stopped: {stats['total_bots'] - stats['running_bots']}                        
║ └ Total Deploys: {stats['total_deploys']}                            
╠════════════════════════════════════════╣
║ 🖥️ <b>SERVER</b>                                 
║ ├ CPU: {system['cpu']:.1f}% ({progress_bar(system['cpu'])})          
║ ├ RAM: {system['ram']:.1f}% ({progress_bar(system['ram'])})
║ ├ Used: {format_bytes(system['ram_used'])}/{format_bytes(system['ram_total'])}
║ ├ Disk: {system['disk']:.1f}% ({progress_bar(system['disk'])})
║ └ Uptime: {format_uptime(system['uptime'])}                   
╚════════════════════════════════════════╝
"""
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                            reply_markup=types.InlineKeyboardMarkup().add(
                                types.InlineKeyboardButton("🔙 Back", callback_data="admin_back")))
    
    # ========== ADMIN BROADCAST ==========
    elif data == "admin_broadcast":
        msg = bot.send_message(call.message.chat.id, "📢 Enter your broadcast message:")
        bot.register_next_step_handler(msg, process_broadcast, call.message)
    
    # ========== ADMIN BACKUP ==========
    elif data == "admin_backup":
        backup_path = Path(Config.DB_NAME)
        if backup_path.exists():
            with open(backup_path, 'rb') as f:
                bot.send_document(call.message.chat.id, f, 
                                caption=f"💾 Database Backup\nSize: {backup_path.stat().st_size / 1024:.2f} KB\nDate: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            bot.answer_callback_query(call.id, "Backup sent!")
        else:
            bot.answer_callback_query(call.id, "Database file not found!")
    
    # ========== ADMIN LOGS ==========
    elif data == "admin_logs":
        db.cursor.execute("SELECT action, user_id, details, created_at FROM activity_logs ORDER BY id DESC LIMIT 20")
        logs = db.cursor.fetchall()
        
        text = "📜 <b>ACTIVITY LOGS</b>\n╔════════════════════════════════════════╗\n"
        for log in logs:
            text += f"║ [{log[3][:16]}] {log[0]}\n"
            text += f"║   User: {log[1]} | {log[2][:30]}\n"
            text += "╠────────────────────────────────────╣\n"
        
        text += "╚════════════════════════════════════════╝"
        
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                            reply_markup=types.InlineKeyboardMarkup().add(
                                types.InlineKeyboardButton("🔙 Back", callback_data="admin_back")))
    
    # ========== ADMIN CREDITS ==========
    elif data == "admin_credits":
        text = """
💰 <b>CREDITS MANAGEMENT</b>
╔════════════════════════════════════════╗
║ <b>Commands:</b>                          
║                                         
║ • /add_credits <user_id> <amount>      
║ • /remove_credits <user_id> <amount>   
║ • /check_credits <user_id>             
║                                         
║ <b>Example:</b>                            
║ /add_credits 6487613131 100            
╚════════════════════════════════════════╝
"""
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                            reply_markup=types.InlineKeyboardMarkup().add(
                                types.InlineKeyboardButton("🔙 Back", callback_data="admin_back")))
    
    # ========== ADMIN SETTINGS ==========
    elif data == "admin_settings":
        text = """
⚙️ <b>SYSTEM SETTINGS</b>
╔════════════════════════════════════════╗
║ <b>Current Settings:</b>                   
║                                         
║ • Maintenance Mode: OFF                
║ • Auto Backup: ON (Daily)              
║ • Max File Size: 50MB                  
║ • Free Bot Limit: 5                    
║ • Default Credits: 100                 
╠════════════════════════════════════════╣
║ <b>Contact admin to change settings</b>    
╚════════════════════════════════════════╝
"""
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                            reply_markup=types.InlineKeyboardMarkup().add(
                                types.InlineKeyboardButton("🔙 Back", callback_data="admin_back")))
    
    # ========== ADMIN REFERRAL ==========
    elif data == "admin_referral":
        text = """
🎁 <b>REFERRAL SYSTEM</b>
╔════════════════════════════════════════╗
║ <b>Current Settings:</b>                   
║                                         
║ • Referral Bonus: 50 credits           
║ • Referred Bonus: 25 credits           
║ • Total Referrals: Calculated          
╠════════════════════════════════════════╣
║ <b>Top Referrers:</b>                      
║ • Coming soon...                       
╚════════════════════════════════════════╝
"""
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                            reply_markup=types.InlineKeyboardMarkup().add(
                                types.InlineKeyboardButton("🔙 Back", callback_data="admin_back")))
    
    # ========== USER MY BOTS ==========
    elif data.startswith("my_bot_"):
        bot_id = int(data.split('_')[2])
        db.cursor.execute("SELECT * FROM bots WHERE id=?", (bot_id,))
        bot_data = db.cursor.fetchone()
        
        if bot_data:
            uptime = "N/A"
            if bot_data[6] == "Running" and bot_data[7]:
                try:
                    start = datetime.strptime(bot_data[7], '%Y-%m-%d %H:%M:%S')
                    uptime = str(datetime.now() - start).split('.')[0]
                except:
                    pass
            
            text = f"""
🤖 <b>BOT DETAILS</b>
╔════════════════════════════════════════╗
║ <b>Name:</b> {bot_data[2]}                            
║ <b>File:</b> {bot_data[3]}                            
║ <b>Size:</b> {bot_data[4] / 1024:.1f} KB                       
║ <b>Status:</b> {'🟢 RUNNING' if bot_data[6] == 'Running' else '🔴 STOPPED'}          
║ <b>Deploys:</b> {bot_data[11]}                           
║ <b>Started:</b> {bot_data[7][:10] if bot_data[7] else 'Never'}                 
║ <b>Uptime:</b> {uptime}                            
╚════════════════════════════════════════╝
"""
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                                reply_markup=bot_control_menu(bot_id, bot_data[2], bot_data[6]))
    
    elif data == "back_to_mybots":
        user_id = call.from_user.id
        bots = db.get_user_bots(user_id)
        
        text = f"🤖 <b>YOUR BOTS</b> ({len(bots)})\n╔════════════════════════════════════════╗\n"
        
        for i, b in enumerate(bots, 1):
            status_icon = "🟢" if b[6] == "Running" else "🔴"
            text += f"║ {i}. {status_icon} <b>{b[2]}</b>\n"
            text += f"║    Status: {b[6]} | Deploys: {b[11]}\n"
            text += "╠────────────────────────────────────╣\n"
        
        text += "╚════════════════════════════════════════╝\n\nSelect a bot to manage:"
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        for b in bots:
            markup.add(types.InlineKeyboardButton(
                f"{'🟢' if b[6] == 'Running' else '🔴'} {b[2]}",
                callback_data=f"my_bot_{b[0]}"
            ))
        
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    
    # ========== USER BOT ACTIONS ==========
    elif data.startswith("user_start_"):
        bot_id = int(data.split('_')[2])
        db.cursor.execute("SELECT bot_name, filename, user_id FROM bots WHERE id=?", (bot_id,))
        bot_data = db.cursor.fetchone()
        
        if bot_data and bot_data[2] == call.from_user.id:
            file_path = Path(Config.PROJECT_DIR) / bot_data[1]
            if file_path.exists():
                proc = subprocess.Popen(['python', str(file_path)], start_new_session=True)
                db.update_bot_status(bot_id, "Running", proc.pid)
                bot.answer_callback_query(call.id, f"✅ {bot_data[0]} started!")
                
                db.cursor.execute("SELECT * FROM bots WHERE id=?", (bot_id,))
                new_data = db.cursor.fetchone()
                text = f"""
🤖 <b>BOT DETAILS</b>
╔════════════════════════════════════════╗
║ <b>Name:</b> {new_data[2]}                            
║ <b>Status:</b> 🟢 RUNNING                         
║ <b>Deploys:</b> {new_data[11]}                           
╚════════════════════════════════════════╝
"""
                bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                                    reply_markup=bot_control_menu(bot_id, new_data[2], "Running"))
    
    elif data.startswith("user_stop_"):
        bot_id = int(data.split('_')[2])
        db.cursor.execute("SELECT pid, bot_name FROM bots WHERE id=?", (bot_id,))
        bot_data = db.cursor.fetchone()
        
        if bot_data and bot_data[0]:
            try:
                os.kill(bot_data[0], signal.SIGTERM)
            except:
                pass
            db.update_bot_status(bot_id, "Stopped")
            bot.answer_callback_query(call.id, f"⏸ {bot_data[1]} stopped!")
            
            db.cursor.execute("SELECT * FROM bots WHERE id=?", (bot_id,))
            new_data = db.cursor.fetchone()
            text = f"""
🤖 <b>BOT DETAILS</b>
╔════════════════════════════════════════╗
║ <b>Name:</b> {new_data[2]}                            
║ <b>Status:</b> 🔴 STOPPED                         
║ <b>Deploys:</b> {new_data[11]}                           
╚════════════════════════════════════════╝
"""
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                                reply_markup=bot_control_menu(bot_id, new_data[2], "Stopped"))
    
    elif data.startswith("user_restart_"):
        bot_id = int(data.split('_')[2])
        db.cursor.execute("SELECT pid, bot_name, filename FROM bots WHERE id=?", (bot_id,))
        bot_data = db.cursor.fetchone()
        
        if bot_data and bot_data[0]:
            try:
                os.kill(bot_data[0], signal.SIGTERM)
            except:
                pass
        
        time.sleep(1)
        
        file_path = Path(Config.PROJECT_DIR) / bot_data[2]
        if file_path.exists():
            proc = subprocess.Popen(['python', str(file_path)], start_new_session=True)
            db.update_bot_status(bot_id, "Running", proc.pid)
            bot.answer_callback_query(call.id, f"🔄 {bot_data[1]} restarted!")
            
            db.cursor.execute("SELECT * FROM bots WHERE id=?", (bot_id,))
            new_data = db.cursor.fetchone()
            text = f"""
🤖 <b>BOT DETAILS</b>
╔════════════════════════════════════════╗
║ <b>Name:</b> {new_data[2]}                            
║ <b>Status:</b> 🟢 RUNNING                         
║ <b>Deploys:</b> {new_data[11]}                           
╚════════════════════════════════════════╝
"""
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                                reply_markup=bot_control_menu(bot_id, new_data[2], "Running"))
    
    elif data.startswith("user_delete_"):
        bot_id = int(data.split('_')[2])
        db.cursor.execute("SELECT pid, bot_name, filename FROM bots WHERE id=?", (bot_id,))
        bot_data = db.cursor.fetchone()
        
        if bot_data and bot_data[0]:
            try:
                os.kill(bot_data[0], signal.SIGKILL)
            except:
                pass
        
        file_path = Path(Config.PROJECT_DIR) / bot_data[2]
        if file_path.exists():
            file_path.unlink()
        
        db.delete_bot(bot_id)
        bot.answer_callback_query(call.id, f"🗑 {bot_data[1]} deleted!")
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, f"✅ Bot '{bot_data[1]}' deleted successfully!")
    
    elif data.startswith("user_export_"):
        bot_id = int(data.split('_')[2])
        db.cursor.execute("SELECT bot_name, filename FROM bots WHERE id=?", (bot_id,))
        bot_data = db.cursor.fetchone()
        
        if bot_data:
            file_path = Path(Config.PROJECT_DIR) / bot_data[1]
            if file_path.exists():
                with open(file_path, 'rb') as f:
                    bot.send_document(call.message.chat.id, f, caption=f"📦 Exported: {bot_data[0]}")
                bot.answer_callback_query(call.id, "Bot exported!")
    
    elif data.startswith("user_stats_"):
        bot_id = int(data.split('_')[2])
        db.cursor.execute("SELECT pid, bot_name, status FROM bots WHERE id=?", (bot_id,))
        bot_data = db.cursor.fetchone()
        
        if bot_data and bot_data[2] == "Running" and bot_data[0]:
            try:
                proc = psutil.Process(bot_data[0])
                cpu = proc.cpu_percent(interval=0.5)
                mem = proc.memory_percent()
                text = f"""
📊 <b>BOT STATISTICS</b>
╔════════════════════════════════════════╗
║ <b>{bot_data[1]}</b>                               
╠════════════════════════════════════════╣
║ 🖥️ <b>RESOURCES</b>                          
║ ├ CPU: {progress_bar(cpu)} {cpu:.1f}%               
║ ├ RAM: {progress_bar(mem)} {mem:.1f}%               
║ ├ PID: <code>{bot_data[0]}</code>                         
║ └ Status: 🟢 Running                      
╚════════════════════════════════════════╝
"""
                bot.send_message(call.message.chat.id, text)
            except:
                bot.answer_callback_query(call.id, "Cannot get stats!")
        else:
            bot.answer_callback_query(call.id, "Bot is not running!")
    
    bot.answer_callback_query(call.id)

# ==================== PROCESS FUNCTIONS ====================
def process_add_credits(message, user_id, original_message):
    try:
        amount = int(message.text.strip())
        db.add_credits(user_id, amount)
        bot.send_message(message.chat.id, f"✅ Added {amount} credits to user {user_id}!")
        
        user = db.get_user(user_id)
        text = f"""
👤 <b>USER DETAILS</b>
╔════════════════════════════════════════╗
║ <b>Username:</b> @{user[1]}                        
║ <b>Credits:</b> {user[5]} (Updated)                 
╚════════════════════════════════════════╝
"""
        bot.edit_message_text(text, original_message.chat.id, original_message.message_id,
                            reply_markup=user_detail_menu(user_id, user[1], user[5], user[4], user[7], user[9], user[10]))
        db.log_activity(Config.ADMIN_ID, "add_credits", f"Added {amount} credits to user {user_id}")
    except:
        bot.send_message(message.chat.id, "❌ Invalid amount! Please enter a number.")

def process_remove_credits(message, user_id, original_message):
    try:
        amount = int(message.text.strip())
        db.remove_credits(user_id, amount)
        bot.send_message(message.chat.id, f"✅ Removed {amount} credits from user {user_id}!")
        
        user = db.get_user(user_id)
        text = f"""
👤 <b>USER DETAILS</b>
╔════════════════════════════════════════╗
║ <b>Username:</b> @{user[1]}                        
║ <b>Credits:</b> {user[5]} (Updated)                 
╚════════════════════════════════════════╝
"""
        bot.edit_message_text(text, original_message.chat.id, original_message.message_id,
                            reply_markup=user_detail_menu(user_id, user[1], user[5], user[4], user[7], user[9], user[10]))
        db.log_activity(Config.ADMIN_ID, "remove_credits", f"Removed {amount} credits from user {user_id}")
    except:
        bot.send_message(message.chat.id, "❌ Invalid amount! Please enter a number.")

def process_ban_user(message, user_id, original_message):
    reason = message.text.strip()
    db.ban_user(user_id, reason)
    bot.send_message(message.chat.id, f"✅ User {user_id} banned!\nReason: {reason}")
    
    user = db.get_user(user_id)
    text = f"""
👤 <b>USER DETAILS</b>
╔════════════════════════════════════════╗
║ <b>Username:</b> @{user[1]}                        
║ <b>Status:</b> 🔴 BANNED                         
║ <b>Reason:</b> {reason}                            
╚════════════════════════════════════════╝
"""
    bot.edit_message_text(text, original_message.chat.id, original_message.message_id,
                        reply_markup=user_detail_menu(user_id, user[1], user[5], user[4], True, user[9], user[10]))
    db.log_activity(Config.ADMIN_ID, "ban_user", f"Banned user {user_id}: {reason}")

def process_broadcast(message, original_message):
    broadcast_text = message.text
    users = db.get_all_users()
    
    success = 0
    failed = 0
    
    for user in users:
        try:
            bot.send_message(user[0], f"📢 <b>ANNOUNCEMENT</b>\n\n{broadcast_text}", parse_mode="HTML")
            success += 1
            time.sleep(0.05)
        except:
            failed += 1
    
    bot.send_message(original_message.chat.id, f"✅ Broadcast completed!\n\n✅ Sent: {success}\n❌ Failed: {failed}")
    db.log_activity(Config.ADMIN_ID, "broadcast", f"Sent broadcast to {success} users")
    
    # Go back to admin panel
    start_command(original_message)

# ==================== FLASK ROUTES ====================
@app.route('/')
def home():
    stats = db.get_stats()
    return jsonify({
        "status": "online",
        "brand": Config.BRAND_NAME,
        "version": Config.VERSION,
        "stats": stats,
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/stats')
def api_stats():
    return jsonify(db.get_stats())

@app.route('/api/users')
def api_users():
    users = db.get_all_users()
    return jsonify([{
        "id": u[0],
        "username": u[1],
        "plan": u[2],
        "credits": u[3],
        "banned": bool(u[4]),
        "bots": u[5]
    } for u in users])

# ==================== BACKGROUND TASKS ====================
def cleanup_processes():
    while True:
        try:
            db.cursor.execute("SELECT id, pid FROM bots WHERE status='Running'")
            running = db.cursor.fetchall()
            
            for bot_id, pid in running:
                if pid:
                    try:
                        os.kill(pid, 0)
                    except OSError:
                        db.update_bot_status(bot_id, "Stopped")
                        db.log_activity(0, "cleanup", f"Cleaned up bot {bot_id}")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
        
        time.sleep(60)

# ==================== MAIN ====================
def run_bot():
    logger.info(f"Starting {Config.BRAND_NAME} v{Config.VERSION}")
    
    try:
        bot.remove_webhook()
        logger.info("Webhook removed")
    except Exception as e:
        logger.error(f"Webhook removal failed: {e}")
    
    time.sleep(2)
    
    while True:
        try:
            bot.infinity_polling(timeout=30, long_polling_timeout=30)
        except Exception as e:
            logger.error(f"Bot error: {e}")
            time.sleep(10)

if __name__ == '__main__':
    # Start cleanup thread
    threading.Thread(target=cleanup_processes, daemon=True).start()
    
    # Start bot thread
    threading.Thread(target=run_bot, daemon=True).start()
    
    # Start Flask
    logger.info(f"Starting Flask on port {Config.PORT}")
    app.run(host='0.0.0.0', port=Config.PORT, debug=False)    BRAND_NAME = "✨ 𝐀𝐔𝐑𝐏𝐎𝐍 𝐃𝐄𝐗 𝐏𝐑𝐎 ✨"
    VERSION = "6.0.0"
    SUPPORT_ID = "@aurponmodz"
    
    Path(PROJECT_DIR).mkdir(exist_ok=True)

# ==================== DATABASE ====================
class Database:
    def __init__(self):
        self.conn = sqlite3.connect(Config.DB_NAME, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()
    
    def create_tables(self):
        # Users table
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            join_date TEXT,
            plan TEXT DEFAULT 'free',
            credits INTEGER DEFAULT 0,
            is_admin INTEGER DEFAULT 0,
            is_banned INTEGER DEFAULT 0
        )''')
        
        # Bots table
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS bots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            bot_name TEXT,
            filename TEXT,
            pid INTEGER,
            status TEXT,
            start_time TEXT,
            deploy_count INTEGER DEFAULT 0
        )''')
        
        # Add admin
        self.cursor.execute("INSERT OR IGNORE INTO users VALUES (?, ?, ?, ?, ?, ?, ?)",
                          (Config.ADMIN_ID, 'admin', datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                           'enterprise', 999999, 1, 0))
        
        self.conn.commit()
    
    def get_user(self, user_id):
        self.cursor.execute("SELECT * FROM users WHERE id=?", (user_id,))
        return self.cursor.fetchone()
    
    def get_all_users(self):
        self.cursor.execute("SELECT id, username, plan, credits, is_banned FROM users ORDER BY id DESC")
        return self.cursor.fetchall()
    
    def get_user_bots(self, user_id):
        self.cursor.execute("SELECT * FROM bots WHERE user_id=? ORDER BY id DESC", (user_id,))
        return self.cursor.fetchall()
    
    def get_all_bots(self):
        self.cursor.execute("SELECT b.*, u.username FROM bots b LEFT JOIN users u ON b.user_id = u.id ORDER BY b.id DESC")
        return self.cursor.fetchall()
    
    def add_bot(self, user_id, bot_name, filename):
        self.cursor.execute("INSERT INTO bots (user_id, bot_name, filename, status) VALUES (?, ?, ?, ?)",
                          (user_id, bot_name, filename, "Uploaded"))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def update_bot_status(self, bot_id, status, pid=None):
        if pid:
            self.cursor.execute("UPDATE bots SET status=?, pid=?, start_time=? WHERE id=?",
                              (status, pid, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), bot_id))
        else:
            self.cursor.execute("UPDATE bots SET status=? WHERE id=?", (status, bot_id))
        self.conn.commit()
    
    def delete_bot(self, bot_id):
        self.cursor.execute("DELETE FROM bots WHERE id=?", (bot_id,))
        self.conn.commit()
    
    def add_credits(self, user_id, amount):
        self.cursor.execute("UPDATE users SET credits=credits+? WHERE id=?", (amount, user_id))
        self.conn.commit()
    
    def ban_user(self, user_id):
        self.cursor.execute("UPDATE users SET is_banned=1 WHERE id=?", (user_id,))
        self.conn.commit()
    
    def unban_user(self, user_id):
        self.cursor.execute("UPDATE users SET is_banned=0 WHERE id=?", (user_id,))
        self.conn.commit()
    
    def get_stats(self):
        total_users = self.cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        total_bots = self.cursor.execute("SELECT COUNT(*) FROM bots").fetchone()[0]
        running_bots = self.cursor.execute("SELECT COUNT(*) FROM bots WHERE status='Running'").fetchone()[0]
        return {'total_users': total_users, 'total_bots': total_bots, 'running_bots': running_bots}

db = Database()

# ==================== BOT INIT ====================
bot = telebot.TeleBot(Config.TOKEN, parse_mode="HTML")
app = Flask(__name__)

# ==================== HELPER FUNCTIONS ====================
def is_admin(user_id):
    user = db.get_user(user_id)
    return user and user[5] == 1

def get_system_stats():
    try:
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory().percent
        uptime = time.time() - psutil.boot_time()
        return {'cpu': cpu, 'ram': ram, 'uptime': uptime}
    except:
        return {'cpu': 25, 'ram': 40, 'uptime': 86400}

def format_uptime(seconds):
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    if days > 0:
        return f"{days}d {hours}h"
    return f"{hours}h"

def progress_bar(percent):
    filled = int(percent / 5)
    return "█" * filled + "░" * (20 - filled)

# ==================== KEYBOARDS ====================
def main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    buttons = ["📤 Upload Bot", "🤖 My Bots", "⚡ Deploy Bot", "💰 Buy Credits", "📊 Dashboard", "❓ Help", "ℹ️ About"]
    if is_admin(user_id):
        buttons.append("👑 Admin Panel")
    markup.add(*buttons)
    return markup

def admin_panel():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("👥 Users", callback_data="admin_users"),
        types.InlineKeyboardButton("🤖 Bots", callback_data="admin_bots"),
        types.InlineKeyboardButton("📊 Stats", callback_data="admin_stats"),
        types.InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast"),
        types.InlineKeyboardButton("💾 Backup", callback_data="admin_backup"),
        types.InlineKeyboardButton("🔙 Back to Menu", callback_data="admin_back")
    )
    return markup

def user_controls(user_id, username, credits, is_banned):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("💰 Add Credits", callback_data=f"add_credits_{user_id}"),
        types.InlineKeyboardButton("🔨 Ban" if not is_banned else "🔓 Unban", callback_data=f"ban_{user_id}" if not is_banned else f"unban_{user_id}"),
        types.InlineKeyboardButton("📊 User Stats", callback_data=f"user_stats_{user_id}"),
        types.InlineKeyboardButton("🔙 Back to Users", callback_data="back_to_users")
    )
    return markup

def bot_controls(bot_id, status):
    markup = types.InlineKeyboardMarkup(row_width=2)
    if status == "Running":
        markup.add(
            types.InlineKeyboardButton("⏸ Stop", callback_data=f"stop_{bot_id}"),
            types.InlineKeyboardButton("📊 Stats", callback_data=f"bot_stats_{bot_id}")
        )
    else:
        markup.add(
            types.InlineKeyboardButton("▶️ Start", callback_data=f"start_{bot_id}"),
            types.InlineKeyboardButton("📊 Stats", callback_data=f"bot_stats_{bot_id}")
        )
    markup.add(
        types.InlineKeyboardButton("📦 Export", callback_data=f"export_{bot_id}"),
        types.InlineKeyboardButton("🗑 Delete", callback_data=f"delete_{bot_id}"),
        types.InlineKeyboardButton("🔙 Back to Bots", callback_data="back_to_bots")
    )
    return markup

# ==================== START COMMAND ====================
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    username = message.from_user.username or "User"
    
    user = db.get_user(user_id)
    if not user:
        db.cursor.execute("INSERT INTO users (id, username, join_date, credits) VALUES (?, ?, ?, ?)",
                         (user_id, username, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 100))
        db.conn.commit()
        user = db.get_user(user_id)
    
    if user[6] == 1:
        bot.send_message(message.chat.id, "❌ You are banned! Contact support.")
        return
    
    stats = get_system_stats()
    
    if is_admin(user_id):
        text = f"""
╔══════════════════════════════╗
║     👑 ADMIN PANEL 👑        ║
╠══════════════════════════════╣
║ 👤 Admin: @{username}          
║ 💎 Status: SUPER ADMIN        
╠══════════════════════════════╣
║ 📊 Stats:                     
║ ├ Users: {db.get_stats()['total_users']}              
║ ├ Bots: {db.get_stats()['total_bots']}               
║ └ Running: {db.get_stats()['running_bots']}          
╠══════════════════════════════╣
║ 🖥️ System:                    
║ ├ CPU: {progress_bar(stats['cpu'])} {stats['cpu']:.0f}%
║ ├ RAM: {progress_bar(stats['ram'])} {stats['ram']:.0f}%
║ └ Uptime: {format_uptime(stats['uptime'])}        
╚══════════════════════════════╝
"""
        bot.send_message(message.chat.id, text, reply_markup=admin_panel())
    else:
        text = f"""
╔══════════════════════════════╗
║  {Config.BRAND_NAME}  ║
╠══════════════════════════════╣
║ 👤 User: @{username}           
║ 💰 Credits: {user[3]}                
║ 📦 Bots: {len(db.get_user_bots(user_id))}                
╠══════════════════════════════╣
║ 🖥️ System:                    
║ ├ CPU: {stats['cpu']:.0f}%                 
║ ├ RAM: {stats['ram']:.0f}%                 
║ └ Uptime: {format_uptime(stats['uptime'])}        
╚══════════════════════════════╝
"""
        bot.send_message(message.chat.id, text, reply_markup=main_menu(user_id))

# ==================== USER MENU HANDLERS ====================
@bot.message_handler(func=lambda m: m.text == "📤 Upload Bot")
def upload_bot(message):
    msg = bot.reply_to(message, "📤 Send your Python bot file (.py)")
    bot.register_next_step_handler(msg, process_upload)

def process_upload(message):
    if not message.document:
        bot.reply_to(message, "❌ Please send a file!")
        return
    
    if not message.document.file_name.endswith('.py'):
        bot.reply_to(message, "❌ Only .py files allowed!")
        return
    
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded = bot.download_file(file_info.file_path)
        
        filename = f"{uuid.uuid4().hex[:8]}_{message.document.file_name}"
        file_path = Path(Config.PROJECT_DIR) / filename
        file_path.write_bytes(downloaded)
        
        msg = bot.reply_to(message, "✅ Uploaded!\n\nEnter bot name:")
        bot.register_next_step_handler(msg, save_bot, filename)
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

def save_bot(message, filename):
    bot_name = message.text.strip()[:30]
    bot_id = db.add_bot(message.from_user.id, bot_name, filename)
    bot.send_message(message.chat.id, f"✅ Bot '{bot_name}' saved!\n\nUse 'Deploy Bot' to start it.", reply_markup=main_menu(message.from_user.id))

@bot.message_handler(func=lambda m: m.text == "🤖 My Bots")
def my_bots(message):
    bots = db.get_user_bots(message.from_user.id)
    if not bots:
        bot.reply_to(message, "🤖 No bots found!")
        return
    
    text = f"🤖 YOUR BOTS ({len(bots)})\n\n"
    for i, b in enumerate(bots, 1):
        status = "🟢" if b[5] == "Running" else "🔴"
        text += f"{i}. {status} {b[2]} - {b[5]}\n"
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b in bots:
        markup.add(types.InlineKeyboardButton(f"{b[2]}", callback_data=f"mybot_{b[0]}"))
    
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "⚡ Deploy Bot")
def deploy_bot(message):
    bots = db.get_user_bots(message.from_user.id)
    available = [b for b in bots if b[5] != "Running"]
    
    if not available:
        bot.reply_to(message, "📭 No bots to deploy!")
        return
    
    text = "⚡ DEPLOY BOT\n\n"
    for i, b in enumerate(available, 1):
        text += f"{i}. {b[2]}\n"
    
    msg = bot.reply_to(message, text + "\nEnter number:")
    bot.register_next_step_handler(msg, process_deploy, available)

def process_deploy(message, bots):
    try:
        choice = int(message.text) - 1
        bot_data = bots[choice]
        file_path = Path(Config.PROJECT_DIR) / bot_data[3]
        
        if not file_path.exists():
            bot.reply_to(message, "❌ File not found!")
            return
        
        proc = subprocess.Popen(['python', str(file_path)], start_new_session=True)
        db.update_bot_status(bot_data[0], "Running", proc.pid)
        bot.reply_to(message, f"✅ {bot_data[2]} started! PID: {proc.pid}")
    except:
        bot.reply_to(message, "❌ Invalid choice!")

@bot.message_handler(func=lambda m: m.text == "💰 Buy Credits")
def buy_credits(message):
    text = """
💰 BUY CREDITS
╔══════════════════════════════╗
║ 100 Credits → $4.99          ║
║ 500 Credits → $19.99         ║
║ 1000 Credits → $34.99        ║
╠══════════════════════════════╣
║ Contact @aurponmodz to buy!  ║
╚══════════════════════════════╝
"""
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: m.text == "📊 Dashboard")
def dashboard(message):
    user = db.get_user(message.from_user.id)
    bots = db.get_user_bots(message.from_user.id)
    stats = get_system_stats()
    
    text = f"""
📊 DASHBOARD
╔══════════════════════════════╗
║ Credits: {user[3]}                   
║ Total Bots: {len(bots)}                
║ Running: {len([b for b in bots if b[5] == 'Running'])}            
╠══════════════════════════════╣
║ CPU: {stats['cpu']:.0f}%                 
║ RAM: {stats['ram']:.0f}%                 
╚══════════════════════════════╝
"""
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: m.text == "❓ Help")
def help_command(message):
    text = """
❓ HELP
╔══════════════════════════════╗
║ 📤 Upload Bot - Upload .py   ║
║ 🤖 My Bots - View your bots  ║
║ ⚡ Deploy Bot - Start bot    ║
║ 💰 Buy Credits - Get credits ║
║ 📊 Dashboard - Your stats    ║
╚══════════════════════════════╝
"""
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: m.text == "ℹ️ About")
def about_command(message):
    text = f"""
ℹ️ ABOUT
╔══════════════════════════════╗
║ {Config.BRAND_NAME}           
║ Version: {Config.VERSION}             
╠══════════════════════════════╣
║ Developer: @aurponmodz       ║
║ Support: {Config.SUPPORT_ID}      ║
╚══════════════════════════════╝
"""
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: m.text == "👑 Admin Panel")
def admin_panel_menu(message):
    if not is_admin(message.from_user.id):
        return
    start_command(message)

# ==================== ADMIN PANEL CALLBACKS ====================
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    data = call.data
    
    # Admin Users
    if data == "admin_users":
        users = db.get_all_users()
        text = f"👥 USERS ({len(users)})\n\n"
        for u in users[:10]:
            status = "✅" if not u[4] else "🔴"
            text += f"{status} {u[1]} | {u[2]} | {u[3]} credits\n"
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        for u in users[:10]:
            markup.add(types.InlineKeyboardButton(f"📊 {u[1]}", callback_data=f"user_{u[0]}"))
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="admin_back"))
        
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    
    # Admin Bots
    elif data == "admin_bots":
        bots = db.get_all_bots()
        text = f"🤖 BOTS ({len(bots)})\n\n"
        for b in bots[:10]:
            status = "🟢" if b[5] == "Running" else "🔴"
            text += f"{status} {b[2]} - Owner: {b[11]}\n"
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        for b in bots[:10]:
            markup.add(types.InlineKeyboardButton(f"🤖 {b[2]}", callback_data=f"adminbot_{b[0]}"))
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="admin_back"))
        
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    
    # Admin Stats
    elif data == "admin_stats":
        stats = db.get_stats()
        text = f"""
📊 SYSTEM STATS
╔══════════════════════════════╗
║ Total Users: {stats['total_users']}        
║ Total Bots: {stats['total_bots']}         
║ Running Bots: {stats['running_bots']}      
╚══════════════════════════════╝
"""
        markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 Back", callback_data="admin_back"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    
    # Admin Broadcast
    elif data == "admin_broadcast":
        msg = bot.send_message(call.message.chat.id, "📢 Enter broadcast message:")
        bot.register_next_step_handler(msg, process_broadcast, call.message)
    
    # Admin Backup
    elif data == "admin_backup":
        backup_path = Path(Config.DB_NAME)
        if backup_path.exists():
            with open(backup_path, 'rb') as f:
                bot.send_document(call.message.chat.id, f, caption="💾 Database Backup")
        bot.answer_callback_query(call.id, "Backup sent!")
    
    # Admin Back
    elif data == "admin_back":
        start_command(call.message)
    
    # View User
    elif data.startswith("user_"):
        user_id = int(data.split('_')[1])
        user = db.get_user(user_id)
        if user:
            text = f"""
👤 USER DETAILS
╔══════════════════════════════╗
║ ID: {user[0]}                 
║ Username: @{user[1]}          
║ Plan: {user[2]}                
║ Credits: {user[3]}             
║ Status: {'🔴 Banned' if user[6] else '🟢 Active'}    
╚══════════════════════════════╝
"""
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                                reply_markup=user_controls(user_id, user[1], user[3], user[6]))
    
    # Add Credits
    elif data.startswith("add_credits_"):
        user_id = int(data.split('_')[2])
        msg = bot.send_message(call.message.chat.id, f"Enter credits to add for user {user_id}:")
        bot.register_next_step_handler(msg, process_add_credits, user_id, call.message)
    
    # Ban User
    elif data.startswith("ban_"):
        user_id = int(data.split('_')[1])
        db.ban_user(user_id)
        bot.answer_callback_query(call.id, "✅ User banned!")
        
        user = db.get_user(user_id)
        text = f"""
👤 USER DETAILS
╔══════════════════════════════╗
║ ID: {user[0]}                 
║ Username: @{user[1]}          
║ Status: 🔴 BANNED             
╚══════════════════════════════╝
"""
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                            reply_markup=user_controls(user_id, user[1], user[3], True))
    
    # Unban User
    elif data.startswith("unban_"):
        user_id = int(data.split('_')[1])
        db.unban_user(user_id)
        bot.answer_callback_query(call.id, "✅ User unbanned!")
        
        user = db.get_user(user_id)
        text = f"""
👤 USER DETAILS
╔══════════════════════════════╗
║ ID: {user[0]}                 
║ Username: @{user[1]}          
║ Status: 🟢 ACTIVE             
╚══════════════════════════════╝
"""
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                            reply_markup=user_controls(user_id, user[1], user[3], False))
    
    # User Stats
    elif data.startswith("user_stats_"):
        user_id = int(data.split('_')[2])
        user = db.get_user(user_id)
        bots = db.get_user_bots(user_id)
        
        text = f"""
📊 USER STATS
╔══════════════════════════════╗
║ @{user[1]}                     
║ Credits: {user[3]}             
║ Total Bots: {len(bots)}        
║ Running: {len([b for b in bots if b[5] == 'Running'])}      
╚══════════════════════════════╝
"""
        bot.send_message(call.message.chat.id, text)
        bot.answer_callback_query(call.id)
    
    # Back to Users
    elif data == "back_to_users":
        users = db.get_all_users()
        text = f"👥 USERS ({len(users)})\n\n"
        for u in users[:10]:
            status = "✅" if not u[4] else "🔴"
            text += f"{status} {u[1]} | {u[2]} | {u[3]} credits\n"
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        for u in users[:10]:
            markup.add(types.InlineKeyboardButton(f"📊 {u[1]}", callback_data=f"user_{u[0]}"))
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="admin_back"))
        
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    
    # Admin Bot View
    elif data.startswith("adminbot_"):
        bot_id = int(data.split('_')[1])
        db.cursor.execute("SELECT * FROM bots WHERE id=?", (bot_id,))
        bot_data = db.cursor.fetchone()
        
        if bot_data:
            text = f"""
🤖 BOT DETAILS
╔══════════════════════════════╗
║ Name: {bot_data[2]}            
║ Owner: {bot_data[1]}           
║ Status: {bot_data[5]}            
║ Deploys: {bot_data[7]}           
╚══════════════════════════════╝
"""
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                                reply_markup=bot_controls(bot_id, bot_data[5]))
    
    # Back to Bots
    elif data == "back_to_bots":
        bots = db.get_all_bots()
        text = f"🤖 BOTS ({len(bots)})\n\n"
        for b in bots[:10]:
            status = "🟢" if b[5] == "Running" else "🔴"
            text += f"{status} {b[2]} - Owner: {b[11]}\n"
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        for b in bots[:10]:
            markup.add(types.InlineKeyboardButton(f"🤖 {b[2]}", callback_data=f"adminbot_{b[0]}"))
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="admin_back"))
        
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    
    # My Bot
    elif data.startswith("mybot_"):
        bot_id = int(data.split('_')[1])
        db.cursor.execute("SELECT * FROM bots WHERE id=?", (bot_id,))
        bot_data = db.cursor.fetchone()
        
        if bot_data:
            text = f"""
🤖 BOT DETAILS
╔══════════════════════════════╗
║ Name: {bot_data[2]}            
║ Status: {bot_data[5]}            
║ Deploys: {bot_data[7]}           
╚══════════════════════════════╝
"""
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                                reply_markup=bot_controls(bot_id, bot_data[5]))
    
    # Start Bot
    elif data.startswith("start_"):
        bot_id = int(data.split('_')[1])
        db.cursor.execute("SELECT bot_name, filename FROM bots WHERE id=?", (bot_id,))
        bot_data = db.cursor.fetchone()
        
        if bot_data:
            file_path = Path(Config.PROJECT_DIR) / bot_data[1]
            if file_path.exists():
                proc = subprocess.Popen(['python', str(file_path)], start_new_session=True)
                db.update_bot_status(bot_id, "Running", proc.pid)
                bot.answer_callback_query(call.id, f"✅ {bot_data[0]} started!")
                
                # Refresh bot details
                db.cursor.execute("SELECT * FROM bots WHERE id=?", (bot_id,))
                new_data = db.cursor.fetchone()
                text = f"""
🤖 BOT DETAILS
╔══════════════════════════════╗
║ Name: {new_data[2]}            
║ Status: {new_data[5]}            
║ Deploys: {new_data[7]}           
╚══════════════════════════════╝
"""
                bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                                    reply_markup=bot_controls(bot_id, "Running"))
    
    # Stop Bot
    elif data.startswith("stop_"):
        bot_id = int(data.split('_')[1])
        db.cursor.execute("SELECT pid, bot_name FROM bots WHERE id=?", (bot_id,))
        bot_data = db.cursor.fetchone()
        
        if bot_data and bot_data[0]:
            try:
                os.kill(bot_data[0], signal.SIGTERM)
            except:
                pass
            db.update_bot_status(bot_id, "Stopped")
            bot.answer_callback_query(call.id, f"⏸ {bot_data[1]} stopped!")
            
            # Refresh bot details
            db.cursor.execute("SELECT * FROM bots WHERE id=?", (bot_id,))
            new_data = db.cursor.fetchone()
            text = f"""
🤖 BOT DETAILS
╔══════════════════════════════╗
║ Name: {new_data[2]}            
║ Status: {new_data[5]}            
║ Deploys: {new_data[7]}           
╚══════════════════════════════╝
"""
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                                reply_markup=bot_controls(bot_id, "Stopped"))
    
    # Export Bot
    elif data.startswith("export_"):
        bot_id = int(data.split('_')[1])
        db.cursor.execute("SELECT bot_name, filename FROM bots WHERE id=?", (bot_id,))
        bot_data = db.cursor.fetchone()
        
        if bot_data:
            file_path = Path(Config.PROJECT_DIR) / bot_data[1]
            if file_path.exists():
                with open(file_path, 'rb') as f:
                    bot.send_document(call.message.chat.id, f, caption=f"📦 {bot_data[0]}")
                bot.answer_callback_query(call.id, "Bot exported!")
    
    # Delete Bot
    elif data.startswith("delete_"):
        bot_id = int(data.split('_')[1])
        db.cursor.execute("SELECT pid, bot_name, filename FROM bots WHERE id=?", (bot_id,))
        bot_data = db.cursor.fetchone()
        
        if bot_data and bot_data[0]:
            try:
                os.kill(bot_data[0], signal.SIGKILL)
            except:
                pass
        
        file_path = Path(Config.PROJECT_DIR) / bot_data[2]
        if file_path.exists():
            file_path.unlink()
        
        db.delete_bot(bot_id)
        bot.answer_callback_query(call.id, f"🗑 {bot_data[1]} deleted!")
        bot.delete_message(call.message.chat.id, call.message.message_id)
    
    # Bot Stats
    elif data.startswith("bot_stats_"):
        bot_id = int(data.split('_')[2])
        db.cursor.execute("SELECT pid, bot_name, status FROM bots WHERE id=?", (bot_id,))
        bot_data = db.cursor.fetchone()
        
        if bot_data and bot_data[2] == "Running" and bot_data[0]:
            try:
                proc = psutil.Process(bot_data[0])
                cpu = proc.cpu_percent(interval=0.5)
                mem = proc.memory_percent()
                text = f"""
📊 BOT STATS
╔══════════════════════════════╗
║ {bot_data[1]}                   
║ CPU: {cpu:.1f}%                 
║ RAM: {mem:.1f}%                 
║ PID: {bot_data[0]}              
╚══════════════════════════════╝
"""
                bot.send_message(call.message.chat.id, text)
            except:
                bot.answer_callback_query(call.id, "Cannot get stats!")
        else:
            bot.answer_callback_query(call.id, "Bot not running!")
    
    bot.answer_callback_query(call.id)

# ==================== PROCESS FUNCTIONS ====================
def process_broadcast(message, original_message):
    broadcast_text = message.text
    users = db.get_all_users()
    
    success = 0
    for user in users:
        try:
            bot.send_message(user[0], f"📢 ANNOUNCEMENT\n\n{broadcast_text}")
            success += 1
            time.sleep(0.05)
        except:
            pass
    
    bot.send_message(original_message.chat.id, f"✅ Broadcast sent to {success} users!")
    start_command(original_message)

def process_add_credits(message, user_id, original_message):
    try:
        amount = int(message.text)
        db.add_credits(user_id, amount)
        bot.send_message(message.chat.id, f"✅ Added {amount} credits!")
        
        user = db.get_user(user_id)
        text = f"""
👤 USER DETAILS
╔══════════════════════════════╗
║ Username: @{user[1]}          
║ Credits: {user[3]} (Updated)   
╚══════════════════════════════╝
"""
        bot.edit_message_text(text, original_message.chat.id, original_message.message_id,
                            reply_markup=user_controls(user_id, user[1], user[3], user[6]))
    except:
        bot.send_message(message.chat.id, "❌ Invalid amount!")

# ==================== FLASK ROUTES ====================
@app.route('/')
def home():
    return jsonify({"status": "online", "brand": Config.BRAND_NAME, "version": Config.VERSION})

# ==================== BACKGROUND TASKS ====================
def cleanup_processes():
    while True:
        try:
            db.cursor.execute("SELECT id, pid FROM bots WHERE status='Running'")
            for bot_id, pid in db.cursor.fetchall():
                if pid:
                    try:
                        os.kill(pid, 0)
                    except OSError:
                        db.update_bot_status(bot_id, "Stopped")
        except:
            pass
        time.sleep(60)

# ==================== MAIN ====================
def run_bot():
    logger.info(f"Starting bot v{Config.VERSION}")
    try:
        bot.remove_webhook()
    except:
        pass
    time.sleep(2)
    while True:
        try:
            bot.infinity_polling(timeout=30)
        except Exception as e:
            logger.error(f"Bot error: {e}")
            time.sleep(10)

if __name__ == '__main__':
    threading.Thread(target=cleanup_processes, daemon=True).start()
    threading.Thread(target=run_bot, daemon=True).start()
    app.run(host='0.0.0.0', port=Config.PORT, debug=False)    BRAND_NAME = "✨ 𝐀𝐔𝐑𝐏𝐎𝐍 𝐃𝐄𝐗 𝐏𝐑𝐎 ✨"
    VERSION = "6.0.0"
    SUPPORT_ID = "@aurponmodz"
    CHANNEL_ID = "@aurponmodz"
    
    # Subscription Plans
    PLANS = {
        "free": {
            "name": "⭐ FREE",
            "bot_limit": 2,
            "storage_limit": 50,  # MB
            "price": 0,
            "duration": 7,  # days
            "features": ["2 Bots", "50MB Storage", "Basic Support"]
        },
        "basic": {
            "name": "💎 BASIC",
            "bot_limit": 10,
            "storage_limit": 200,
            "price": 4.99,
            "duration": 30,
            "features": ["10 Bots", "200MB Storage", "Priority Support", "Templates"]
        },
        "pro": {
            "name": "🚀 PRO",
            "bot_limit": 50,
            "storage_limit": 1000,
            "price": 14.99,
            "duration": 90,
            "features": ["50 Bots", "1GB Storage", "24/7 Support", "AI Generator", "Analytics"]
        },
        "enterprise": {
            "name": "👑 ENTERPRISE",
            "bot_limit": 999,
            "storage_limit": 10000,
            "price": 49.99,
            "duration": 365,
            "features": ["Unlimited Bots", "10GB Storage", "Dedicated Support", "All Features", "API Access"]
        }
    }
    
    Path(PROJECT_DIR).mkdir(exist_ok=True)

# ==================== DATABASE ====================
class Database:
    def __init__(self):
        self.conn = sqlite3.connect(Config.DB_NAME, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()
    
    def create_tables(self):
        # Users table
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            join_date TEXT,
            plan TEXT DEFAULT 'free',
            expiry_date TEXT,
            credits INTEGER DEFAULT 0,
            bot_limit INTEGER DEFAULT 2,
            storage_used INTEGER DEFAULT 0,
            api_key TEXT,
            referral_code TEXT,
            referred_by INTEGER,
            total_referrals INTEGER DEFAULT 0,
            is_banned INTEGER DEFAULT 0,
            ban_reason TEXT,
            last_active TEXT,
            notification_settings TEXT DEFAULT 'all',
            language TEXT DEFAULT 'en',
            two_fa_enabled INTEGER DEFAULT 0,
            two_fa_secret TEXT
        )''')
        
        # Bots table
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS bots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            bot_name TEXT,
            filename TEXT,
            file_size INTEGER,
            pid INTEGER,
            status TEXT,
            start_time TEXT,
            last_active TEXT,
            cpu_usage REAL,
            ram_usage REAL,
            deploy_count INTEGER DEFAULT 0,
            auto_restart INTEGER DEFAULT 0,
            webhook_url TEXT,
            error_log TEXT,
            version TEXT DEFAULT '1.0'
        )''')
        
        # Payments table
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            plan TEXT,
            amount REAL,
            payment_id TEXT,
            status TEXT,
            created_at TEXT
        )''')
        
        # Templates table
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            description TEXT,
            category TEXT,
            code TEXT,
            author_id INTEGER,
            downloads INTEGER DEFAULT 0,
            rating REAL DEFAULT 0,
            created_at TEXT
        )''')
        
        # Activity logs
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT,
            details TEXT,
            ip TEXT,
            created_at TEXT
        )''')
        
        # Referral rewards
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER,
            referred_id INTEGER,
            reward_earned INTEGER,
            created_at TEXT
        )''')
        
        # Admin settings
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT
        )''')
        
        # Add default settings
        default_settings = [
            ('maintenance_mode', '0'),
            ('auto_approve_templates', '1'),
            ('referral_bonus', '50'),
            ('min_withdraw', '100'),
            ('support_chat', Config.SUPPORT_ID)
        ]
        
        for key, value in default_settings:
            self.cursor.execute("INSERT OR IGNORE INTO settings (key, value, updated_at) VALUES (?, ?, ?)",
                              (key, value, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        
        # Add admin user
        admin_expiry = (datetime.now() + timedelta(days=3650)).strftime('%Y-%m-%d %H:%M:%S')
        referral_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        api_key = hashlib.sha256(f"{Config.ADMIN_ID}{Config.TOKEN}".encode()).hexdigest()
        
        self.cursor.execute("INSERT OR IGNORE INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                          (Config.ADMIN_ID, 'admin', 'Administrator',
                           datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                           'enterprise', admin_expiry, 999999, 999, 0,
                           api_key, referral_code, None, 0, 0, None,
                           datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                           'all', 'en', 0, None))
        
        # Add default templates
        self.add_default_templates()
        
        self.conn.commit()
    
    def add_default_templates(self):
        templates = [
            ("Echo Bot", "Simple echo bot", "basic",
             '''import telebot
TOKEN = "YOUR_BOT_TOKEN"
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(func=lambda m: True)
def echo(message):
    bot.reply_to(message, message.text)

print("Bot started!")
bot.infinity_polling()''', Config.ADMIN_ID),
            
            ("Weather Bot", "Get weather updates", "utility",
             '''import telebot
import requests

TOKEN = "YOUR_BOT_TOKEN"
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['weather'])
def weather(message):
    city = message.text.replace('/weather', '').strip()
    if city:
        try:
            url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid=YOUR_API_KEY&units=metric"
            data = requests.get(url).json()
            temp = data['main']['temp']
            condition = data['weather'][0]['description']
            bot.reply_to(message, f"🌤️ {city}: {temp}°C\\n{condition}")
        except:
            bot.reply_to(message, "City not found!")
    else:
        bot.reply_to(message, "Usage: /weather <city>")

bot.infinity_polling()''', Config.ADMIN_ID),
            
            ("Quote Bot", "Send motivational quotes", "entertainment",
             '''import telebot
import random

TOKEN = "YOUR_BOT_TOKEN"
bot = telebot.TeleBot(TOKEN)

quotes = [
    "Believe in yourself!",
    "Stay positive!",
    "You can do it!",
    "Never give up!",
    "Dream big!"
]

@bot.message_handler(commands=['quote'])
def quote(message):
    bot.reply_to(message, random.choice(quotes))

bot.infinity_polling()''', Config.ADMIN_ID),
            
            ("Admin Bot", "Bot with admin commands", "advanced",
             '''import telebot
TOKEN = "YOUR_BOT_TOKEN"
ADMIN_ID = YOUR_ADMIN_ID
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Welcome to Admin Bot!")

@bot.message_handler(commands=['stats'])
def stats(message):
    if message.from_user.id == ADMIN_ID:
        bot.reply_to(message, "System is running fine!")
    else:
        bot.reply_to(message, "Admin only!")

bot.infinity_polling()''', Config.ADMIN_ID)
        ]
        
        for t in templates:
            self.cursor.execute("INSERT OR IGNORE INTO templates (name, description, category, code, author_id, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                              (t[0], t[1], t[2], t[3], t[4], datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        
        self.conn.commit()
    
    def get_user(self, user_id):
        self.cursor.execute("SELECT * FROM users WHERE id=?", (user_id,))
        return self.cursor.fetchone()
    
    def get_user_by_api_key(self, api_key):
        self.cursor.execute("SELECT * FROM users WHERE api_key=?", (api_key,))
        return self.cursor.fetchone()
    
    def get_all_users(self):
        self.cursor.execute("SELECT id, username, plan, expiry_date, credits, is_banned FROM users ORDER BY id DESC")
        return self.cursor.fetchall()
    
    def get_user_bots(self, user_id):
        self.cursor.execute("SELECT * FROM bots WHERE user_id=? ORDER BY id DESC", (user_id,))
        return self.cursor.fetchall()
    
    def get_all_bots(self):
        self.cursor.execute("SELECT b.*, u.username FROM bots b LEFT JOIN users u ON b.user_id = u.id ORDER BY b.id DESC")
        return self.cursor.fetchall()
    
    def get_templates(self, category=None):
        if category:
            self.cursor.execute("SELECT * FROM templates WHERE category=? ORDER BY downloads DESC", (category,))
        else:
            self.cursor.execute("SELECT * FROM templates ORDER BY downloads DESC")
        return self.cursor.fetchall()
    
    def get_template(self, template_id):
        self.cursor.execute("SELECT * FROM templates WHERE id=?", (template_id,))
        return self.cursor.fetchone()
    
    def add_bot(self, user_id, bot_name, filename, file_size):
        self.cursor.execute("INSERT INTO bots (user_id, bot_name, filename, file_size, status) VALUES (?, ?, ?, ?, ?)",
                          (user_id, bot_name, filename, file_size, "Uploaded"))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def update_bot_status(self, bot_id, status, pid=None):
        if pid:
            self.cursor.execute("UPDATE bots SET status=?, pid=?, last_active=? WHERE id=?",
                              (status, pid, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), bot_id))
        else:
            self.cursor.execute("UPDATE bots SET status=?, last_active=? WHERE id=?",
                              (status, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), bot_id))
        self.conn.commit()
    
    def delete_bot(self, bot_id):
        self.cursor.execute("DELETE FROM bots WHERE id=?", (bot_id,))
        self.conn.commit()
    
    def add_credits(self, user_id, amount):
        self.cursor.execute("UPDATE users SET credits=credits+? WHERE id=?", (amount, user_id))
        self.conn.commit()
    
    def remove_credits(self, user_id, amount):
        self.cursor.execute("UPDATE users SET credits=credits-? WHERE id=?", (amount, user_id))
        self.conn.commit()
    
    def update_user_plan(self, user_id, plan, duration_days):
        expiry = (datetime.now() + timedelta(days=duration_days)).strftime('%Y-%m-%d %H:%M:%S')
        plan_config = Config.PLANS[plan]
        
        self.cursor.execute("UPDATE users SET plan=?, expiry_date=?, bot_limit=? WHERE id=?",
                          (plan, expiry, plan_config['bot_limit'], user_id))
        self.conn.commit()
        
        # Add credits as bonus
        bonus_credits = {"basic": 100, "pro": 500, "enterprise": 2000}.get(plan, 0)
        if bonus_credits > 0:
            self.add_credits(user_id, bonus_credits)
        
        # Log payment
        self.cursor.execute("INSERT INTO payments (user_id, plan, amount, status, created_at) VALUES (?, ?, ?, ?, ?)",
                          (user_id, plan, plan_config['price'], 'completed', datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        self.conn.commit()
        
        return expiry
    
    def create_referral(self, referrer_id, referred_id):
        bonus = int(self.get_setting('referral_bonus'))
        self.add_credits(referrer_id, bonus)
        self.add_credits(referred_id, bonus // 2)
        
        self.cursor.execute("UPDATE users SET total_referrals=total_referrals+1 WHERE id=?", (referrer_id,))
        self.cursor.execute("INSERT INTO referrals (referrer_id, referred_id, reward_earned, created_at) VALUES (?, ?, ?, ?)",
                          (referrer_id, referred_id, bonus, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        self.conn.commit()
    
    def get_setting(self, key):
        self.cursor.execute("SELECT value FROM settings WHERE key=?", (key,))
        result = self.cursor.fetchone()
        return result[0] if result else None
    
    def update_setting(self, key, value):
        self.cursor.execute("UPDATE settings SET value=?, updated_at=? WHERE key=?",
                          (value, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), key))
        self.conn.commit()
    
    def log_activity(self, user_id, action, details, ip=""):
        self.cursor.execute("INSERT INTO activity_logs (user_id, action, details, ip, created_at) VALUES (?, ?, ?, ?, ?)",
                          (user_id, action, details, ip, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        self.conn.commit()
    
    def get_stats(self):
        total_users = self.cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        active_users = self.cursor.execute("SELECT COUNT(*) FROM users WHERE expiry_date > datetime('now')").fetchone()[0]
        total_bots = self.cursor.execute("SELECT COUNT(*) FROM bots").fetchone()[0]
        running_bots = self.cursor.execute("SELECT COUNT(*) FROM bots WHERE status='Running'").fetchone()[0]
        total_deploys = self.cursor.execute("SELECT SUM(deploy_count) FROM bots").fetchone()[0] or 0
        total_revenue = self.cursor.execute("SELECT SUM(amount) FROM payments WHERE status='completed'").fetchone()[0] or 0
        
        return {
            'total_users': total_users,
            'active_users': active_users,
            'total_bots': total_bots,
            'running_bots': running_bots,
            'total_deploys': total_deploys,
            'total_revenue': total_revenue
        }

db = Database()

# ==================== BOT INIT ====================
bot = telebot.TeleBot(Config.TOKEN, parse_mode="HTML")
app = Flask(__name__)

# ==================== DECORATORS ====================
def is_admin(user_id):
    user = db.get_user(user_id)
    return user and user[4] == 'enterprise'

def is_banned(user_id):
    user = db.get_user(user_id)
    return user and user[14] == 1

def check_subscription(user_id):
    user = db.get_user(user_id)
    if not user:
        return False
    if user[5]:
        expiry = datetime.strptime(user[5], '%Y-%m-%d %H:%M:%S')
        return expiry > datetime.now()
    return False

def handle_errors(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}")
            bot.reply_to(args[0], f"❌ Error: {str(e)[:100]}")
    return wrapper

# ==================== SYSTEM FUNCTIONS ====================
def get_system_stats():
    try:
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        return {
            'cpu': cpu,
            'ram': ram.percent,
            'ram_used': ram.used,
            'ram_total': ram.total,
            'disk': disk.percent,
            'disk_used': disk.used,
            'disk_total': disk.total,
            'uptime': time.time() - psutil.boot_time()
        }
    except:
        return {'cpu': 25, 'ram': 40, 'disk': 50, 'uptime': 86400, 'ram_used': 2e9, 'ram_total': 8e9, 'disk_used': 50e9, 'disk_total': 100e9}

def format_bytes(bytes):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024.0:
            return f"{bytes:.1f} {unit}"
        bytes /= 1024.0
    return f"{bytes:.1f} TB"

def format_uptime(seconds):
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    
    if days > 0:
        return f"{days}d {hours}h"
    elif hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"

def progress_bar(percent, length=15):
    filled = int(length * percent / 100)
    return "█" * filled + "░" * (length - filled)

# ==================== KEYBOARDS ====================
class Keyboards:
    @staticmethod
    def main_menu(user_id):
        user = db.get_user(user_id)
        is_premium = user and user[4] != 'free'
        
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        
        buttons = [
            "📤 Upload Bot", "🤖 My Bots",
            "⚡ Deploy Bot", "🎨 Templates"
        ]
        
        if is_premium:
            buttons.extend(["🤖 AI Generator", "📈 Analytics"])
        
        buttons.extend([
            "💰 Upgrade Plan", "🎁 Referral",
            "📊 Dashboard", "⚙️ Settings",
            "❓ Help", "ℹ️ About"
        ])
        
        if is_admin(user_id):
            buttons.extend(["👑 Admin Panel", "📊 Full Stats"])
        
        markup.add(*[types.KeyboardButton(btn) for btn in buttons])
        return markup
    
    @staticmethod
    def admin_panel():
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("👥 Users", callback_data="admin_users"),
            types.InlineKeyboardButton("🤖 Bots", callback_data="admin_bots"),
            types.InlineKeyboardButton("💰 Revenue", callback_data="admin_revenue"),
            types.InlineKeyboardButton("📊 Stats", callback_data="admin_stats"),
            types.InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast"),
            types.InlineKeyboardButton("💾 Backup", callback_data="admin_backup"),
            types.InlineKeyboardButton("🎨 Templates", callback_data="admin_templates"),
            types.InlineKeyboardButton("⚙️ Settings", callback_data="admin_settings"),
            types.InlineKeyboardButton("📜 Logs", callback_data="admin_logs"),
            types.InlineKeyboardButton("🎁 Referrals", callback_data="admin_referrals")
        )
        return markup
    
    @staticmethod
    def subscription_plans():
        markup = types.InlineKeyboardMarkup(row_width=1)
        for plan_id, plan in Config.PLANS.items():
            if plan_id != 'free':
                markup.add(types.InlineKeyboardButton(
                    f"{plan['name']} - ${plan['price']} ({plan['duration']} days)",
                    callback_data=f"subscribe_{plan_id}"
                ))
        return markup
    
    @staticmethod
    def bot_controls(bot_id, status):
        markup = types.InlineKeyboardMarkup(row_width=2)
        
        if status == "Running":
            markup.add(
                types.InlineKeyboardButton("⏸ Stop", callback_data=f"stop_{bot_id}"),
                types.InlineKeyboardButton("🔄 Restart", callback_data=f"restart_{bot_id}"),
                types.InlineKeyboardButton("📊 Stats", callback_data=f"stats_{bot_id}")
            )
        else:
            markup.add(
                types.InlineKeyboardButton("▶️ Start", callback_data=f"start_{bot_id}"),
                types.InlineKeyboardButton("📊 Stats", callback_data=f"stats_{bot_id}")
            )
        
        markup.add(
            types.InlineKeyboardButton("📦 Export", callback_data=f"export_{bot_id}"),
            types.InlineKeyboardButton("🗑 Delete", callback_data=f"delete_{bot_id}"),
            types.InlineKeyboardButton("⚙️ Auto Restart", callback_data=f"autorestart_{bot_id}")
        )
        
        return markup

# ==================== START COMMAND ====================
@bot.message_handler(commands=['start'])
@handle_errors
def start_command(message):
    user_id = message.from_user.id
    username = message.from_user.username or "User"
    full_name = message.from_user.first_name or "User"
    
    # Check if user exists
    user = db.get_user(user_id)
    if not user:
        # Create new user
        referral_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        api_key = hashlib.sha256(f"{user_id}{Config.TOKEN}".encode()).hexdigest()
        expiry = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
        
        db.cursor.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                         (user_id, username, full_name,
                          datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                          'free', expiry, 0, 2, 0,
                          api_key, referral_code, None, 0, 0, None,
                          datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                          'all', 'en', 0, None))
        db.conn.commit()
        
        # Check referral
        if 'start' in message.text and '_' in message.text:
            try:
                ref_code = message.text.split('_')[1]
                db.cursor.execute("SELECT id FROM users WHERE referral_code=?", (ref_code,))
                referrer = db.cursor.fetchone()
                if referrer and referrer[0] != user_id:
                    db.create_referral(referrer[0], user_id)
                    bot.send_message(user_id, "🎉 You got 25 free credits from referral!")
            except:
                pass
        
        user = db.get_user(user_id)
    
    # Check if banned
    if user[14] == 1:
        bot.send_message(message.chat.id, f"❌ You are banned!\nReason: {user[15]}\nContact: {Config.SUPPORT_ID}")
        return
    
    # Update last active
    db.cursor.execute("UPDATE users SET last_active=? WHERE id=?", 
                     (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), user_id))
    db.conn.commit()
    
    # Get system stats
    stats = get_system_stats()
    db_stats = db.get_stats()
    
    # Check if admin
    if is_admin(user_id):
        text = f"""
╔════════════════════════════════════════╗
║     👑 ADMIN CONTROL PANEL 👑         ║
╠════════════════════════════════════════╣
║ 👤 <b>ADMIN:</b> @{username}                      
║ 🆔 <b>ID:</b> <code>{user_id}</code>                         
║ 💎 <b>Plan:</b> ENTERPRISE                        
╠════════════════════════════════════════╣
║ 📊 <b>PLATFORM STATS</b>                      
║ ├ Users: {db_stats['total_users']}                          
║ ├ Active: {db_stats['active_users']}                          
║ ├ Bots: {db_stats['total_bots']}/{db_stats['running_bots']} running     
║ ├ Deploys: {db_stats['total_deploys']}                          
║ └ Revenue: ${db_stats['total_revenue']:.2f}                         
╠════════════════════════════════════════╣
║ 🖥️ <b>SERVER</b>                                
║ ├ CPU: {progress_bar(stats['cpu'])} {stats['cpu']:.0f}%           
║ ├ RAM: {progress_bar(stats['ram'])} {stats['ram']:.0f}%           
║ ├ Disk: {progress_bar(stats['disk'])} {stats['disk']:.0f}%           
║ └ Uptime: {format_uptime(stats['uptime'])}                 
╠════════════════════════════════════════╣
║ 🔧 <b>ADMIN COMMANDS</b>                        
║ • /stats - System statistics           
║ • /users - List all users             
║ • /broadcast - Send announcement      
╚════════════════════════════════════════╝
"""
        bot.send_message(message.chat.id, text, reply_markup=Keyboards.admin_panel())
    else:
        # Calculate days left
        days_left = 0
        if user[5]:
            try:
                expiry = datetime.strptime(user[5], '%Y-%m-%d %H:%M:%S')
                days_left = (expiry - datetime.now()).days
            except:
                pass
        
        text = f"""
╔════════════════════════════════════════╗
║  {Config.BRAND_NAME} v{Config.VERSION}  ║
╠════════════════════════════════════════╣
║ 👤 <b>USER INFO</b>                              
║ ├ ID: <code>{user_id}</code>                         
║ ├ Name: @{username}                         
║ └ Joined: {user[3][:10]}                        
╠════════════════════════════════════════╣
║ 💎 <b>ACCOUNT</b>                                
║ ├ Plan: {Config.PLANS[user[4]]['name']}                     
║ ├ Credits: {user[6]} 💎                         
║ ├ Bots: {len(db.get_user_bots(user_id))}/{user[7]}               
║ └ Expires: {user[5][:10] if user[5] else 'Never'} ({days_left} days left)  
╠════════════════════════════════════════╣
║ 🖥️ <b>SYSTEM</b>                                 
║ ├ CPU: {progress_bar(stats['cpu'])} {stats['cpu']:.0f}%           
║ ├ RAM: {progress_bar(stats['ram'])} {stats['ram']:.0f}%           
║ ├ Uptime: {format_uptime(stats['uptime'])}                 
║ └ Active Users: {db_stats['active_users']}                      
╠════════════════════════════════════════╣
║ 🎁 <b>REFERRAL</b>                               
║ └ Code: <code>{user[10]}</code>                         
║    Each referral gives you {db.get_setting('referral_bonus')} credits!
╚════════════════════════════════════════╝
"""
        bot.send_message(message.chat.id, text, reply_markup=Keyboards.main_menu(user_id))
    
    db.log_activity(user_id, "start", "Started the bot")

# ==================== ADMIN COMMANDS ====================
@bot.message_handler(commands=['stats'])
@handle_errors
def stats_command(message):
    if not is_admin(message.from_user.id):
        return
    
    stats = db.get_stats()
    system = get_system_stats()
    
    text = f"""
╔════════════════════════════════════════╗
║           📊 SYSTEM STATS             ║
╠════════════════════════════════════════╣
║ 👥 <b>USERS</b>                                 
║ ├ Total: {stats['total_users']}                          
║ ├ Active: {stats['active_users']}                          
║ └ Banned: {stats['total_users'] - stats['active_users']}                      
╠════════════════════════════════════════╣
║ 🤖 <b>BOTS</b>                                  
║ ├ Total: {stats['total_bots']}                          
║ ├ Running: {stats['running_bots']}                          
║ ├ Stopped: {stats['total_bots'] - stats['running_bots']}                      
║ └ Deploys: {stats['total_deploys']}                          
╠════════════════════════════════════════╣
║ 💰 <b>FINANCE</b>                                
║ └ Revenue: ${stats['total_revenue']:.2f}                         
╠════════════════════════════════════════╣
║ 🖥️ <b>SERVER</b>                                 
║ ├ CPU: {system['cpu']:.1f}% ({progress_bar(system['cpu'])})          
║ ├ RAM: {system['ram']:.1f}% ({progress_bar(system['ram'])}) ({format_bytes(system['ram_used'])}/{format_bytes(system['ram_total'])})  
║ ├ Disk: {system['disk']:.1f}% ({progress_bar(system['disk'])})          
║ └ Uptime: {format_uptime(system['uptime'])}                 
╚════════════════════════════════════════╝
"""
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['users'])
@handle_errors
def users_command(message):
    if not is_admin(message.from_user.id):
        return
    
    users = db.get_all_users()
    text = f"👥 <b>USERS LIST</b> ({len(users)})\n\n"
    
    for user in users[:20]:
        status = "🟢" if not user[5] else "🔴"
        text += f"{status} <b>{user[1]}</b> | {user[2]} | {user[3]} credits\n"
    
    if len(users) > 20:
        text += f"\n... and {len(users)-20} more"
    
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['broadcast'])
@handle_errors
def broadcast_command(message):
    if not is_admin(message.from_user.id):
        return
    
    msg = bot.reply_to(message, "📢 Enter your broadcast message:")
    bot.register_next_step_handler(msg, process_broadcast)

def process_broadcast(message):
    broadcast_text = message.text
    users = db.get_all_users()
    
    success = 0
    failed = 0
    
    for user in users:
        try:
            bot.send_message(user[0], f"📢 <b>ANNOUNCEMENT</b>\n\n{broadcast_text}", parse_mode="HTML")
            success += 1
            time.sleep(0.05)
        except:
            failed += 1
    
    bot.send_message(message.chat.id, f"✅ Broadcast completed!\n\n✅ Sent: {success}\n❌ Failed: {failed}")

# ==================== USER MENU HANDLERS ====================
@bot.message_handler(func=lambda m: m.text == "📤 Upload Bot")
@handle_errors
def upload_bot(message):
    user = db.get_user(message.from_user.id)
    
    if user[14] == 1:
        bot.reply_to(message, "❌ You are banned!")
        return
    
    if len(db.get_user_bots(message.from_user.id)) >= user[7]:
        bot.reply_to(message, f"❌ Bot limit reached! Your limit: {user[7]}\nUpgrade to get more!")
        return
    
    msg = bot.reply_to(message, "📤 Send your Python bot file (.py)\nMax size: 50MB")
    bot.register_next_step_handler(msg, process_upload)

def process_upload(message):
    if not message.document:
        bot.reply_to(message, "❌ Please send a file!")
        return
    
    file_name = message.document.file_name
    if not file_name.endswith('.py'):
        bot.reply_to(message, "❌ Only .py files are allowed!")
        return
    
    file_size = message.document.file_size
    if file_size > 50 * 1024 * 1024:
        bot.reply_to(message, "❌ File too large! Max 50MB")
        return
    
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded = bot.download_file(file_info.file_path)
        
        safe_name = f"{uuid.uuid4().hex[:8]}_{file_name}"
        file_path = Path(Config.PROJECT_DIR) / safe_name
        file_path.write_bytes(downloaded)
        
        # Save to database
        bot_id = db.add_bot(message.from_user.id, "New Bot", safe_name, file_size)
        
        msg = bot.reply_to(message, "✅ Uploaded!\n\nEnter bot name:")
        bot.register_next_step_handler(msg, save_bot_name, bot_id, safe_name)
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

def save_bot_name(message, bot_id, filename):
    bot_name = message.text.strip()[:50]
    
    db.cursor.execute("UPDATE bots SET bot_name=? WHERE id=?", (bot_name, bot_id))
    db.conn.commit()
    
    user = db.get_user(message.from_user.id)
    
    bot.send_message(message.chat.id, 
                    f"✅ Bot '{bot_name}' saved!\n\nUse '⚡ Deploy Bot' to start it.",
                    reply_markup=Keyboards.main_menu(message.from_user.id))
    
    db.log_activity(message.from_user.id, "upload_bot", f"Uploaded {filename}")

@bot.message_handler(func=lambda m: m.text == "🤖 My Bots")
@handle_errors
def my_bots(message):
    user_id = message.from_user.id
    bots = db.get_user_bots(user_id)
    
    if not bots:
        bot.reply_to(message, "🤖 No bots found!\nUse 'Upload Bot' to create one.")
        return
    
    text = f"🤖 <b>YOUR BOTS</b> ({len(bots)})\n╔════════════════════════════════════════╗\n"
    
    for i, b in enumerate(bots[:10], 1):
        status_icon = "🟢" if b[6] == "Running" else "🔴" if b[6] == "Stopped" else "🟡"
        text += f"║ {i}. {status_icon} <b>{b[2]}</b>\n"
        text += f"║    Status: {b[6]} | Deploys: {b[11]}\n"
        text += "╠────────────────────────────────────╣\n"
    
    text += "╚════════════════════════════════════════╝\n\nSelect a bot to manage:"
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b in bots:
        markup.add(types.InlineKeyboardButton(
            f"{b[2]} - {b[6]}", callback_data=f"user_bot_{b[0]}"
        ))
    
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "⚡ Deploy Bot")
@handle_errors
def deploy_bot(message):
    user_id = message.from_user.id
    bots = db.get_user_bots(user_id)
    available = [b for b in bots if b[6] != "Running"]
    
    if not available:
        bot.reply_to(message, "📭 No bots available for deployment!\nUpload a bot first.")
        return
    
    text = "⚡ <b>DEPLOY BOT</b>\n╔════════════════════════════════════════╗\n"
    for i, b in enumerate(available, 1):
        text += f"║ {i}. <b>{b[2]}</b>\n"
        text += "╠────────────────────────────────────╣\n"
    
    text += "╚════════════════════════════════════════╝\n\nEnter number to deploy:"
    
    msg = bot.reply_to(message, text)
    bot.register_next_step_handler(msg, process_deploy, available)

def process_deploy(message, bots):
    try:
        choice = int(message.text.strip()) - 1
        if choice < 0 or choice >= len(bots):
            raise ValueError
        
        bot_data = bots[choice]
        bot_id = bot_data[0]
        bot_name = bot_data[2]
        filename = bot_data[3]
        file_path = Path(Config.PROJECT_DIR) / filename
        
        if not file_path.exists():
            bot.reply_to(message, "❌ File not found!")
            return
        
        # Start the bot
        proc = subprocess.Popen(['python', str(file_path)], 
                               start_new_session=True,
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
        
        db.update_bot_status(bot_id, "Running", proc.pid)
        
        bot.reply_to(message, f"✅ <b>{bot_name}</b> is RUNNING!\nPID: <code>{proc.pid}</code>")
        db.log_activity(message.from_user.id, "deploy_bot", f"Deployed {bot_name}")
        
    except:
        bot.reply_to(message, "❌ Invalid selection!")

@bot.message_handler(func=lambda m: m.text == "🎨 Templates")
@handle_errors
def templates_menu(message):
    templates = db.get_templates()
    
    text = "🎨 <b>BOT TEMPLATES</b>\n╔════════════════════════════════════════╗\n"
    
    for t in templates[:10]:
        text += f"║ 📦 <b>{t[1]}</b> [{t[3]}]\n"
        text += f"║    {t[2][:35]}...\n"
        text += f"║    ⭐ {t[7]:.1f} | 📥 {t[6]} downloads\n"
        text += "╠────────────────────────────────────╣\n"
    
    text += "╚════════════════════════════════════════╝\n\nSelect a template:"
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for t in templates:
        markup.add(types.InlineKeyboardButton(f"📦 {t[1]}", callback_data=f"use_template_{t[0]}"))
    
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "💰 Upgrade Plan")
@handle_errors
def upgrade_plan(message):
    user = db.get_user(message.from_user.id)
    
    text = f"""
╔════════════════════════════════════════╗
║         💰 UPGRADE PLAN              ║
╠════════════════════════════════════════╣
║ 📊 <b>Current Plan:</b> {Config.PLANS[user[4]]['name']}        
║ 💎 <b>Current Credits:</b> {user[6]}                     
╠════════════════════════════════════════╣
║ <b>📋 AVAILABLE PLANS</b>                   
║                                         
║ 💎 <b>BASIC</b> - $4.99/30 days           
║ ├ 10 Bots | 200MB Storage              
║ ├ Priority Support                     
║ └ +100 Bonus Credits                   
║                                         
║ 🚀 <b>PRO</b> - $14.99/90 days            
║ ├ 50 Bots | 1GB Storage                
║ ├ 24/7 Support | AI Generator          
║ └ +500 Bonus Credits                   
║                                         
║ 👑 <b>ENTERPRISE</b> - $49.99/year         
║ ├ Unlimited Bots | 10GB Storage        
║ ├ Dedicated Support | API Access       
║ └ +2000 Bonus Credits                  
╠════════════════════════════════════════╣
║ 💳 <b>Payment Methods:</b>                 
║ • Crypto (USDT, BTC, ETH)              
║ • USDT (TRC20/BEP20)                   
║ • Bank Transfer (BD)                   
║ • bKash/Nagad/Rocket (BD)              
╠════════════════════════════════════════╣
║ 💬 Contact @aurponmodz to upgrade!      
╚════════════════════════════════════════╝
"""
    bot.send_message(message.chat.id, text, reply_markup=Keyboards.subscription_plans())

@bot.message_handler(func=lambda m: m.text == "🎁 Referral")
@handle_errors
def referral_menu(message):
    user = db.get_user(message.from_user.id)
    bonus = db.get_setting('referral_bonus')
    
    text = f"""
╔════════════════════════════════════════╗
║            🎁 REFERRAL                ║
╠════════════════════════════════════════╣
║ <b>YOUR REFERRAL CODE:</b>                  
║ <code>{user[10]}</code>                         
║                                         
║ <b>REFERRAL LINK:</b>                      
║ <code>https://t.me/{Config.BOT_USERNAME[1:]}?start={user[10]}</code>
╠════════════════════════════════════════╣
║ 📊 <b>STATISTICS</b>                       
║ ├ Total Referrals: {user[12]}                     
║ ├ Credits Earned: {user[12] * int(bonus)}                  
║ └ Next Reward: {int(bonus) - (user[6] % int(bonus))} credits           
╠════════════════════════════════════════╣
║ 💡 <b>HOW IT WORKS</b>                      
║ 1. Share your referral link            
║ 2. Friends join using your link        
║ 3. You get {bonus} credits each!          
║ 4. Friend gets {int(bonus)//2} free credits!    
╚════════════════════════════════════════╝
"""
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📤 Share Link", switch_inline_query=f"Join @{Config.BOT_USERNAME[1:]} using my referral code: {user[10]}"))
    
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "📊 Dashboard")
@handle_errors
def dashboard(message):
    user = db.get_user(message.from_user.id)
    bots = db.get_user_bots(message.from_user.id)
    stats = get_system_stats()
    db_stats = db.get_stats()
    
    running = len([b for b in bots if b[6] == "Running"])
    total_storage = sum([b[4] for b in bots]) / (1024 * 1024)
    
    days_left = 0
    if user[5]:
        try:
            expiry = datetime.strptime(user[5], '%Y-%m-%d %H:%M:%S')
            days_left = (expiry - datetime.now()).days
        except:
            pass
    
    text = f"""
╔════════════════════════════════════════╗
║           📊 DASHBOARD                ║
╠════════════════════════════════════════╣
║ 👤 <b>ACCOUNT INFO</b>                      
║ ├ Plan: {Config.PLANS[user[4]]['name']}                     
║ ├ Credits: {user[6]} 💎                         
║ ├ Expires: {days_left} days left                 
║ └ Storage: {total_storage:.1f}/{Config.PLANS[user[4]]['storage_limit']} MB        
╠════════════════════════════════════════╣
║ 🤖 <b>BOT STATS</b>                         
║ ├ Total: {len(bots)}/{user[7]}                      
║ ├ Running: {running}                          
║ ├ Stopped: {len(bots) - running}                      
║ └ Total Deploys: {sum([b[11] for b in bots])}                  
╠════════════════════════════════════════╣
║ 🎁 <b>REFERRAL</b>                            
║ ├ Referrals: {user[12]}                          
║ └ Code: <code>{user[10][:10]}...</code>                     
╠════════════════════════════════════════╣
║ 🖥️ <b>SYSTEM</b>                              
║ ├ CPU: {stats['cpu']:.1f}% ({progress_bar(stats['cpu'])})          
║ ├ RAM: {stats['ram']:.1f}% ({progress_bar(stats['ram'])})          
║ └ Active Users: {db_stats['active_users']}                      
╚════════════════════════════════════════╝
"""
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("💰 Buy Credits", callback_data="buy_credits"),
        types.InlineKeyboardButton("🎁 Referral", callback_data="referral"),
        types.InlineKeyboardButton("📈 Analytics", callback_data="analytics"),
        types.InlineKeyboardButton("⚙️ Settings", callback_data="settings")
    )
    
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "⚙️ Settings")
@handle_errors
def settings_menu(message):
    user = db.get_user(message.from_user.id)
    
    text = f"""
╔════════════════════════════════════════╗
║           ⚙️ SETTINGS                 ║
╠════════════════════════════════════════╣
║ <b>🔐 ACCOUNT</b>                            
║ ├ Plan: {Config.PLANS[user[4]]['name']}                     
║ ├ API Key: <code>{user[9][:20]}...</code>               
║ └ 2FA: {'✅ Enabled' if user[18] else '❌ Disabled'}                    
╠════════════════════════════════════════╣
║ <b>🔔 NOTIFICATIONS</b>                     
║ └ Status: {user[16]}                            
╠════════════════════════════════════════╣
║ <b>🌐 LANGUAGE</b>                           
║ └ English                             
╚════════════════════════════════════════╝
"""
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🔑 API Key", callback_data="api_key"),
        types.InlineKeyboardButton("🔐 2FA", callback_data="two_fa"),
        types.InlineKeyboardButton("🔔 Notifications", callback_data="notifications"),
        types.InlineKeyboardButton("🗑 Delete Data", callback_data="delete_data")
    )
    
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "❓ Help")
@handle_errors
def help_command(message):
    text = f"""
╔════════════════════════════════════════╗
║              ❓ HELP                  ║
╠════════════════════════════════════════╣
║ <b>📤 UPLOAD BOT</b>                        
║ Upload your Python bot file (.py)     
║                                         
║ <b>🤖 MY BOTS</b>                           
║ View and manage your bots             
║                                         
║ <b>⚡ DEPLOY BOT</b>                        
║ Start your uploaded bot               
║                                         
║ <b>🎨 TEMPLATES</b>                        
║ Use ready-made bot templates          
║                                         
║ <b>💰 UPGRADE PLAN</b>                     
║ Get more features and limits          
║                                         
║ <b>🎁 REFERRAL</b>                         
║ Invite friends and earn credits       
║                                         
║ <b>📊 DASHBOARD</b>                        
║ View your statistics                  
║                                         
║ <b>⚙️ SETTINGS</b>                         
║ Configure your account                
╠════════════════════════════════════════╣
║ 💬 <b>SUPPORT</b>                             
║ Contact: {Config.SUPPORT_ID}                 
║ Channel: {Config.CHANNEL_ID}                 
╚════════════════════════════════════════╝
"""
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: m.text == "ℹ️ About")
@handle_errors
def about_command(message):
    stats = db.get_stats()
    
    text = f"""
╔════════════════════════════════════════╗
║            ℹ️ ABOUT                   ║
╠════════════════════════════════════════╣
║ {Config.BRAND_NAME}                       
║ Version: {Config.VERSION}                     
╠════════════════════════════════════════╣
║ <b>✨ FEATURES</b>                           
║ ✓ Easy bot deployment                 
║ ✓ 50+ Bot templates                   
║ ✓ AI bot generator                    
║ ✓ Real-time monitoring                
║ ✓ Referral system                     
║ ✓ Credit system                       
║ ✓ 24/7 hosting                        
║ ✓ API access                          
╠════════════════════════════════════════╣
║ <b>📊 PLATFORM STATS</b>                    
║ ├ Users: {stats['total_users']}                          
║ ├ Bots: {stats['total_bots']}                          
║ └ Revenue: ${stats['total_revenue']:.2f}                         
╠════════════════════════════════════════╣
║ 👨‍💻 <b>DEVELOPER</b>                         
║ @aurponmodz                           
║                                         
║ 💬 <b>SUPPORT</b>                            
║ {Config.SUPPORT_ID}                         
╚════════════════════════════════════════╝
"""
    bot.send_message(message.chat.id, text)

# ==================== CALLBACK HANDLERS ====================
@bot.callback_query_handler(func=lambda call: True)
@handle_errors
def handle_callbacks(call):
    data = call.data
    
    # Admin callbacks
    if data == "admin_users":
        users = db.get_all_users()
        text = f"👥 <b>USERS ({len(users)})</b>\n\n"
        
        for user in users[:15]:
            status = "🟢" if not user[5] else "🔴"
            text += f"{status} <b>{user[1]}</b> | {user[2]} | {user[3]} credits\n"
        
        if len(users) > 15:
            text += f"\n... and {len(users)-15} more"
        
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id)
    
    elif data == "admin_stats":
        stats = db.get_stats()
        system = get_system_stats()
        
        text = f"""
<b>📊 SYSTEM STATISTICS</b>
╔════════════════════════════════════════╗
║ 👥 <b>USERS</b>                                 
║ ├ Total: {stats['total_users']}                          
║ ├ Active: {stats['active_users']}                          
║ └ Banned: {stats['total_users'] - stats['active_users']}                      
╠════════════════════════════════════════╣
║ 🤖 <b>BOTS</b>                                  
║ ├ Total: {stats['total_bots']}                          
║ ├ Running: {stats['running_bots']}                          
║ └ Deploys: {stats['total_deploys']}                          
╠════════════════════════════════════════╣
║ 💰 <b>REVENUE</b>                                
║ └ ${stats['total_revenue']:.2f}                         
╠════════════════════════════════════════╣
║ 🖥️ <b>SERVER</b>                                 
║ ├ CPU: {system['cpu']:.1f}%                          
║ ├ RAM: {system['ram']:.1f}%                          
║ └ Uptime: {format_uptime(system['uptime'])}                 
╚════════════════════════════════════════╝
"""
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id)
    
    # Subscription callbacks
    elif data.startswith("subscribe_"):
        plan_id = data.split('_')[1]
        plan = Config.PLANS[plan_id]
        
        text = f"""
<b>💎 UPGRADE TO {plan['name']}</b>
╔════════════════════════════════════════╗
║ <b>📋 PLAN DETAILS</b>                       
║ ├ Price: ${plan['price']}                         
║ ├ Duration: {plan['duration']} days                  
║ └ Bots: {plan['bot_limit']}                          
╠════════════════════════════════════════╣
║ <b>✨ FEATURES</b>                            
"""
        for feature in plan['features']:
            text += f"║ ✓ {feature}\n"
        
        text += f"""
╠════════════════════════════════════════╣
║ <b>💳 PAYMENT METHODS</b>                    
║ • USDT (TRC20/BEP20)                   
║ • BTC / ETH                            
║ • bKash / Nagad / Rocket (BD)          
║ • Bank Transfer                        
╠════════════════════════════════════════╣
║ 💬 Contact @aurponmodz to complete     
║    your payment and get activated!     
╚════════════════════════════════════════╝
"""
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id)
        bot.answer_callback_query(call.id, "Contact @aurponmodz to complete payment!")
    
    # Bot control callbacks
    elif data.startswith("start_"):
        bot_id = int(data.split('_')[1])
        db.cursor.execute("SELECT bot_name, filename FROM bots WHERE id=?", (bot_id,))
        bot_data = db.cursor.fetchone()
        
        if bot_data:
            file_path = Path(Config.PROJECT_DIR) / bot_data[1]
            if file_path.exists():
                proc = subprocess.Popen(['python', str(file_path)], 
                                       start_new_session=True,
                                       stdout=subprocess.DEVNULL,
                                       stderr=subprocess.DEVNULL)
                db.update_bot_status(bot_id, "Running", proc.pid)
                bot.answer_callback_query(call.id, f"✅ {bot_data[0]} started!")
            else:
                bot.answer_callback_query(call.id, "File not found!")
    
    elif data.startswith("stop_"):
        bot_id = int(data.split('_')[1])
        db.cursor.execute("SELECT pid, bot_name FROM bots WHERE id=?", (bot_id,))
        bot_data = db.cursor.fetchone()
        
        if bot_data and bot_data[0]:
            try:
                os.kill(bot_data[0], signal.SIGTERM)
            except:
                pass
            db.update_bot_status(bot_id, "Stopped")
            bot.answer_callback_query(call.id, f"⏸ {bot_data[1]} stopped!")
    
    elif data.startswith("restart_"):
        bot_id = int(data.split('_')[1])
        db.cursor.execute("SELECT pid, bot_name, filename FROM bots WHERE id=?", (bot_id,))
        bot_data = db.cursor.fetchone()
        
        if bot_data and bot_data[0]:
            try:
                os.kill(bot_data[0], signal.SIGTERM)
            except:
                pass
        
        time.sleep(1)
        
        file_path = Path(Config.PROJECT_DIR) / bot_data[2]
        if file_path.exists():
            proc = subprocess.Popen(['python', str(file_path)], 
                                   start_new_session=True,
                                   stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)
            db.update_bot_status(bot_id, "Running", proc.pid)
            bot.answer_callback_query(call.id, f"🔄 {bot_data[1]} restarted!")
    
    elif data.startswith("delete_"):
        bot_id = int(data.split('_')[1])
        db.cursor.execute("SELECT pid, bot_name, filename FROM bots WHERE id=?", (bot_id,))
        bot_data = db.cursor.fetchone()
        
        if bot_data and bot_data[0]:
            try:
                os.kill(bot_data[0], signal.SIGKILL)
            except:
                pass
        
        file_path = Path(Config.PROJECT_DIR) / bot_data[2]
        if file_path.exists():
            file_path.unlink()
        
        db.delete_bot(bot_id)
        bot.answer_callback_query(call.id, f"🗑 {bot_data[1]} deleted!")
        bot.delete_message(call.message.chat.id, call.message.message_id)
    
    elif data.startswith("stats_"):
        bot_id = int(data.split('_')[1])
        db.cursor.execute("SELECT pid, bot_name, status FROM bots WHERE id=?", (bot_id,))
        bot_data = db.cursor.fetchone()
        
        if bot_data and bot_data[2] == "Running" and bot_data[0]:
            try:
                proc = psutil.Process(bot_data[0])
                cpu = proc.cpu_percent(interval=0.5)
                mem = proc.memory_percent()
                
                text = f"""
<b>📊 BOT STATISTICS</b>
╔════════════════════════════════════════╗
║ <b>{bot_data[1]}</b>                             
╠════════════════════════════════════════╣
║ 🖥️ <b>RESOURCES</b>                            
║ ├ CPU: {progress_bar(cpu)} {cpu:.1f}%           
║ ├ RAM: {progress_bar(mem)} {mem:.1f}%           
║ ├ PID: <code>{bot_data[0]}</code>                         
║ └ Status: 🟢 Running                      
╠════════════════════════════════════════╣
║ 📈 <b>PERFORMANCE</b>                         
║ ├ Memory: {format_bytes(proc.memory_info().rss)}        
║ └ Threads: {proc.num_threads()}                          
╚════════════════════════════════════════╝
"""
                bot.send_message(call.message.chat.id, text)
            except:
                bot.answer_callback_query(call.id, "Cannot get stats!")
        else:
            bot.answer_callback_query(call.id, "Bot is not running!")
    
    elif data.startswith("export_"):
        bot_id = int(data.split('_')[1])
        db.cursor.execute("SELECT bot_name, filename FROM bots WHERE id=?", (bot_id,))
        bot_data = db.cursor.fetchone()
        
        if bot_data:
            file_path = Path(Config.PROJECT_DIR) / bot_data[1]
            if file_path.exists():
                with open(file_path, 'rb') as f:
                    bot.send_document(call.message.chat.id, f, 
                                    caption=f"📦 Exported: {bot_data[0]}")
                bot.answer_callback_query(call.id, "Bot exported!")
    
    elif data.startswith("use_template_"):
        template_id = int(data.split('_')[2])
        template = db.get_template(template_id)
        
        if template:
            filename = f"template_{uuid.uuid4().hex[:8]}.py"
            file_path = Path(Config.PROJECT_DIR) / filename
            file_path.write_text(template[4])
            
            db.add_bot(call.from_user.id, f"Template: {template[1]}", filename, len(template[4]))
            db.cursor.execute("UPDATE templates SET downloads=downloads+1 WHERE id=?", (template_id,))
            db.conn.commit()
            
            bot.answer_callback_query(call.id, f"✅ Template '{template[1]}' added!")
            bot.send_message(call.message.chat.id, 
                           f"✅ Template '{template[1]}' saved!\n\nUse 'Deploy Bot' to start it.")
    
    elif data == "buy_credits":
        text = """
<b>💰 BUY CREDITS</b>
╔════════════════════════════════════════╗
║ <b>💎 CREDIT PACKAGES</b>                   
║                                         
║ 100 Credits → $4.99                    
║ 500 Credits → $19.99                   
║ 1000 Credits → $34.99                  
║ 5000 Credits → $149.99                 
╠════════════════════════════════════════╣
║ 💳 Payment Methods:                    
║ • USDT (TRC20/BEP20)                   
║ • bKash/Nagad/Rocket (BD)              
╠════════════════════════════════════════╣
║ 💬 Contact @aurponmodz to purchase!    
╚════════════════════════════════════════╝
"""
        bot.send_message(call.message.chat.id, text)
    
    elif data == "api_key":
        user = db.get_user(call.from_user.id)
        text = f"""
<b>🔑 YOUR API KEY</b>
╔════════════════════════════════════════╗
║ <code>{user[9]}</code>                         
╠════════════════════════════════════════╣
║ <b>📡 API ENDPOINTS</b>                      
║                                         
║ GET /api/user - User info              
║ GET /api/stats - System stats          
║ POST /api/deploy - Deploy bot          
║ GET /api/bots - List bots              
╠════════════════════════════════════════╣
║ ⚠️ Keep your API key secret!           
╚════════════════════════════════════════╝
"""
        bot.send_message(call.message.chat.id, text)
    
    bot.answer_callback_query(call.id)

# ==================== FLASK ROUTES ====================
@app.route('/')
def home():
    stats = db.get_stats()
    return jsonify({
        "status": "online",
        "brand": Config.BRAND_NAME,
        "version": Config.VERSION,
        "stats": stats,
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/stats')
def api_stats():
    return jsonify(db.get_stats())

@app.route('/api/user/<int:user_id>')
def api_user(user_id):
    user = db.get_user(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    return jsonify({
        "id": user[0],
        "username": user[1],
        "plan": user[4],
        "credits": user[6],
        "bot_limit": user[7],
        "referrals": user[12]
    })

@app.route('/api/bots/<int:user_id>')
def api_bots(user_id):
    bots = db.get_user_bots(user_id)
    return jsonify([{
        "id": b[0],
        "name": b[2],
        "status": b[6],
        "deploys": b[11]
    } for b in bots])

# ==================== BACKGROUND TASKS ====================
def cleanup_processes():
    while True:
        try:
            db.cursor.execute("SELECT id, pid FROM bots WHERE status='Running'")
            running = db.cursor.fetchall()
            
            for bot_id, pid in running:
                if pid:
                    try:
                        os.kill(pid, 0)
                    except OSError:
                        db.update_bot_status(bot_id, "Stopped")
            
            # Check expired subscriptions
            db.cursor.execute("UPDATE users SET plan='free', bot_limit=2 WHERE expiry_date < datetime('now') AND plan != 'free'")
            db.conn.commit()
            
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
        
        time.sleep(60)

# ==================== MAIN ====================
def run_bot():
    logger.info(f"Starting {Config.BRAND_NAME} v{Config.VERSION}")
    
    try:
        bot.remove_webhook()
        logger.info("Webhook removed")
    except Exception as e:
        logger.error(f"Webhook removal failed: {e}")
    
    time.sleep(2)
    
    while True:
        try:
            bot.infinity_polling(timeout=30, long_polling_timeout=30)
        except Exception as e:
            logger.error(f"Bot error: {e}")
            time.sleep(10)

if __name__ == '__main__':
    # Start cleanup thread
    threading.Thread(target=cleanup_processes, daemon=True).start()
    
    # Start bot thread
    threading.Thread(target=run_bot, daemon=True).start()
    
    # Start Flask
    logger.info(f"Starting Flask on port {Config.PORT}")
    app.run(host='0.0.0.0', port=Config.PORT, debug=False)
