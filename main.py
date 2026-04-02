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
import psutil
import requests
import re
import asyncio
from pathlib import Path
from telebot import types
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from flask import Flask, send_file, jsonify, request
from flask_cors import CORS
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

# ================== Configuration ==================
class Config:
    TOKEN = os.environ.get('BOT_TOKEN', '8754448627:AAF5eBQdCfV1bSNnE4BzSKIpiPSWrRNTnI4')
    ADMIN_ID = int(os.environ.get('ADMIN_ID', 6487613131))
    PROJECT_DIR = 'projects'
    DB_NAME = 'cyber_v2.db'
    PORT = int(os.environ.get('PORT', 10000))
    MAINTENANCE = False
    BACKUP_DIR = 'backups'
    LOGS_DIR = 'logs'
    
    ADMIN_USERNAME = 'aurponmodz' 
    BOT_USERNAME = "@aurpon_bot_host_bot" 
    SUPPORT_ID = "@aurponmodz" 
    BRAND_NAME = "💎𝐀𝐔𝐑𝐏𝐎𝐍 𝐇𝐎𝐒𝐓 💎" 
    
    MAX_FILE_SIZE = 5.5 * 1024 * 1024
    MAX_BOTS_PER_USER = 50
    AUTO_BACKUP_INTERVAL = 24  # ঘন্টা
    WEBHOOK_URL = os.environ.get('WEBHOOK_URL', '')
    
    ENCRYPTION_KEY = Fernet.generate_key()
    API_SECRET = os.environ.get('API_SECRET', 'your-secret-key-here')

cipher = Fernet(Config.ENCRYPTION_KEY)
bot = telebot.TeleBot(Config.TOKEN, parse_mode="HTML")
project_path = Path(Config.PROJECT_DIR)
project_path.mkdir(exist_ok=True)
Path(Config.BACKUP_DIR).mkdir(exist_ok=True)
Path(Config.LOGS_DIR).mkdir(exist_ok=True)
app = Flask(__name__)
CORS(app)

