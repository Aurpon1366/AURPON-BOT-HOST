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
from pathlib import Path
from telebot import types
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from flask import Flask, send_file, jsonify, request
from flask_cors import CORS

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
    AUTO_BACKUP_INTERVAL = 24

# Initialize
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
                 auto_restart INTEGER DEFAULT 1, env_vars TEXT)''')
    
    # Bot logs table
    c.execute('''CREATE TABLE IF NOT EXISTS bot_logs 
                (id INTEGER PRIMARY KEY AUTOINCREMENT, bot_id INTEGER, log_type TEXT, 
                 message TEXT, timestamp TEXT)''')
    
    # Announcements table
    c.execute('''CREATE TABLE IF NOT EXISTS announcements 
                (id INTEGER PRIMARY KEY AUTOINCREMENT, message TEXT, 
                 created_by INTEGER, timestamp TEXT)''')
    
    join_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    expiry_date = (datetime.now() + timedelta(days=3650)).strftime('%Y-%m-%d %H:%M:%S')
    
    c.execute("INSERT OR IGNORE INTO users (id, username, expiry, file_limit, is_prime, join_date, last_renewal, api_key, total_bots, total_uptime) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
             (Config.ADMIN_ID, 'admin', expiry_date, 999, 1, join_date, join_date, f"admin_key_{uuid.uuid4().hex[:8]}", 0, 0))
    
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
    backups = sorted(Path(Config.BACKUP_DIR).glob("backup_*.db"))
    for old_backup in backups[:-10]:
        old_backup.unlink()

def schedule_auto_backup():
    while True:
        time.sleep(Config.AUTO_BACKUP_INTERVAL * 3600)
        auto_backup()

def monitor_bots():
    while True:
        try:
            conn = sqlite3.connect(Config.DB_NAME)
            c = conn.cursor()
            running_bots = c.execute("SELECT id, pid, bot_name, user_id, auto_restart, filename FROM deployments WHERE status='Running'").fetchall()
            
            for bot_id, pid, bot_name, user_id, auto_restart, filename in running_bots:
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
                        file_path = project_path / filename
                        if file_path.exists():
                            proc = subprocess.Popen(['python', str(file_path)], start_new_session=True)
                            c.execute("UPDATE deployments SET pid=?, status='Running', start_time=? WHERE id=?",
                                     (proc.pid, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), bot_id))
                            log_bot_activity(bot_id, "RESTART", "Bot auto-restarted by monitor")
                    else:
                        c.execute("UPDATE deployments SET status='Crashed', pid=0 WHERE id=?", (bot_id,))
                        log_bot_activity(bot_id, "CRASH", "Bot crashed and auto-restart is disabled")
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Monitor error: {e}")
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

# ================== Admin Security ==================
@bot.message_handler(func=lambda message: message.from_user.id != Config.ADMIN_ID and message.text not in ['/start'])
def ignore_others(message):
    if message.text == '/start':
        welcome(message)
    else:
        return

# ================== Command Handlers ==================
@bot.message_handler(commands=['start'])
def welcome(message):
    uid = message.from_user.id
    username = message.from_user.username or "User"
    user = get_user(uid)
    
    if not user:
        join_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        expiry_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
        conn = sqlite3.connect(Config.DB_NAME)
        c = conn.cursor()
        c.execute("INSERT INTO users (id, username, expiry, file_limit, is_prime, join_date, last_renewal, api_key) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                 (uid, username, expiry_date, 5, 0, join_date, join_date, f"user_{uuid.uuid4().hex[:8]}"))
        conn.commit()
        conn.close()
        user = get_user(uid)
    
    prime_status = "👑 𝗣𝗥𝗜𝗠𝗘 𝗔𝗗𝗠𝗜𝗡" if uid == Config.ADMIN_ID else ("💎 𝗣𝗥𝗜𝗠𝗘" if is_prime(uid) else "👤 𝗙𝗥𝗘𝗘")
    
    text = f"""
✨ <b>{Config.BRAND_NAME}</b> ✨
<b>━━━━━━━━━━━━━━━━━━━━━━</b>
👤 <b>𝗨𝘀𝗲𝗿:</b> @{username}
🆔 <b>𝗜𝗗:</b> <code>{uid}</code>
💎 <b>𝗦𝘁𝗮𝘁𝘂𝘀:</b> {prime_status}
📅 <b>𝗝𝗼𝗶𝗻𝗲𝗱:</b> {user[5][:10]}
<b>━━━━━━━━━━━━━━━━━━━━━━</b>
📊 <b>𝗔𝗰𝗰𝗼𝘂𝗻𝘁 𝗜𝗻𝗳𝗼</b>
• <b>𝗣𝗹𝗮𝗻:</b> {'Premium' if is_prime(uid) else 'Free'}
• <b>𝗙𝗶𝗹𝗲 𝗟𝗶𝗺𝗶𝘁:</b> <code>{user[3]}</code>
• <b>𝗘𝘅𝗽𝗶𝗿𝘆:</b> {user[2][:10] if user[2] else 'N/A'}
• <b>𝗧𝗼𝘁𝗮𝗹 𝗕𝗼𝘁𝘀:</b> <code>{user[8]}</code>
<b>━━━━━━━━━━━━━━━━━━━━━━</b>
"""
    bot.send_message(message.chat.id, text, reply_markup=main_menu_reply(uid))

@bot.message_handler(func=lambda message: message.text == "🏠 𝗠𝗮𝗶𝗻 𝗠𝗲𝗻𝘂")
def back_to_main(message):
    welcome(message)

@bot.message_handler(func=lambda message: message.text == "⚙️ 𝗦𝗲𝘁𝘁𝗶𝗻𝗴𝘀")
def settings_menu(message):
    uid = message.from_user.id
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("🔄 Auto Restart", callback_data=f"toggle_restart_{uid}")
    btn2 = types.InlineKeyboardButton("🗑️ Clear Logs", callback_data=f"clear_logs_{uid}")
    markup.add(btn1, btn2)
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

@bot.message_handler(func=lambda message: message.text == "📤 𝗨𝗽𝗹𝗼𝗮𝗱 𝗕𝗼𝘁")
def upload_handler(message):
    user = get_user(message.from_user.id)
    if user[8] >= Config.MAX_BOTS_PER_USER and not is_prime(message.from_user.id):
        bot.reply_to(message, f"<b>❌ Bot limit reached! Max {Config.MAX_BOTS_PER_USER} bots for free users.</b>")
        return
    
    msg = bot.reply_to(message, "<b>📤 Send your .py or .zip file (Max 5.5MB):</b>")
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
            
            status_msg = bot.send_message(chat_id, "<b>📥 Downloading file...</b>")
            
            file_info = bot.get_file(message.document.file_id)
            downloaded = bot.download_file(file_info.file_path)
            
            safe_name = secure_filename(message.document.file_name)
            file_path = project_path / safe_name
            file_path.write_bytes(downloaded)
            
            # Extract ZIP if needed
            if file_name.endswith('.zip'):
                bot.edit_message_text("<b>📦 Extracting ZIP...</b>", chat_id, status_msg.message_id)
                extract_dir = project_path / safe_name.replace('.zip', '')
                extract_dir.mkdir(exist_ok=True)
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
                
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
    markup.add(btn1, btn2)
    
    bot.send_message(message.chat.id, f"<b>✅ Bot '{bot_name}' uploaded!</b>\n\nClick below to install libraries and deploy:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('install_libs_'))
def install_libraries_callback(call):
    bot_id = int(call.data.split('_')[2])
    msg = bot.send_message(call.message.chat.id, "<b>📚 Enter pip commands (one per line):</b>\nExample:\n<code>pip install requests</code>\n<code>pip install telebot</code>")
    bot.register_next_step_handler(msg, install_libraries_step, bot_id)

def install_libraries_step(message, bot_id):
    commands = [cmd.strip() for cmd in message.text.strip().split('\n') if cmd.strip() and 'pip install' in cmd]
    
    if not commands:
        bot.send_message(message.chat.id, "<b>❌ No valid pip commands found!</b>")
        return
    
    results = []
    for cmd in commands:
        result = subprocess.run(cmd.split(), capture_output=True, text=True)
        if result.returncode == 0:
            results.append(f"✅ <code>{cmd}</code>")
            log_bot_activity(bot_id, "LIB_INSTALL", f"Success: {cmd}")
        else:
            results.append(f"❌ <code>{cmd}</code>")
    
    bot.send_message(message.chat.id, "<b>📊 Installation Results:</b>\n" + "\n".join(results[:10]))

@bot.message_handler(func=lambda message: message.text == "🤖 𝗠𝘆 𝗕𝗼𝘁𝘀")
def show_my_bots(message):
    uid = message.from_user.id
    bots = get_user_bots(uid)
    
    if not bots:
        bot.reply_to(message, "<b>🤖 No bots found!</b>")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    for bot_id, bot_name, filename, pid, start_time, status, port in bots:
        status_icon = "🟢" if status == "Running" else ("🟡" if status == "Stopped" else "🔴")
        btn = types.InlineKeyboardButton(f"{status_icon} {bot_name[:20]}", callback_data=f"bot_{bot_id}")
        markup.add(btn)
    
    bot.send_message(message.chat.id, f"<b>🤖 YOUR BOTS ({len(bots)})</b>", reply_markup=markup)

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
    
    text = f"""
<b>🤖 BOT: {bot_info[2]}</b>
<b>━━━━━━━━━━━━━━━━━━━━━━</b>
📊 <b>Status:</b> {status_icon} {bot_info[6]}
🆔 <b>PID:</b> <code>{bot_info[4] or 'N/A'}</code>
🚀 <b>Started:</b> {bot_info[5] or 'Not started'}
💾 <b>CPU:</b> {bot_info[7] or 0}% | <b>RAM:</b> {bot_info[8] or 0}%
🔄 <b>Auto-Restart:</b> {'✅ ON' if bot_info[11] else '❌ OFF'}
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
        bot.answer_callback_query(call.id, "✅ Bot started!")
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
        if bot_info[2] and bot_info[2] > 0:
            try:
                os.kill(bot_info[2], signal.SIGTERM)
            except:
                pass
        
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
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton("✅ Yes", callback_data=f"confirm_delete_{bot_id}")
    btn2 = types.InlineKeyboardButton("❌ No", callback_data=f"cancel_delete_{bot_id}")
    markup.add(btn1, btn2)
    bot.edit_message_text("<b>⚠️ Delete this bot? This cannot be undone!</b>", 
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
        bot.edit_message_text("<b>✅ Bot deleted successfully!</b>", call.message.chat.id, call.message.message_id)
        
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ Failed")
    
    conn.close()

@bot.callback_query_handler(func=lambda call: call.data.startswith('cancel_delete_'))
def cancel_delete_bot(call):
    bot.answer_callback_query(call.id, "❌ Cancelled")
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
    
    bot.send_message(call.message.chat.id, log_text[:4000])

@bot.callback_query_handler(func=lambda call: call.data.startswith('stats_'))
def show_bot_stats(call):
    bot_id = int(call.data.split('_')[1])
    
    conn = sqlite3.connect(Config.DB_NAME)
    c = conn.cursor()
    bot_info = c.execute("SELECT cpu_usage, ram_usage, start_time, last_active, status FROM deployments WHERE id=?", (bot_id,)).fetchone()
    conn.close()
    
    text = f"""
<b>📊 BOT STATISTICS</b>
<b>━━━━━━━━━━━━━━━━━━━━━━</b>
💾 <b>CPU Usage:</b> {create_progress_bar(int(bot_info[0] or 0))} {bot_info[0] or 0}%
📀 <b>RAM Usage:</b> {create_progress_bar(int(bot_info[1] or 0))} {bot_info[1] or 0}%
🚀 <b>Started:</b> {bot_info[2] or 'N/A'}
🕐 <b>Last Active:</b> {bot_info[3] or 'N/A'}
📊 <b>Status:</b> {'🟢 Online' if bot_info[4] == 'Running' else '🔴 Offline'}
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
                'export_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            zipf.writestr('metadata.json', json.dumps(metadata, indent=4))
        
        with open(zip_path, 'rb') as f:
            bot.send_document(call.message.chat.id, f, caption=f"<b>📦 Exported: {bot_info[1]}</b>")
        
        zip_path.unlink()
        
    except Exception as e:
        bot.send_message(call.message.chat.id, f"<b>❌ Export failed</b>")

@bot.message_handler(func=lambda message: message.text == "🚀 𝗗𝗲𝗽𝗹𝗼𝘆 𝗕𝗼𝘁")
def deploy_bot_handler(message):
    uid = message.from_user.id
    bots = get_user_bots(uid, "Uploaded")
    
    if not bots:
        bot.reply_to(message, "<b>📭 No uploaded bots found!</b>")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for bot_id, bot_name, filename, pid, start_time, status, port in bots:
        btn = types.InlineKeyboardButton(f"📤 {bot_name}", callback_data=f"deploy_{bot_id}")
        markup.add(btn)
    
    bot.send_message(message.chat.id, f"<b>🚀 Select bot to deploy ({len(bots)} available):</b>", reply_markup=markup)

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
        
        bot.edit_message_text(f"<b>✅ {bot_info[1]} DEPLOYED!</b>\n\n🆔 PID: <code>{proc.pid}</code>\n🚀 Status: 🟢 Running", 
                             call.message.chat.id, status_msg.message_id)
        
    except Exception as e:
        bot.edit_message_text(f"<b>❌ Deployment failed: {str(e)[:100]}</b>", 
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
<b>📊 ADMIN DASHBOARD</b>
<b>━━━━━━━━━━━━━━━━━━━━━━</b>
👥 <b>Total Users:</b> {total_stats['total_users']}
🤖 <b>Total Bots:</b> {total_stats['total_bots']}
🟢 <b>Running:</b> {total_stats['running_bots']}
🔑 <b>Keys:</b> {total_stats['total_keys']}
<b>━━━━━━━━━━━━━━━━━━━━━━</b>
🖥️ <b>SERVER STATUS</b>
• <b>CPU:</b> {create_progress_bar(int(stats['cpu_percent']))} {stats['cpu_percent']:.1f}%
• <b>RAM:</b> {create_progress_bar(int(stats['ram_percent']))} {stats['ram_percent']:.1f}%
• <b>DISK:</b> {create_progress_bar(int(stats['disk_percent']))} {stats['disk_percent']:.1f}%
"""
    else:
        text = f"""
<b>📊 USER DASHBOARD</b>
<b>━━━━━━━━━━━━━━━━━━━━━━</b>
💎 <b>Plan:</b> {'Premium' if is_prime(uid) else 'Free'}
📦 <b>File Limit:</b> {user[3]}
🤖 <b>Your Bots:</b> {user[8]}
📅 <b>Expires:</b> {user[2][:10] if user[2] else 'N/A'}
<b>━━━━━━━━━━━━━━━━━━━━━━</b>
🖥️ <b>SERVER STATUS</b>
• <b>CPU:</b> {create_progress_bar(int(stats['cpu_percent']))} {stats['cpu_percent']:.1f}%
• <b>RAM:</b> {create_progress_bar(int(stats['ram_percent']))} {stats['ram_percent']:.1f}%
"""
    
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda message: message.text == "📢 𝗔𝗻𝗻𝗼𝘂𝗻𝗰𝗲𝗺𝗲𝗻𝘁𝘀")
def show_announcements(message):
    conn = sqlite3.connect(Config.DB_NAME)
    c = conn.cursor()
    announcements = c.execute("SELECT message, timestamp FROM announcements ORDER BY id DESC LIMIT 10").fetchall()
    conn.close()
    
    if not announcements:
        bot.send_message(message.chat.id, "<b>📢 No announcements yet!</b>")
        return
    
    text = "<b>📢 LATEST ANNOUNCEMENTS</b>\n<b>━━━━━━━━━━━━━━━━━━━━━━</b>\n\n"
    for msg, timestamp in announcements:
        text += f"<b>📅 {timestamp[:16]}</b>\n{msg}\n<b>━━━━━━━━━━━━━━━━━━━━━━</b>\n\n"
    
    bot.send_message(message.chat.id, text[:4000])

# ================== Admin Handlers ==================
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id != Config.ADMIN_ID:
        return
    bot.send_message(message.chat.id, "<b>👑 ADMIN PANEL</b>\nSelect an option:", reply_markup=admin_panel_reply())

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
        text += f"<b>ID:</b> <code>{uid}</code> | {status}\n<b>👤 @{username}</b> | 🤖 {bots} bots\n<b>📅 Exp:</b> {expiry[:10] if expiry else 'N/A'}\n<b>━━━━━━━━━━━━━━━━━━━━━━</b>\n\n"
    
    bot.send_message(message.chat.id, text[:4000])

@bot.message_handler(func=lambda message: message.text == "🔑 𝗚𝗲𝗻𝗲𝗿𝗮𝘁𝗲 𝗞𝗲𝘆")
def admin_generate_key(message):
    if message.from_user.id != Config.ADMIN_ID:
        return
    
    msg = bot.reply_to(message, "<b>🔑 Enter duration (days) and file limit:</b>\nExample: <code>30 50</code>")
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
        
        bot.send_message(message.chat.id, f"<b>✅ KEY GENERATED!</b>\n\n🔑 <code>{key}</code>\n📅 {days} days\n📦 {file_limit} bots")
    except:
        bot.send_message(message.chat.id, "<b>❌ Invalid format! Use: days file_limit</b>")

@bot.message_handler(func=lambda message: message.text == "📊 𝗦𝘁𝗮𝘁𝘀")
def admin_stats(message):
    if message.from_user.id != Config.ADMIN_ID:
        return
    
    stats = get_system_stats()
    total_stats = get_total_stats()
    
    try:
        uptime_seconds = time.time() - psutil.boot_time()
        days = int(uptime_seconds // 86400)
        hours = int((uptime_seconds % 86400) // 3600)
        uptime_str = f"{days}d {hours}h"
    except:
        uptime_str = "N/A"
    
    text = f"""
<b>📊 SYSTEM STATS</b>
<b>━━━━━━━━━━━━━━━━━━━━━━</b>
👥 <b>Users:</b> {total_stats['total_users']}
🤖 <b>Bots:</b> {total_stats['total_bots']}
🟢 <b>Running:</b> {total_stats['running_bots']}
<b>━━━━━━━━━━━━━━━━━━━━━━</b>
🖥️ <b>CPU:</b> {stats['cpu_percent']:.1f}% [{create_progress_bar(int(stats['cpu_percent']))}]
📀 <b>RAM:</b> {stats['ram_percent']:.1f}% [{create_progress_bar(int(stats['ram_percent']))}]
💾 <b>DISK:</b> {stats['disk_percent']:.1f}%
⏰ <b>Uptime:</b> {uptime_str}
"""
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda message: message.text == "📢 𝗕𝗿𝗼𝗮𝗱𝗰𝗮𝘀𝘁")
def admin_broadcast(message):
    if message.from_user.id != Config.ADMIN_ID:
        return
    
    msg = bot.reply_to(message, "<b>📢 Enter broadcast message:</b>")
    bot.register_next_step_handler(msg, process_broadcast)

def process_broadcast(message):
    broadcast_msg = message.text
    
    conn = sqlite3.connect(Config.DB_NAME)
    c = conn.cursor()
    users = c.execute("SELECT id FROM users").fetchall()
    conn.close()
    
    status_msg = bot.send_message(message.chat.id, f"<b>📢 Broadcasting to {len(users)} users...</b>")
    
    success = 0
    for uid in users:
        try:
            bot.send_message(uid[0], f"<b>📢 ANNOUNCEMENT</b>\n<b>━━━━━━━━━━━━━━━━━━━━━━</b>\n\n{broadcast_msg}")
            success += 1
        except:
            pass
        time.sleep(0.05)
    
    conn = sqlite3.connect(Config.DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO announcements (message, created_by, timestamp) VALUES (?, ?, ?)",
             (broadcast_msg, Config.ADMIN_ID, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    conn.close()
    
    bot.edit_message_text(f"<b>✅ Broadcast sent to {success} users!</b>", message.chat.id, status_msg.message_id)

@bot.message_handler(func=lambda message: message.text == "🔄 𝗕𝗮𝗰𝗸𝘂𝗽")
def admin_backup(message):
    if message.from_user.id != Config.ADMIN_ID:
        return
    
    try:
        auto_backup()
        backup_files = sorted(Path(Config.BACKUP_DIR).glob("backup_*.db"), reverse=True)
        
        if backup_files:
            with open(backup_files[0], 'rb') as f:
                bot.send_document(message.chat.id, f, caption=f"<b>✅ Database Backup</b>\n📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    except Exception as e:
        bot.send_message(message.chat.id, f"<b>❌ Backup failed</b>")

# ================== Flask Routes ==================
@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "brand": Config.BRAND_NAME,
        "version": "3.0.1"
    })

@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

# ================== Main Execution ==================
def start_polling():
    """Start bot polling with error recovery"""
    while True:
        try:
            bot.remove_webhook()
            time.sleep(1)
            print("🤖 Bot polling started...")
            bot.polling(none_stop=True, interval=1, timeout=30, long_polling_timeout=30)
        except Exception as e:
            print(f"Polling error: {e}")
            time.sleep(10)

if __name__ == '__main__':
    print(f"🚀 Starting {Config.BRAND_NAME}...")
    print(f"👑 Admin ID: {Config.ADMIN_ID}")
    print(f"📊 System monitoring active")
    
    # Remove webhook first
    try:
        bot.remove_webhook()
        print("✅ Webhook removed")
    except:
        pass
    
    # Clear pending updates
    try:
        bot.get_updates(offset=-1, timeout=5)
        print("✅ Updates cleared")
    except:
        pass
    
    # Start monitoring threads
    threading.Thread(target=monitor_bots, daemon=True).start()
    threading.Thread(target=schedule_auto_backup, daemon=True).start()
    
    # Start bot in background
    threading.Thread(target=start_polling, daemon=True).start()
    
    # Run Flask
    app.run(host='0.0.0.0', port=Config.PORT, debug=False, threaded=True)