# ================== Database Functions ==================
def init_db():
    conn = sqlite3.connect(Config.DB_NAME)
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                (id INTEGER PRIMARY KEY, username TEXT, expiry TEXT, file_limit INTEGER, 
                 is_prime INTEGER, join_date TEXT, last_renewal TEXT, api_key TEXT, 
                 total_bots INTEGER DEFAULT 0, total_uptime INTEGER DEFAULT 0)''')
    
    # Keys table
    c.execute('''CREATE TABLE IF NOT EXISTS keys 
                (key TEXT PRIMARY KEY, duration_days INTEGER, file_limit INTEGER, 
                 created_date TEXT, used_by INTEGER, used_date TEXT)''')
    
    # Deployments table
    c.execute('''CREATE TABLE IF NOT EXISTS deployments 
                (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, bot_name TEXT, 
                 filename TEXT, pid INTEGER, start_time TEXT, status TEXT, 
                 cpu_usage REAL, ram_usage REAL, last_active TEXT, port INTEGER,
                 webhook_url TEXT, auto_restart INTEGER DEFAULT 1, env_vars TEXT)''')
    
    # Bot logs table
    c.execute('''CREATE TABLE IF NOT EXISTS bot_logs 
                (id INTEGER PRIMARY KEY AUTOINCREMENT, bot_id INTEGER, log_type TEXT, 
                 message TEXT, timestamp TEXT)''')
    
    # Payments table
    c.execute('''CREATE TABLE IF NOT EXISTS payments 
                (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount REAL, 
                 transaction_id TEXT, status TEXT, timestamp TEXT)''')
    
    # Announcements table
    c.execute('''CREATE TABLE IF NOT EXISTS announcements 
                (id INTEGER PRIMARY KEY AUTOINCREMENT, message TEXT, 
                 created_by INTEGER, timestamp TEXT)''')
    
    join_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    expiry_date = (datetime.now() + timedelta(days=3650)).strftime('%Y-%m-%d %H:%M:%S')
    api_key = cipher.encrypt(f"{Config.ADMIN_ID}:{uuid.uuid4()}".encode()).decode()
    
    c.execute("INSERT OR IGNORE INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", 
             (Config.ADMIN_ID, 'admin', expiry_date, 999, 1, join_date, join_date, api_key, 0, 0))
    
    conn.commit()
    conn.close()

init_db()

# ================== Advanced Helper Functions ==================
def get_user(user_id):
    conn = sqlite3.connect(Config.DB_NAME)
    c = conn.cursor()
    user = c.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    return user

def update_user_bot_count(user_id):
    conn = sqlite3.connect(Config.DB_NAME)
    c = conn.cursor()
    count = c.execute("SELECT COUNT(*) FROM deployments WHERE user_id=?", (user_id,)).fetchone()[0]
    c.execute("UPDATE users SET total_bots=? WHERE id=?", (count, user_id))
    conn.commit()
    conn.close()

def is_prime(user_id):
    user = get_user(user_id)
    if user and user[2]:
        try:
            expiry = datetime.strptime(user[2], '%Y-%m-%d %H:%M:%S')
            return expiry > datetime.now()
        except:
            return False
    return False

def get_user_bots(user_id, status=None):
    conn = sqlite3.connect(Config.DB_NAME)
    c = conn.cursor()
    if status:
        bots = c.execute("SELECT id, bot_name, filename, pid, start_time, status, port FROM deployments WHERE user_id=? AND status=?", (user_id, status)).fetchall()
    else:
        bots = c.execute("SELECT id, bot_name, filename, pid, start_time, status, port FROM deployments WHERE user_id=?", (user_id,)).fetchall()
    conn.close()
    return bots

def get_system_stats():
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        ram_percent = psutil.virtual_memory().percent
        disk_percent = psutil.disk_usage('/').percent
        return {
            'cpu_percent': cpu_percent,
            'ram_percent': ram_percent,
            'disk_percent': disk_percent,
            'cpu_count': psutil.cpu_count(),
            'total_ram': round(psutil.virtual_memory().total / (1024**3), 2),
            'available_ram': round(psutil.virtual_memory().available / (1024**3), 2)
        }
    except:
        return {
            'cpu_percent': random.randint(10, 60),
            'ram_percent': random.randint(20, 70),
            'disk_percent': random.randint(30, 80),
            'cpu_count': 4,
            'total_ram': 8,
            'available_ram': 4
        }

def get_total_stats():
    conn = sqlite3.connect(Config.DB_NAME)
    c = conn.cursor()
    total_users = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_bots = c.execute("SELECT COUNT(*) FROM deployments").fetchone()[0]
    running_bots = c.execute("SELECT COUNT(*) FROM deployments WHERE status='Running'").fetchone()[0]
    total_keys = c.execute("SELECT COUNT(*) FROM keys").fetchone()[0]
    conn.close()
    return {
        'total_users': total_users,
        'total_bots': total_bots,
        'running_bots': running_bots,
        'total_keys': total_keys
    }

def create_progress_bar(percentage):
    bars = int(percentage / 10)
    return "🟢" * bars + "⚪" * (10 - bars)

def log_bot_activity(bot_id, log_type, message):
    conn = sqlite3.connect(Config.DB_NAME)
    c = conn.cursor()
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    c.execute("INSERT INTO bot_logs (bot_id, log_type, message, timestamp) VALUES (?, ?, ?, ?)",
             (bot_id, log_type, message, timestamp))
    conn.commit()
    conn.close()

def auto_backup():
    backup_file = f"{Config.BACKUP_DIR}/backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    shutil.copy2(Config.DB_NAME, backup_file)
    # Keep only last 10 backups
    backups = sorted(Path(Config.BACKUP_DIR).glob("backup_*.db"))
    for old_backup in backups[:-10]:
        old_backup.unlink()

def schedule_auto_backup():
    schedule.every(Config.AUTO_BACKUP_INTERVAL).hours.do(auto_backup)
    while True:
        schedule.run_pending()
        time.sleep(60)

def monitor_bots():
    while True:
        conn = sqlite3.connect(Config.DB_NAME)
        c = conn.cursor()
        running_bots = c.execute("SELECT id, pid, bot_name, user_id, auto_restart FROM deployments WHERE status='Running'").fetchall()
        
        for bot_id, pid, bot_name, user_id, auto_restart in running_bots:
            try:
                if pid and pid > 0:
                    process = psutil.Process(pid)
                    cpu_usage = process.cpu_percent(interval=0.5)
                    ram_usage = process.memory_percent()
                    c.execute("UPDATE deployments SET cpu_usage=?, ram_usage=?, last_active=? WHERE id=?",
                             (cpu_usage, ram_usage, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), bot_id))
                else:
                    raise psutil.NoSuchProcess(pid)
            except:
                if auto_restart:
                    # Auto restart bot
                    bot_file = c.execute("SELECT filename FROM deployments WHERE id=?", (bot_id,)).fetchone()
                    if bot_file:
                        file_path = project_path / bot_file[0]
                        proc = subprocess.Popen(['python', str(file_path)], start_new_session=True)
                        c.execute("UPDATE deployments SET pid=?, status='Running', start_time=? WHERE id=?",
                                 (proc.pid, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), bot_id))
                        log_bot_activity(bot_id, "RESTART", "Bot auto-restarted by monitor")
                else:
                    c.execute("UPDATE deployments SET status='Crashed', pid=0 WHERE id=?", (bot_id,))
                    log_bot_activity(bot_id, "CRASH", "Bot crashed and auto-restart is disabled")
        
        conn.commit()
        conn.close()
        time.sleep(30)

# ================== Keyboards ==================
def main_menu_reply(user_id):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = types.KeyboardButton("📤 𝗨𝗽𝗹𝗼𝗮𝗱 𝗕𝗼𝘁")
    btn2 = types.KeyboardButton("🤖 𝗠𝘆 𝗕𝗼𝘁𝘀")
    btn3 = types.KeyboardButton("🚀 𝗗𝗲𝗽𝗹𝗼𝘆 𝗕𝗼𝘁")
    btn4 = types.KeyboardButton("📊 𝗗𝗮𝘀𝗵𝗯𝗼𝗮𝗿𝗱")
    btn5 = types.KeyboardButton("⚙️ 𝗦𝗲𝘁𝘁𝗶𝗻𝗴𝘀")
    btn6 = types.KeyboardButton("📢 𝗔𝗻𝗻𝗼𝘂𝗻𝗰𝗲𝗺𝗲𝗻𝘁𝘀")
    markup.add(btn1, btn2, btn3, btn4, btn5, btn6)
    return markup

def admin_panel_reply():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = types.KeyboardButton("👥 𝗨𝘀𝗲𝗿 𝗟𝗶𝘀𝘁")
    btn2 = types.KeyboardButton("🔑 𝗚𝗲𝗻𝗲𝗿𝗮𝘁𝗲 𝗞𝗲𝘆")
    btn3 = types.KeyboardButton("📊 𝗦𝘁𝗮𝘁𝘀")
    btn4 = types.KeyboardButton("📢 𝗕𝗿𝗼𝗮𝗱𝗰𝗮𝘀𝘁")
    btn5 = types.KeyboardButton("🔄 𝗕𝗮𝗰𝗸𝘂𝗽")
    btn6 = types.KeyboardButton("🏠 𝗠𝗮𝗶𝗻 𝗠𝗲𝗻𝘂")
    markup.add(btn1, btn2, btn3, btn4, btn5, btn6)
    return markup

# ================== Command Handlers ==================
@bot.message_handler(commands=['start'])
def welcome(message):
    uid = message.from_user.id
    username = message.from_user.username or "User"
    user = get_user(uid)
    
    if not user:
        # New user registration
        join_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        expiry_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
        api_key = cipher.encrypt(f"{uid}:{uuid.uuid4()}".encode()).decode()
        conn = sqlite3.connect(Config.DB_NAME)
        c = conn.cursor()
        c.execute("INSERT INTO users (id, username, expiry, file_limit, is_prime, join_date, last_renewal, api_key) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                 (uid, username, expiry_date, 5, 0, join_date, join_date, api_key))
        conn.commit()
        conn.close()
        user = get_user(uid)
    
    prime_status = "👑 𝗣𝗥𝗜𝗠𝗘 𝗔𝗗𝗠𝗜𝗡" if uid == Config.ADMIN_ID else ("💎 𝗣𝗥𝗜𝗠𝗘 𝗠𝗘𝗠𝗕𝗘𝗥" if is_prime(uid) else "👤 𝗙𝗥𝗘𝗘 𝗨𝗦𝗘𝗥")
    
    text = f"""
╔══════════════════════════╗
║     ✨ {Config.BRAND_NAME} ✨     ║
╠══════════════════════════╣
║ 👤 <b>𝗨𝘀𝗲𝗿:</b> @{username}
║ 🆔 <b>𝗜𝗗:</b> <code>{uid}</code>
║ 💎 <b>𝗦𝘁𝗮𝘁𝘂𝘀:</b> {prime_status}
║ 📅 <b>𝗝𝗼𝗶𝗻𝗲𝗱:</b> {user[5]}
╠══════════════════════════╣
║ 📊 <b>𝗔𝗰𝗰𝗼𝘂𝗻𝘁 𝗜𝗻𝗳𝗼</b>
║ • <b>𝗣𝗹𝗮𝗻:</b> {'Premium' if is_prime(uid) else 'Free'}
║ • <b>𝗙𝗶𝗹𝗲 𝗟𝗶𝗺𝗶𝘁:</b> <code>{user[3]}</code>
║ • <b>𝗘𝘅𝗽𝗶𝗿𝘆:</b> {user[2][:10] if user[2] else 'N/A'}
║ • <b>𝗧𝗼𝘁𝗮𝗹 𝗕𝗼𝘁𝘀:</b> <code>{user[8]}</code>
╚══════════════════════════╝
"""
    bot.send_message(message.chat.id, text, reply_markup=main_menu_reply(uid))

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id != Config.ADMIN_ID:
        return
    text = """
╔══════════════════════════╗
║     👑 𝗔𝗗𝗠𝗜𝗡 𝗣𝗔𝗡𝗘𝗟 👑     ║
╠══════════════════════════╣
║ <b>📌 Available Actions:</b>
║ • 👥 View all users
║ • 🔑 Generate premium keys
║ • 📊 View system stats
║ • 📢 Send broadcasts
║ • 🔄 Create backups
╚══════════════════════════╝
"""
    bot.send_message(message.chat.id, text, reply_markup=admin_panel_reply())

@bot.message_handler(func=lambda message: message.text == "🏠 𝗠𝗮𝗶𝗻 𝗠𝗲𝗻𝘂")
def back_to_main(message):
    welcome(message)

@bot.message_handler(func=lambda message: message.text == "⚙️ 𝗦𝗲𝘁𝘁𝗶𝗻𝗴𝘀")
def settings_menu(message):
    uid = message.from_user.id
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("🤖 Auto Restart", callback_data=f"toggle_restart_{uid}")
    btn2 = types.InlineKeyboardButton("🔑 API Key", callback_data=f"show_api_{uid}")
    btn3 = types.InlineKeyboardButton("📊 Analytics", callback_data=f"analytics_{uid}")
    btn4 = types.InlineKeyboardButton("🗑️ Clear Logs", callback_data=f"clear_logs_{uid}")
    markup.add(btn1, btn2, btn3, btn4)
    bot.send_message(message.chat.id, "<b>⚙️ 𝗦𝗲𝘁𝘁𝗶𝗻𝗴𝘀 𝗣𝗮𝗻𝗲𝗹</b>\nSelect an option:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('toggle_restart_'))
def toggle_auto_restart(call):
    user_id = int(call.data.split('_')[2])
    if call.from_user.id != user_id:
        bot.answer_callback_query(call.id, "❌ Access Denied!")
        return
    
    conn = sqlite3.connect(Config.DB_NAME)
    c = conn.cursor()
    current = c.execute("SELECT auto_restart FROM deployments WHERE user_id=? AND status='Running'", (user_id,)).fetchone()
    new_value = 0 if current and current[0] else 1
    c.execute("UPDATE deployments SET auto_restart=? WHERE user_id=?", (new_value, user_id))
    conn.commit()
    conn.close()
    
    status = "✅ ENABLED" if new_value else "❌ DISABLED"
    bot.answer_callback_query(call.id, f"Auto Restart {status}")
    bot.edit_message_text(f"<b>⚙️ Auto Restart has been {status}</b>\nAll your running bots will {'now auto-restart on crash' if new_value else 'no longer auto-restart'}.", 
                         call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('show_api_'))
def show_api_key(call):
    user_id = int(call.data.split('_')[2])
    if call.from_user.id != user_id:
        bot.answer_callback_query(call.id, "❌ Access Denied!")
        return
    
    conn = sqlite3.connect(Config.DB_NAME)
    c = conn.cursor()
    api_key = c.execute("SELECT api_key FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    
    if api_key:
        bot.answer_callback_query(call.id, "API Key sent in DM")
        bot.send_message(call.message.chat.id, f"<b>🔑 Your API Key:</b>\n<code>{api_key[0]}</code>\n\n<b>📌 Usage:</b>\nUse this key for external API access.")
    else:
        bot.answer_callback_query(call.id, "No API Key found")

@bot.message_handler(func=lambda message: message.text == "📤 𝗨𝗽𝗹𝗼𝗮𝗱 𝗕𝗼𝘁")
def upload_handler(message):
    user = get_user(message.from_user.id)
    if user[8] >= Config.MAX_BOTS_PER_USER and not is_prime(message.from_user.id):
        bot.reply_to(message, f"<b>❌ Bot limit reached! Max {Config.MAX_BOTS_PER_USER} bots for free users.\nUpgrade to Prime for unlimited bots!</b>")
        return
    
    msg = bot.reply_to(message, """
<b>📤 𝗨𝗣𝗟𝗢𝗔𝗗 𝗕𝗢𝗧 𝗙𝗜𝗟𝗘</b>
<b>━━━━━━━━━━━━━━━━━━━━━━</b>
<b>📁 Supported formats:</b> .py, .zip
<b>📦 Max size:</b> 5.5 MB
<b>🤖 Bot name:</b> Will ask after upload

<b>💡 Tips:</b>
• Use requirements.txt for dependencies
• Include a main function
• Test locally before uploading

<b>📤 Send your file now:</b>
""")
    bot.register_next_step_handler(msg, upload_file_step)

def upload_file_step(message):
    uid = message.from_user.id
    chat_id = message.chat.id
    
    if message.content_type == 'document':
        try:
            file_name = message.document.file_name.lower()
            if not (file_name.endswith('.py') or file_name.endswith('.zip')):
                bot.send_message(chat_id, "<b>❌ Only Python (.py) or ZIP (.zip) files allowed!</b>")
                return
            
            file_size = message.document.file_size
            if file_size > Config.MAX_FILE_SIZE:
                bot.send_message(chat_id, f"<b>❌ File too large! Max {Config.MAX_FILE_SIZE/1024/1024}MB</b>")
                return
            
            status_msg = bot.send_message(chat_id, "<b>📥 Downloading file... 0%</b>")
            
            file_info = bot.get_file(message.document.file_id)
            downloaded = bot.download_file(file_info.file_path)
            
            bot.edit_message_text("<b>📥 Downloading file... 100%</b>", chat_id, status_msg.message_id)
            
            safe_name = secure_filename(message.document.file_name)
            file_path = project_path / safe_name
            file_path.write_bytes(downloaded)
            
            # Check if it's a ZIP file and extract
            if file_name.endswith('.zip'):
                bot.edit_message_text("<b>📦 Extracting ZIP file...</b>", chat_id, status_msg.message_id)
                extract_dir = project_path / safe_name.replace('.zip', '')
                extract_dir.mkdir(exist_ok=True)
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
                # Look for main.py or bot.py
                main_file = None
                for py_file in extract_dir.glob("*.py"):
                    if py_file.name in ['main.py', 'bot.py', 'app.py']:
                        main_file = py_file
                        break
                if not main_file:
                    main_file = list(extract_dir.glob("*.py"))[0] if list(extract_dir.glob("*.py")) else None
                
                if main_file:
                    safe_name = secure_filename(main_file.name)
                    shutil.move(str(main_file), str(project_path / safe_name))
                    shutil.rmtree(extract_dir)
                    file_path.unlink()
                else:
                    bot.send_message(chat_id, "<b>❌ No Python file found in ZIP!</b>")
                    return
            
            msg = bot.send_message(chat_id, "<b>✅ File uploaded!\n\n🤖 Enter a name for your bot (max 30 chars):</b>")
            bot.register_next_step_handler(msg, save_bot_name, safe_name)
            
        except Exception as e:
            bot.send_message(chat_id, f"<b>❌ Error: {str(e)}</b>")
    else:
        bot.send_message(chat_id, "<b>❌ Please send a valid file!</b>")

def save_bot_name(message, safe_name):
    uid = message.from_user.id
    bot_name = message.text.strip()[:30]
    
    conn = sqlite3.connect(Config.DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO deployments (user_id, bot_name, filename, pid, start_time, status, last_active, auto_restart) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
             (uid, bot_name, safe_name, 0, None, "Uploaded", datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 1))
    bot_id = c.lastrowid
    conn.commit()
    conn.close()
    
    update_user_bot_count(uid)
    
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton("📚 Install Libs", callback_data=f"install_libs_{bot_id}")
    btn2 = types.InlineKeyboardButton("🚀 Deploy Now", callback_data=f"deploy_{bot_id}")
    btn3 = types.InlineKeyboardButton("📦 Set Env Vars", callback_data=f"set_env_{bot_id}")
    markup.add(btn1, btn2)
    markup.add(btn3)
    
    bot.send_message(message.chat.id, f"""
<b>✅ Bot '{bot_name}' uploaded successfully!</b>

<b>📊 Bot Info:</b>
• <b>ID:</b> <code>{bot_id}</code>
• <b>File:</b> <code>{safe_name}</code>
• <b>Status:</b> 📤 Uploaded

<b>🔧 Next steps:</b>
1. Install required libraries
2. Set environment variables (if needed)
3. Deploy the bot

Click buttons below to continue:
""", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('install_libs_'))
def install_libraries_callback(call):
    bot_id = int(call.data.split('_')[2])
    
    msg = bot.send_message(call.message.chat.id, """
<b>📚 INSTALL LIBRARIES</b>

<b>📌 Enter pip commands:</b>
Example:
<code>pip install requests telebot</code>
<code>pip install flask pillow</code>

<b>💡 Tip:</b> One command per line
""")
    bot.register_next_step_handler(msg, install_libraries_step, bot_id)

def install_libraries_step(message, bot_id):
    commands = [cmd.strip() for cmd in message.text.strip().split('\n') if cmd.strip() and 'pip install' in cmd]
    
    if not commands:
        bot.send_message(message.chat.id, "<b>❌ No valid pip commands found!</b>")
        return
    
    status_msg = bot.send_message(message.chat.id, "<b>🛠 Installing libraries... 0%</b>")
    
    results = []
    for i, cmd in enumerate(commands):
        bot.edit_message_text(f"<b>🛠 Installing libraries... {int((i+1)/len(commands)*100)}%</b>", 
                             message.chat.id, status_msg.message_id)
        
        result = subprocess.run(cmd.split(), capture_output=True, text=True)
        if result.returncode == 0:
            results.append(f"✅ <code>{cmd}</code>")
            log_bot_activity(bot_id, "LIB_INSTALL", f"Success: {cmd}")
        else:
            results.append(f"❌ <code>{cmd}</code> - {result.stderr[:100]}")
            log_bot_activity(bot_id, "LIB_ERROR", f"Failed: {cmd} - {result.stderr[:200]}")
    
    bot.edit_message_text(f"<b>📊 Installation Results:</b>\n\n" + "\n".join(results[:10]) + 
                         (f"\n... and {len(results)-10} more" if len(results) > 10 else ""), 
                         message.chat.id, status_msg.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('set_env_'))
def set_environment_vars(call):
    bot_id = int(call.data.split('_')[2])
    
    msg = bot.send_message(call.message.chat.id, """
<b>📦 SET ENVIRONMENT VARIABLES</b>

<b>📌 Format:</b> KEY=VALUE (one per line)
Example:
<code>BOT_TOKEN=123456:ABC-DEF</code>
<code>API_KEY=your-api-key</code>
<code>DATABASE_URL=sqlite:///bot.db</code>

<b>💡 Leave empty to skip</b>
""")
    bot.register_next_step_handler(msg, save_environment_vars, bot_id)

def save_environment_vars(message, bot_id):
    env_vars = {}
    for line in message.text.strip().split('\n'):
        if '=' in line:
            key, value = line.split('=', 1)
            env_vars[key.strip()] = value.strip()
    
    if env_vars:
        conn = sqlite3.connect(Config.DB_NAME)
        c = conn.cursor()
        c.execute("UPDATE deployments SET env_vars=? WHERE id=?", (json.dumps(env_vars), bot_id))
        conn.commit()
        conn.close()
        bot.send_message(message.chat.id, f"<b>✅ Saved {len(env_vars)} environment variables!</b>")
    else:
        bot.send_message(message.chat.id, "<b>ℹ️ No environment variables saved</b>")

@bot.message_handler(func=lambda message: message.text == "🤖 𝗠𝘆 𝗕𝗼𝘁𝘀")
def show_my_bots(message):
    uid = message.from_user.id
    bots = get_user_bots(uid)
    
    if not bots:
        bot.reply_to(message, "<b>🤖 No bots found!\n\n📤 Upload a bot using 'Upload Bot' button.</b>")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    for bot_id, bot_name, filename, pid, start_time, status, port in bots:
        status_icon = "🟢" if status == "Running" else ("🟡" if status == "Stopped" else "🔴")
        btn = types.InlineKeyboardButton(f"{status_icon} {bot_name[:20]}", callback_data=f"bot_{bot_id}")
        markup.add(btn)
    
    bot.send_message(message.chat.id, f"<b>🤖 YOUR BOTS ({len(bots)})</b>\n\nClick on any bot to manage it:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('bot_'))
def manage_bot(call):
    bot_id = int(call.data.split('_')[1])
    
    conn = sqlite3.connect(Config.DB_NAME)
    c = conn.cursor()
    bot_info = c.execute("SELECT * FROM deployments WHERE id=?", (bot_id,)).fetchone()
    conn.close()
    
    if not bot_info:
        bot.answer_callback_query(call.id, "Bot not found!")
        return
    
    status_icon = "🟢" if bot_info[6] == "Running" else ("🟡" if bot_info[6] == "Stopped" else "🔴")
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    if bot_info[6] == "Running":
        markup.add(types.InlineKeyboardButton("⏹️ Stop", callback_data=f"stop_{bot_id}"))
    else:
        markup.add(types.InlineKeyboardButton("▶️ Start", callback_data=f"start_{bot_id}"))
    
    markup.add(types.InlineKeyboardButton("🔄 Restart", callback_data=f"restart_{bot_id}"))
    markup.add(types.InlineKeyboardButton("📋 Logs", callback_data=f"logs_{bot_id}"))
    markup.add(types.InlineKeyboardButton("📊 Stats", callback_data=f"stats_{bot_id}"))
    markup.add(types.InlineKeyboardButton("🗑️ Delete", callback_data=f"delete_{bot_id}"))
    markup.add(types.InlineKeyboardButton("📦 Export", callback_data=f"export_{bot_id}"))
    markup.add(types.InlineKeyboardButton("⚙️ Settings", callback_data=f"settings_{bot_id}"))
    
    text = f"""
<b>🤖 BOT MANAGEMENT</b>
<b>━━━━━━━━━━━━━━━━━━━━━━</b>
<b>📌 Name:</b> {bot_info[2]}
<b>📁 File:</b> <code>{bot_info[3]}</code>
<b>📊 Status:</b> {status_icon} {bot_info[6]}
<b>🆔 PID:</b> <code>{bot_info[4] or 'N/A'}</code>
<b>🚀 Started:</b> {bot_info[5] or 'Not started'}
<b>💾 CPU:</b> {bot_info[7] or 0}% | <b>RAM:</b> {bot_info[8] or 0}%
<b>🔄 Auto-Restart:</b> {'✅ ON' if bot_info[11] else '❌ OFF'}
<b>━━━━━━━━━━━━━━━━━━━━━━</b>

Select an action below:
"""
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('start_'))
def start_bot_callback(call):
    bot_id = int(call.data.split('_')[1])
    uid = call.from_user.id
    
    conn = sqlite3.connect(Config.DB_NAME)
    c = conn.cursor()
    bot_info = c.execute("SELECT user_id, filename, env_vars FROM deployments WHERE id=?", (bot_id,)).fetchone()
    
    if not bot_info or bot_info[0] != uid:
        bot.answer_callback_query(call.id, "❌ Access Denied!")
        conn.close()
        return
    
    try:
        file_path = project_path / bot_info[1]
        env = os.environ.copy()
        if bot_info[2]:
            env_vars = json.loads(bot_info[2])
            env.update(env_vars)
        
        proc = subprocess.Popen(['python', str(file_path)], start_new_session=True, env=env)
        start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        c.execute("UPDATE deployments SET pid=?, start_time=?, status='Running', last_active=? WHERE id=?",
                 (proc.pid, start_time, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), bot_id))
        conn.commit()
        
        log_bot_activity(bot_id, "START", f"Bot started by user {uid}")
        bot.answer_callback_query(call.id, "✅ Bot started successfully!")
        
        # Refresh the management panel
        manage_bot(call)
        
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ Failed: {str(e)[:50]}")
    
    conn.close()

@bot.callback_query_handler(func=lambda call: call.data.startswith('stop_'))
def stop_bot_callback(call):
    bot_id = int(call.data.split('_')[1])
    uid = call.from_user.id
    
    conn = sqlite3.connect(Config.DB_NAME)
    c = conn.cursor()
    bot_info = c.execute("SELECT user_id, pid FROM deployments WHERE id=?", (bot_id,)).fetchone()
    
    if not bot_info or bot_info[0] != uid:
        bot.answer_callback_query(call.id, "❌ Access Denied!")
        conn.close()
        return
    
    try:
        if bot_info[1] and bot_info[1] > 0:
            os.kill(bot_info[1], signal.SIGTERM)
        c.execute("UPDATE deployments SET status='Stopped', pid=0 WHERE id=?", (bot_id,))
        conn.commit()
        
        log_bot_activity(bot_id, "STOP", f"Bot stopped by user {uid}")
        bot.answer_callback_query(call.id, "⏹️ Bot stopped!")
        
        manage_bot(call)
        
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ Failed: {str(e)[:50]}")
    
    conn.close()

@bot.callback_query_handler(func=lambda call: call.data.startswith('restart_'))
def restart_bot_callback(call):
    bot_id = int(call.data.split('_')[1])
    uid = call.from_user.id
    
    conn = sqlite3.connect(Config.DB_NAME)
    c = conn.cursor()
    bot_info = c.execute("SELECT user_id, filename, pid, env_vars FROM deployments WHERE id=?", (bot_id,)).fetchone()
    
    if not bot_info or bot_info[0] != uid:
        bot.answer_callback_query(call.id, "❌ Access Denied!")
        conn.close()
        return
    
    try:
        # Stop existing process
        if bot_info[2] and bot_info[2] > 0:
            try:
                os.kill(bot_info[2], signal.SIGTERM)
            except:
                pass
        
        # Start new process
        file_path = project_path / bot_info[1]
        env = os.environ.copy()
        if bot_info[3]:
            env_vars = json.loads(bot_info[3])
            env.update(env_vars)
        
        proc = subprocess.Popen(['python', str(file_path)], start_new_session=True, env=env)
        start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        c.execute("UPDATE deployments SET pid=?, start_time=?, status='Running', last_active=? WHERE id=?",
                 (proc.pid, start_time, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), bot_id))
        conn.commit()
        
        log_bot_activity(bot_id, "RESTART", f"Bot restarted by user {uid}")
        bot.answer_callback_query(call.id, "🔄 Bot restarted!")
        
        manage_bot(call)
        
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ Failed: {str(e)[:50]}")
    
    conn.close()

@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_'))
def delete_bot_callback(call):
    bot_id = int(call.data.split('_')[1])
    uid = call.from_user.id
    
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton("✅ Yes, Delete", callback_data=f"confirm_delete_{bot_id}")
    btn2 = types.InlineKeyboardButton("❌ No, Cancel", callback_data=f"cancel_delete_{bot_id}")
    markup.add(btn1, btn2)
    
    bot.edit_message_text("<b>⚠️ Are you sure you want to delete this bot?\n\nThis action cannot be undone!</b>", 
                         call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_delete_'))
def confirm_delete_bot(call):
    bot_id = int(call.data.split('_')[2])
    uid = call.from_user.id
    
    conn = sqlite3.connect(Config.DB_NAME)
    c = conn.cursor()
    bot_info = c.execute("SELECT user_id, filename, pid FROM deployments WHERE id=?", (bot_id,)).fetchone()
    
    if not bot_info or bot_info[0] != uid:
        bot.answer_callback_query(call.id, "❌ Access Denied!")
        conn.close()
        return
    
    try:
        if bot_info[2] and bot_info[2] > 0:
            try:
                os.kill(bot_info[2], signal.SIGKILL)
            except:
                pass
        
        file_path = project_path / bot_info[1]
        if file_path.exists():
            file_path.unlink()
        
        c.execute("DELETE FROM deployments WHERE id=?", (bot_id,))
        c.execute("DELETE FROM bot_logs WHERE bot_id=?", (bot_id,))
        conn.commit()
        
        update_user_bot_count(uid)
        
        bot.answer_callback_query(call.id, "🗑️ Bot deleted!")
        bot.edit_message_text("<b>✅ Bot has been deleted successfully!</b>", 
                             call.message.chat.id, call.message.message_id)
        
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ Failed: {str(e)[:50]}")
    
    conn.close()

@bot.callback_query_handler(func=lambda call: call.data.startswith('cancel_delete_'))
def cancel_delete_bot(call):
    bot_id = int(call.data.split('_')[2])
    bot.answer_callback_query(call.id, "❌ Deletion cancelled")
    manage_bot(call)

@bot.callback_query_handler(func=lambda call: call.data.startswith('logs_'))
def show_bot_logs(call):
    bot_id = int(call.data.split('_')[1])
    
    conn = sqlite3.connect(Config.DB_NAME)
    c = conn.cursor()
    logs = c.execute("SELECT log_type, message, timestamp FROM bot_logs WHERE bot_id=? ORDER BY id DESC LIMIT 20", (bot_id,)).fetchall()
    conn.close()
    
    if not logs:
        bot.answer_callback_query(call.id, "No logs found")
        return
    
    log_text = "<b>📋 BOT LOGS (Last 20)</b>\n<b>━━━━━━━━━━━━━━━━━━━━━━</b>\n"
    for log_type, message, timestamp in logs:
        icon = "📝" if log_type == "START" else ("⏹️" if log_type == "STOP" else ("🔄" if log_type == "RESTART" else "⚠️"))
        log_text += f"{icon} <b>{log_type}</b> | {timestamp[5:16]}\n<code>{message[:60]}</code>\n"
    
    if len(log_text) > 4000:
        log_text = log_text[:4000] + "..."
    
    bot.send_message(call.message.chat.id, log_text)

@bot.callback_query_handler(func=lambda call: call.data.startswith('stats_'))
def show_bot_stats(call):
    bot_id = int(call.data.split('_')[1])
    
    conn = sqlite3.connect(Config.DB_NAME)
    c = conn.cursor()
    bot_info = c.execute("SELECT cpu_usage, ram_usage, start_time, last_active, status FROM deployments WHERE id=?", (bot_id,)).fetchone()
    conn.close()
    
    if not bot_info:
        bot.answer_callback_query(call.id, "Bot not found")
        return
    
    text = f"""
<b>📊 BOT STATISTICS</b>
<b>━━━━━━━━━━━━━━━━━━━━━━</b>
<b>💾 CPU Usage:</b> {create_progress_bar(int(bot_info[0] or 0))} {bot_info[0] or 0}%
<b>📀 RAM Usage:</b> {create_progress_bar(int(bot_info[1] or 0))} {bot_info[1] or 0}%
<b>🚀 Started:</b> {bot_info[2] or 'N/A'}
<b>🕐 Last Active:</b> {bot_info[3] or 'N/A'}
<b>📊 Status:</b> {'🟢 Online' if bot_info[4] == 'Running' else '🔴 Offline'}
<b>━━━━━━━━━━━━━━━━━━━━━━</b>

<b>💡 Tip:</b> Use 'Restart' if stats show high usage
"""
    bot.send_message(call.message.chat.id, text)

@bot.callback_query_handler(func=lambda call: call.data.startswith('export_'))
def export_bot_callback(call):
    bot_id = int(call.data.split('_')[1])
    uid = call.from_user.id
    
    conn = sqlite3.connect(Config.DB_NAME)
    c = conn.cursor()
    bot_info = c.execute("SELECT user_id, bot_name, filename FROM deployments WHERE id=?", (bot_id,)).fetchone()
    conn.close()
    
    if not bot_info or bot_info[0] != uid:
        bot.answer_callback_query(call.id, "❌ Access Denied!")
        return
    
    try:
        bot.answer_callback_query(call.id, "📦 Exporting bot...")
        
        export_dir = Path('exports')
        export_dir.mkdir(exist_ok=True)
        zip_filename = f"{bot_info[1]}_{int(time.time())}.zip"
        zip_path = export_dir / zip_filename
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            bot_file_path = project_path / bot_info[2]
            if bot_file_path.exists():
                zipf.write(bot_file_path, arcname=bot_info[2])
            
            metadata = {
                'bot_name': bot_info[1],
                'filename': bot_info[2],
                'export_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'user_id': uid,
                'version': '3.0.1'
            }
            zipf.writestr('metadata.json', json.dumps(metadata, indent=4))
        
        with open(zip_path, 'rb') as f:
            bot.send_document(call.message.chat.id, f, caption=f"<b>📦 Exported: {bot_info[1]}</b>\n<b>📅 Date:</b> {metadata['export_date']}")
        
        zip_path.unlink()
        
    except Exception as e:
        bot.send_message(call.message.chat.id, f"<b>❌ Export failed: {str(e)}</b>")

@bot.callback_query_handler(func=lambda call: call.data.startswith('settings_'))
def bot_settings(call):
    bot_id = int(call.data.split('_')[1])
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn1 = types.InlineKeyboardButton("🔄 Toggle Auto-Restart", callback_data=f"toggle_auto_{bot_id}")
    btn2 = types.InlineKeyboardButton("📦 Set Environment Vars", callback_data=f"set_env_{bot_id}")
    btn3 = types.InlineKeyboardButton("📚 Install Libraries", callback_data=f"install_libs_{bot_id}")
    btn4 = types.InlineKeyboardButton("◀️ Back", callback_data=f"bot_{bot_id}")
    markup.add(btn1, btn2, btn3, btn4)
    
    bot.edit_message_text("<b>⚙️ BOT SETTINGS</b>\n\nConfigure your bot's behavior below:", 
                         call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('toggle_auto_'))
def toggle_bot_auto_restart(call):
    bot_id = int(call.data.split('_')[2])
    
    conn = sqlite3.connect(Config.DB_NAME)
    c = conn.cursor()
    current = c.execute("SELECT auto_restart FROM deployments WHERE id=?", (bot_id,)).fetchone()
    new_value = 0 if current and current[0] else 1
    c.execute("UPDATE deployments SET auto_restart=? WHERE id=?", (new_value, bot_id))
    conn.commit()
    conn.close()
    
    status = "✅ ENABLED" if new_value else "❌ DISABLED"
    bot.answer_callback_query(call.id, f"Auto-Restart {status}")
    bot_settings(call)

@bot.message_handler(func=lambda message: message.text == "🚀 𝗗𝗲𝗽𝗹𝗼𝘆 𝗕𝗼𝘁")
def deploy_bot_handler(message):
    uid = message.from_user.id
    bots = get_user_bots(uid, "Uploaded")
    
    if not bots:
        bot.reply_to(message, "<b>📭 No uploaded bots found!\n\nFirst upload a bot using 'Upload Bot' button.</b>")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for bot_id, bot_name, filename, pid, start_time, status, port in bots:
        btn = types.InlineKeyboardButton(f"📤 {bot_name}", callback_data=f"deploy_{bot_id}")
        markup.add(btn)
    
    bot.send_message(message.chat.id, f"<b>🚀 DEPLOY BOT</b>\n\nSelect a bot to deploy ({len(bots)} available):", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('deploy_'))
def deploy_selected_bot(call):
    bot_id = int(call.data.split('_')[1])
    uid = call.from_user.id
    
    conn = sqlite3.connect(Config.DB_NAME)
    c = conn.cursor()
    bot_info = c.execute("SELECT user_id, bot_name, filename, env_vars FROM deployments WHERE id=?", (bot_id,)).fetchone()
    
    if not bot_info or bot_info[0] != uid:
        bot.answer_callback_query(call.id, "❌ Access Denied!")
        conn.close()
        return
    
    try:
        status_msg = bot.send_message(call.message.chat.id, f"<b>🚀 Deploying {bot_info[1]}...</b>")
        
        file_path = project_path / bot_info[2]
        env = os.environ.copy()
        if bot_info[3]:
            env_vars = json.loads(bot_info[3])
            env.update(env_vars)
        
        proc = subprocess.Popen(['python', str(file_path)], start_new_session=True, env=env)
        start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        c.execute("UPDATE deployments SET pid=?, start_time=?, status='Running', last_active=? WHERE id=?",
                 (proc.pid, start_time, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), bot_id))
        conn.commit()
        
        log_bot_activity(bot_id, "START", f"Bot deployed by user {uid}")
        
        bot.edit_message_text(f"""
<b>✅ {bot_info[1]} DEPLOYED SUCCESSFULLY!</b>

<b>📊 Deployment Info:</b>
• <b>PID:</b> <code>{proc.pid}</code>
• <b>Started:</b> {start_time}
• <b>Status:</b> 🟢 Running

<b>🔧 Manage your bot:</b>
Use 'My Bots' button to control it.
""", call.message.chat.id, status_msg.message_id)
        
    except Exception as e:
        bot.edit_message_text(f"<b>❌ Deployment failed: {str(e)}</b>", 
                             call.message.chat.id, status_msg.message_id)
    
    conn.close()

@bot.message_handler(func=lambda message: message.text == "📊 𝗗𝗮𝘀𝗵𝗯𝗼𝗮𝗿𝗱")
def show_dashboard(message):
    uid = message.from_user.id
    user = get_user(uid)
    stats = get_system_stats()
    total_stats = get_total_stats()
    
    if uid == Config.ADMIN_ID:
        text = f"""
╔══════════════════════════╗
║     📊 𝗔𝗗𝗠𝗜𝗡 𝗗𝗔𝗦𝗛𝗕𝗢𝗔𝗥𝗗     ║
╠══════════════════════════╣
║ 👥 <b>Total Users:</b> {total_stats['total_users']}
║ 🤖 <b>Total Bots:</b> {total_stats['total_bots']}
║ 🟢 <b>Running:</b> {total_stats['running_bots']}
║ 🔑 <b>Keys Generated:</b> {total_stats['total_keys']}
╠══════════════════════════╣
║ 🖥️ <b>SERVER STATUS</b>
║ • <b>CPU:</b> {create_progress_bar(int(stats['cpu_percent']))} {stats['cpu_percent']:.1f}%
║ • <b>RAM:</b> {create_progress_bar(int(stats['ram_percent']))} {stats['ram_percent']:.1f}%
║ • <b>DISK:</b> {create_progress_bar(int(stats['disk_percent']))} {stats['disk_percent']:.1f}%
║ • <b>Cores:</b> {stats['cpu_count']} | <b>RAM:</b> {stats['total_ram']}GB
╚══════════════════════════╝
"""
    else:
        prime_check = check_prime_expiry(uid)
        text = f"""
╔══════════════════════════╗
║     📊 𝗨𝗦𝗘𝗥 𝗗𝗔𝗦𝗛𝗕𝗢𝗔𝗥𝗗     ║
╠══════════════════════════╣
║ 💎 <b>Plan:</b> {'Premium' if is_prime(uid) else 'Free'}
║ 📦 <b>File Limit:</b> {user[3]}
║ 🤖 <b>Your Bots:</b> {user[8]}
║ 📅 <b>Expires:</b> {user[2][:10] if user[2] else 'N/A'}
╠══════════════════════════╣
║ 🖥️ <b>SERVER STATUS</b>
║ • <b>CPU:</b> {create_progress_bar(int(stats['cpu_percent']))} {stats['cpu_percent']:.1f}%
║ • <b>RAM:</b> {create_progress_bar(int(stats['ram_percent']))} {stats['ram_percent']:.1f}%
║ • <b>DISK:</b> {create_progress_bar(int(stats['disk_percent']))} {stats['disk_percent']:.1f}%
╚══════════════════════════╝
"""
    
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda message: message.text == "📢 𝗔𝗻𝗻𝗼𝘂𝗻𝗰𝗲𝗺𝗲𝗻𝘁𝘀")
def show_announcements(message):
    conn = sqlite3.connect(Config.DB_NAME)
    c = conn.cursor()
    announcements = c.execute("SELECT message, created_by, timestamp FROM announcements ORDER BY id DESC LIMIT 10").fetchall()
    conn.close()
    
    if not announcements:
        bot.send_message(message.chat.id, "<b>📢 No announcements yet!</b>")
        return
    
    text = "<b>📢 LATEST ANNOUNCEMENTS</b>\n<b>━━━━━━━━━━━━━━━━━━━━━━</b>\n\n"
    for msg, created_by, timestamp in announcements:
        text += f"<b>📅 {timestamp[:16]}</b>\n{msg}\n<b>━━━━━━━━━━━━━━━━━━━━━━</b>\n\n"
    
    bot.send_message(message.chat.id, text)

# ================== Admin Handlers ==================
@bot.message_handler(func=lambda message: message.text == "👥 𝗨𝘀𝗲𝗿 𝗟𝗶𝘀𝘁")
def admin_user_list(message):
    if message.from_user.id != Config.ADMIN_ID:
        return
    
    conn = sqlite3.connect(Config.DB_NAME)
    c = conn.cursor()
    users = c.execute("SELECT id, username, expiry, total_bots FROM users ORDER BY id").fetchall()
    conn.close()
    
    text = "<b>👥 USER LIST</b>\n<b>━━━━━━━━━━━━━━━━━━━━━━</b>\n\n"
    for uid, username, expiry, bots in users:
        status = "👑 ADMIN" if uid == Config.ADMIN_ID else ("💎 PRIME" if is_prime(uid) else "👤 USER")
        text += f"<b>ID:</b> <code>{uid}</code> | <b>{status}</b>\n<b>👤 @{username}</b> | 🤖 {bots} bots\n<b>📅 Exp:</b> {expiry[:10] if expiry else 'N/A'}\n<b>━━━━━━━━━━━━━━━━━━━━━━</b>\n\n"
    
    if len(text) > 4000:
        text = text[:4000] + "..."
    
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda message: message.text == "🔑 𝗚𝗲𝗻𝗲𝗿𝗮𝘁𝗲 𝗞𝗲𝘆")
def admin_generate_key(message):
    if message.from_user.id != Config.ADMIN_ID:
        return
    
    msg = bot.reply_to(message, """
<b>🔑 GENERATE PREMIUM KEY</b>

<b>📌 Enter duration (days):</b>
Example: <code>30</code> for 30 days
<b>📌 Enter file limit:</b>
Example: <code>50</code> for 50 bots

<b>Format:</b> <code>days file_limit</code>
Example: <code>30 50</code>
""")
    bot.register_next_step_handler(msg, process_key_generation)

def process_key_generation(message):
    try:
        parts = message.text.strip().split()
        days = int(parts[0])
        file_limit = int(parts[1]) if len(parts) > 1 else 10
        
        key = f"PRIME-{uuid.uuid4().hex[:12].upper()}"
        created_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        conn = sqlite3.connect(Config.DB_NAME)
        c = conn.cursor()
        c.execute("INSERT INTO keys (key, duration_days, file_limit, created_date) VALUES (?, ?, ?, ?)",
                 (key, days, file_limit, created_date))
        conn.commit()
        conn.close()
        
        bot.send_message(message.chat.id, f"""
<b>✅ KEY GENERATED SUCCESSFULLY!</b>

<b>🔑 Key:</b> <code>{key}</code>
<b>📅 Duration:</b> {days} days
<b>📦 File Limit:</b> {file_limit} bots

<b>📌 Send this key to users for premium access.</b>
""")
    except:
        bot.send_message(message.chat.id, "<b>❌ Invalid format! Use: days file_limit</b>")

@bot.message_handler(func=lambda message: message.text == "📊 𝗦𝘁𝗮𝘁𝘀")
def admin_stats(message):
    if message.from_user.id != Config.ADMIN_ID:
        return
    
    stats = get_system_stats()
    total_stats = get_total_stats()
    
    # Calculate uptime
    try:
        uptime_seconds = time.time() - psutil.boot_time()
        days = int(uptime_seconds // 86400)
        hours = int((uptime_seconds % 86400) // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        uptime_str = f"{days}d {hours}h {minutes}m"
    except:
        uptime_str = "N/A"
    
    text = f"""
╔══════════════════════════╗
║     📊 𝗦𝗬𝗦𝗧𝗘𝗠 𝗦𝗧𝗔𝗧𝗦     ║
╠══════════════════════════╣
║ 📈 <b>USERS & BOTS</b>
║ • <b>Users:</b> {total_stats['total_users']}
║ • <b>Bots:</b> {total_stats['total_bots']}
║ • <b>Running:</b> {total_stats['running_bots']}
║ • <b>Keys:</b> {total_stats['total_keys']}
╠══════════════════════════╣
║ 🖥️ <b>RESOURCE USAGE</b>
║ • <b>CPU:</b> {stats['cpu_percent']:.1f}% [{create_progress_bar(int(stats['cpu_percent']))}]
║ • <b>RAM:</b> {stats['ram_percent']:.1f}% [{create_progress_bar(int(stats['ram_percent']))}]
║ • <b>DISK:</b> {stats['disk_percent']:.1f}% [{create_progress_bar(int(stats['disk_percent']))}]
║ • <b>Uptime:</b> {uptime_str}
╠══════════════════════════╣
║ 💻 <b>HARDWARE</b>
║ • <b>CPU Cores:</b> {stats['cpu_count']}
║ • <b>Total RAM:</b> {stats['total_ram']}GB
║ • <b>Available:</b> {stats['available_ram']}GB
╚══════════════════════════╝
"""
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda message: message.text == "📢 𝗕𝗿𝗼𝗮𝗱𝗰𝗮𝘀𝘁")
def admin_broadcast(message):
    if message.from_user.id != Config.ADMIN_ID:
        return
    
    msg = bot.reply_to(message, "<b>📢 Enter broadcast message:</b>\n\n💡 Tip: Use HTML tags for formatting")
    bot.register_next_step_handler(msg, process_broadcast)

def process_broadcast(message):
    broadcast_msg = message.text
    
    conn = sqlite3.connect(Config.DB_NAME)
    c = conn.cursor()
    users = c.execute("SELECT id FROM users").fetchall()
    conn.close()
    
    status_msg = bot.send_message(message.chat.id, f"<b>📢 Broadcasting to {len(users)} users...</b>")
    
    success = 0
    failed = 0
    
    for uid in users:
        try:
            bot.send_message(uid[0], f"""
<b>📢 ANNOUNCEMENT FROM ADMIN</b>
<b>━━━━━━━━━━━━━━━━━━━━━━</b>

{broadcast_msg}

<b>━━━━━━━━━━━━━━━━━━━━━━</b>
<i>This is an official announcement.</i>
""")
            success += 1
        except:
            failed += 1
        time.sleep(0.05)  # Avoid flooding
    
    # Save to announcements
    conn = sqlite3.connect(Config.DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO announcements (message, created_by, timestamp) VALUES (?, ?, ?)",
             (broadcast_msg, Config.ADMIN_ID, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    conn.close()
    
    bot.edit_message_text(f"<b>✅ Broadcast completed!</b>\n\n📨 Sent: {success}\n❌ Failed: {failed}", 
                         message.chat.id, status_msg.message_id)

@bot.message_handler(func=lambda message: message.text == "🔄 𝗕𝗮𝗰𝗸𝘂𝗽")
def admin_backup(message):
    if message.from_user.id != Config.ADMIN_ID:
        return
    
    try:
        auto_backup()
        backup_files = sorted(Path(Config.BACKUP_DIR).glob("backup_*.db"), reverse=True)
        
        if backup_files:
            latest_backup = backup_files[0]
            with open(latest_backup, 'rb') as f:
                bot.send_document(message.chat.id, f, caption=f"<b>✅ Database Backup</b>\n<b>📅 Date:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n<b>📦 Size:</b> {latest_backup.stat().st_size / 1024:.1f}KB")
        else:
            bot.send_message(message.chat.id, "<b>❌ Backup failed!</b>")
    except Exception as e:
        bot.send_message(message.chat.id, f"<b>❌ Error: {str(e)}</b>")

# ================== API Endpoints ==================
@app.route('/api/stats', methods=['GET'])
def api_stats():
    api_key = request.headers.get('X-API-Key')
    if not api_key:
        return jsonify({'error': 'API key required'}), 401
    
    conn = sqlite3.connect(Config.DB_NAME)
    c = conn.cursor()
    user = c.execute("SELECT id, api_key FROM users WHERE api_key=?", (api_key,)).fetchone()
    conn.close()
    
    if not user:
        return jsonify({'error': 'Invalid API key'}), 401
    
    stats = get_system_stats()
    return jsonify(stats)

@app.route('/api/bots/<int:user_id>', methods=['GET'])
def api_get_bots(user_id):
    api_key = request.headers.get('X-API-Key')
    if not api_key:
        return jsonify({'error': 'API key required'}), 401
    
    conn = sqlite3.connect(Config.DB_NAME)
    c = conn.cursor()
    user = c.execute("SELECT api_key FROM users WHERE id=? AND api_key=?", (user_id, api_key)).fetchone()
    
    if not user:
        conn.close()
        return jsonify({'error': 'Invalid API key'}), 401
    
    bots = c.execute("SELECT id, bot_name, status, start_time FROM deployments WHERE user_id=?", (user_id,)).fetchall()
    conn.close()
    
    return jsonify([{'id': b[0], 'name': b[1], 'status': b[2], 'started': b[3]} for b in bots])

@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "brand": Config.BRAND_NAME,
        "version": "3.0.1",
        "features": ["Bot Hosting", "Auto Restart", "Analytics", "API Access"]
    })

# ================== Main Execution ==================
def start_bot():
    print(f"🤖 {Config.BRAND_NAME} is starting...")
    print(f"👑 Admin ID: {Config.ADMIN_ID}")
    print(f"📊 System monitoring active")
    
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"Bot polling error: {e}")
            time.sleep(5)

if __name__ == '__main__':
    # Start background threads
    threading.Thread(target=start_bot, daemon=True).start()
    threading.Thread(target=monitor_bots, daemon=True).start()
    threading.Thread(target=schedule_auto_backup, daemon=True).start()
    
    # Start Flask server
    app.run(host='0.0.0.0', port=Config.PORT, debug=False)