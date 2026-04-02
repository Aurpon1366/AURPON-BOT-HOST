import os
import telebot
import sqlite3
import threading
import time
import uuid
import subprocess
import signal
import psutil
import json
import shutil
import hashlib
import logging
from datetime import datetime, timedelta
from flask import Flask, jsonify
from telebot import types
from pathlib import Path
import random
import string

# ==================== LOGGING SETUP ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== CONFIGURATION ====================
class Config:
    TOKEN = os.environ.get('BOT_TOKEN', '8754448627:AAFReyCErlSnESaSJOUzAt1Ut-n95w_xWDI')
    ADMIN_ID = int(os.environ.get('ADMIN_ID', 6487613131))
    PORT = int(os.environ.get('PORT', 10000))
    PROJECT_DIR = 'projects'
    DB_NAME = 'aurpon_bot.db'
    
    BRAND_NAME = "𝐀𝐔𝐑𝐏𝐎𝐍 𝐃𝐄𝐗"
    VERSION = "5.0.0"
    SUPPORT_ID = "@aurponmodz"
    BOT_USERNAME = "@aurpon_bot_host_bot"
    MAX_FILE_SIZE = 50 * 1024 * 1024
    
    Path(PROJECT_DIR).mkdir(exist_ok=True)

# ==================== DATABASE ====================
class DatabaseManager:
    def __init__(self):
        self.conn = sqlite3.connect(Config.DB_NAME, check_same_thread=False)
        self.init_db()
    
    def init_db(self):
        cursor = self.conn.cursor()
        
        # Users table
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            join_date TEXT,
            expiry_date TEXT,
            credits INTEGER DEFAULT 100,
            bots_limit INTEGER DEFAULT 5,
            is_admin INTEGER DEFAULT 0,
            is_banned INTEGER DEFAULT 0,
            referral_code TEXT
        )''')
        
        # Bots table
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
        
        # Templates table
        cursor.execute('''CREATE TABLE IF NOT EXISTS templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            description TEXT,
            code TEXT,
            downloads INTEGER DEFAULT 0
        )''')
        
        # System logs table
        cursor.execute('''CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT,
            admin_id INTEGER,
            user_id INTEGER,
            details TEXT,
            created_at TEXT
        )''')
        
        # Add admin user
        referral_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        expiry = (datetime.now() + timedelta(days=3650)).strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute("INSERT OR IGNORE INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                      (Config.ADMIN_ID, 'admin', datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                       expiry, 999999, 999, 1, 0, referral_code))
        
        # Add default templates
        self.add_default_templates(cursor)
        
        self.conn.commit()
    
    def add_default_templates(self, cursor):
        templates = [
            ("Echo Bot", "Simple echo bot that replies with same message", 
             "import telebot\nTOKEN = 'YOUR_BOT_TOKEN'\nbot = telebot.TeleBot(TOKEN)\n\n@bot.message_handler(func=lambda m: True)\ndef echo(message):\n    bot.reply_to(message, message.text)\n\nbot.infinity_polling()"),
            
            ("Weather Bot", "Get weather information for any city",
             "import telebot\nimport requests\n\nTOKEN = 'YOUR_BOT_TOKEN'\nbot = telebot.TeleBot(TOKEN)\n\n@bot.message_handler(commands=['weather'])\ndef weather(message):\n    city = message.text.replace('/weather', '').strip()\n    if city:\n        api_key = 'YOUR_API_KEY'\n        url = f'http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric'\n        data = requests.get(url).json()\n        temp = data['main']['temp']\n        bot.reply_to(message, f'Weather in {city}: {temp}°C')\n\nbot.infinity_polling()"),
        ]
        
        for t in templates:
            cursor.execute("INSERT OR IGNORE INTO templates (name, description, code) VALUES (?, ?, ?)", t)
    
    def get_user(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id=?", (user_id,))
        return cursor.fetchone()
    
    def get_all_users(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, username, join_date, credits, is_banned FROM users ORDER BY id DESC")
        return cursor.fetchall()
    
    def get_user_bots(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM bots WHERE user_id=? ORDER BY id DESC", (user_id,))
        return cursor.fetchall()
    
    def get_all_bots(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT b.*, u.username FROM bots b LEFT JOIN users u ON b.user_id = u.id ORDER BY b.id DESC")
        return cursor.fetchall()
    
    def get_stats(self):
        cursor = self.conn.cursor()
        total_users = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        total_bots = cursor.execute("SELECT COUNT(*) FROM bots").fetchone()[0]
        running_bots = cursor.execute("SELECT COUNT(*) FROM bots WHERE status='Running'").fetchone()[0]
        total_deploys = cursor.execute("SELECT SUM(deploy_count) FROM bots").fetchone()[0] or 0
        
        return {
            'total_users': total_users,
            'total_bots': total_bots,
            'running_bots': running_bots,
            'total_deploys': total_deploys
        }
    
    def ban_user(self, user_id, reason):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE users SET is_banned=1 WHERE id=?", (user_id,))
        self.conn.commit()
        self.add_log(Config.ADMIN_ID, 'ban_user', user_id, f"Banned: {reason}")
    
    def unban_user(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE users SET is_banned=0 WHERE id=?", (user_id,))
        self.conn.commit()
        self.add_log(Config.ADMIN_ID, 'unban_user', user_id, "Unbanned")
    
    def add_credits(self, user_id, amount):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE users SET credits=credits+? WHERE id=?", (amount, user_id))
        self.conn.commit()
        self.add_log(Config.ADMIN_ID, 'add_credits', user_id, f"Added {amount} credits")
    
    def remove_credits(self, user_id, amount):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE users SET credits=credits-? WHERE id=?", (amount, user_id))
        self.conn.commit()
        self.add_log(Config.ADMIN_ID, 'remove_credits', user_id, f"Removed {amount} credits")
    
    def extend_expiry(self, user_id, days):
        cursor = self.conn.cursor()
        user = self.get_user(user_id)
        if user and user[3]:
            current_expiry = datetime.strptime(user[3], '%Y-%m-%d %H:%M:%S')
            new_expiry = current_expiry + timedelta(days=days)
        else:
            new_expiry = datetime.now() + timedelta(days=days)
        
        cursor.execute("UPDATE users SET expiry_date=? WHERE id=?", (new_expiry.strftime('%Y-%m-%d %H:%M:%S'), user_id))
        self.conn.commit()
        self.add_log(Config.ADMIN_ID, 'extend_expiry', user_id, f"Extended by {days} days")
    
    def add_log(self, admin_id, action, user_id, details):
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO logs (action, admin_id, user_id, details, created_at) VALUES (?, ?, ?, ?, ?)",
                      (action, admin_id, user_id, details, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        self.conn.commit()
    
    def get_logs(self, limit=20):
        cursor = self.conn.cursor()
        cursor.execute("SELECT action, admin_id, user_id, details, created_at FROM logs ORDER BY id DESC LIMIT ?", (limit,))
        return cursor.fetchall()

db = DatabaseManager()

# ==================== BOT INITIALIZATION ====================
bot = telebot.TeleBot(Config.TOKEN, parse_mode="HTML")
app = Flask(__name__)

# ==================== HELPER FUNCTIONS ====================
def is_admin(user_id):
    user = db.get_user(user_id)
    return user and user[6] == 1

def get_system_stats():
    try:
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/').percent
        uptime = time.time() - psutil.boot_time()
        return {'cpu': cpu, 'ram': ram, 'disk': disk, 'uptime': uptime}
    except:
        return {'cpu': 25, 'ram': 40, 'disk': 50, 'uptime': 86400}

def format_uptime(seconds):
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    
    if days > 0:
        return f"{days}d {hours}h"
    elif hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"

def progress_bar(percent, length=20):
    filled = int(length * percent / 100)
    return "█" * filled + "░" * (length - filled)

# ==================== KEYBOARDS ====================
def user_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    buttons = [
        "📤 Upload Bot", "🤖 My Bots",
        "⚡ Deploy Bot", "🎨 Templates",
        "💰 Buy Credits", "📊 Dashboard",
        "❓ Help", "ℹ️ About"
    ]
    markup.add(*[types.KeyboardButton(btn) for btn in buttons])
    return markup

def admin_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    buttons = [
        "👑 Admin Panel", "📊 Full Stats",
        "👥 All Users", "🤖 All Bots",
        "📢 Broadcast", "💾 Backup",
        "📜 System Logs", "🔙 User Menu"
    ]
    markup.add(*[types.KeyboardButton(btn) for btn in buttons])
    return markup

def admin_panel():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("👥 Users", callback_data="admin_users"),
        types.InlineKeyboardButton("🤖 Bots", callback_data="admin_bots"),
        types.InlineKeyboardButton("📊 Stats", callback_data="admin_stats"),
        types.InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast"),
        types.InlineKeyboardButton("💾 Backup", callback_data="admin_backup"),
        types.InlineKeyboardButton("📜 Logs", callback_data="admin_logs"),
        types.InlineKeyboardButton("🎨 Templates", callback_data="admin_templates"),
        types.InlineKeyboardButton("⚙️ Settings", callback_data="admin_settings")
    )
    return markup

def user_controls(user_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("💰 Add Credits", callback_data=f"add_credits_{user_id}"),
        types.InlineKeyboardButton("💎 Remove Credits", callback_data=f"remove_credits_{user_id}"),
        types.InlineKeyboardButton("📅 Extend Expiry", callback_data=f"extend_expiry_{user_id}"),
        types.InlineKeyboardButton("🔨 Ban", callback_data=f"ban_{user_id}"),
        types.InlineKeyboardButton("🔓 Unban", callback_data=f"unban_{user_id}"),
        types.InlineKeyboardButton("📊 Stats", callback_data=f"user_stats_{user_id}"),
        types.InlineKeyboardButton("🔙 Back", callback_data="back_to_users")
    )
    return markup

def bot_controls(bot_id, status):
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    if status == "Running":
        markup.add(
            types.InlineKeyboardButton("⏸ Stop", callback_data=f"stop_{bot_id}"),
            types.InlineKeyboardButton("🔄 Restart", callback_data=f"restart_{bot_id}")
        )
    else:
        markup.add(
            types.InlineKeyboardButton("▶️ Start", callback_data=f"start_{bot_id}"),
            types.InlineKeyboardButton("📊 Stats", callback_data=f"stats_{bot_id}")
        )
    
    markup.add(
        types.InlineKeyboardButton("📦 Export", callback_data=f"export_{bot_id}"),
        types.InlineKeyboardButton("🗑 Delete", callback_data=f"delete_{bot_id}")
    )
    
    return markup

# ==================== START HANDLER ====================
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    username = message.from_user.username or "User"
    
    user = db.get_user(user_id)
    if not user:
        referral_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        expiry = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
        
        cursor = db.conn.cursor()
        cursor.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                      (user_id, username, datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                       expiry, 100, 5, 0, 0, referral_code))
        db.conn.commit()
        user = db.get_user(user_id)
    
    stats = get_system_stats()
    
    # Check if user is admin
    if is_admin(user_id):
        text = f"""
╔══════════════════════════════════╗
║     👑 ADMIN CONTROL PANEL      ║
╠══════════════════════════════════╣
║ 👤 <b>ADMIN:</b> @{username}              
║ 🆔 <b>ID:</b> <code>{user_id}</code>                 
║ 💎 <b>Status:</b> SUPER ADMIN            
╠══════════════════════════════════╣
║ 📊 <b>STATS</b>                       
║ ├ Users: {db.get_stats()['total_users']}                  
║ ├ Bots: {db.get_stats()['total_bots']}                  
║ └ Running: {db.get_stats()['running_bots']}               
╠══════════════════════════════════╣
║ 🖥️ <b>SYSTEM</b>                      
║ ├ CPU: {progress_bar(stats['cpu'])} {stats['cpu']:.0f}%   
║ ├ RAM: {progress_bar(stats['ram'])} {stats['ram']:.0f}%   
║ ├ Disk: {progress_bar(stats['disk'])} {stats['disk']:.0f}%   
║ └ Uptime: {format_uptime(stats['uptime'])}         
╚══════════════════════════════════╝

🔧 <b>ADMIN COMMANDS:</b>
• Use buttons below to manage everything
• /stats - View system stats
• /users - List all users
• /broadcast - Send message to all

Select an option from the menu below:
"""
        bot.send_message(message.chat.id, text, reply_markup=admin_menu())
    else:
        text = f"""
╔══════════════════════════════════╗
║  {Config.BRAND_NAME} v{Config.VERSION}  ║
╠══════════════════════════════════╣
║ 👤 <b>USER:</b> @{username}                 
║ 💎 <b>Status:</b> {'VIP' if user[6] else 'FREE'}              
║ 💰 <b>Credits:</b> {user[4]}                 
║ 📦 <b>Bots Limit:</b> {user[5]}                
╠══════════════════════════════════╣
║ 🖥️ <b>SYSTEM</b>                      
║ ├ CPU: {progress_bar(stats['cpu'])} {stats['cpu']:.0f}%   
║ ├ RAM: {progress_bar(stats['ram'])} {stats['ram']:.0f}%   
║ ├ Disk: {progress_bar(stats['disk'])} {stats['disk']:.0f}%   
║ └ Uptime: {format_uptime(stats['uptime'])}         
╚══════════════════════════════════╝

🎁 <b>Referral Code:</b> <code>{user[8]}</code>
Share and get 50 credits per referral!
"""
        bot.send_message(message.chat.id, text, reply_markup=user_menu())

# ==================== ADMIN COMMANDS ====================
@bot.message_handler(commands=['stats'])
def admin_stats(message):
    if not is_admin(message.from_user.id):
        return
    
    stats = db.get_stats()
    system = get_system_stats()
    
    text = f"""
╔══════════════════════════════════╗
║        📊 SYSTEM STATS          ║
╠══════════════════════════════════╣
║ 👥 <b>USERS</b>                       ║
║ ├ Total: {stats['total_users']}                  ║
║ └ Active: {stats['total_users']}                  ║
╠══════════════════════════════════╣
║ 🤖 <b>BOTS</b>                        ║
║ ├ Total: {stats['total_bots']}                  ║
║ ├ Running: {stats['running_bots']}                ║
║ └ Deploys: {stats['total_deploys']}                  ║
╠══════════════════════════════════╣
║ 🖥️ <b>SERVER</b>                      ║
║ ├ CPU: {system['cpu']:.1f}%                  ║
║ ├ RAM: {system['ram']:.1f}%                  ║
║ ├ Disk: {system['disk']:.1f}%                  ║
║ └ Uptime: {format_uptime(system['uptime'])}            ║
╚══════════════════════════════════╝
"""
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['users'])
def admin_users(message):
    if not is_admin(message.from_user.id):
        return
    
    users = db.get_all_users()
    text = f"👥 <b>USERS ({len(users)})</b>\n\n"
    
    for user in users[:20]:
        status = "🟢" if not user[4] else "🔴"
        text += f"{status} <b>{user[1]}</b> (ID: {user[0]}) | Credits: {user[3]}\n"
    
    if len(users) > 20:
        text += f"\n... and {len(users)-20} more"
    
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['broadcast'])
def admin_broadcast(message):
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
    
    bot.send_message(message.chat.id, f"✅ Broadcast sent!\n\nSent: {success}\nFailed: {failed}")

# ==================== ADMIN MENU HANDLERS ====================
@bot.message_handler(func=lambda m: m.text == "👑 Admin Panel")
def admin_panel_menu(message):
    if not is_admin(message.from_user.id):
        return
    
    text = """
╔══════════════════════════════════╗
║        👑 ADMIN PANEL           ║
╠══════════════════════════════════╣
║ Select an option to manage:     ║
║                                  ║
║ 👥 Users - Manage all users     ║
║ 🤖 Bots - Manage all bots       ║
║ 📊 Stats - View statistics      ║
║ 📢 Broadcast - Send message     ║
║ 💾 Backup - Database backup     ║
║ 📜 Logs - System logs           ║
║ 🎨 Templates - Manage templates ║
╚══════════════════════════════════╝
"""
    bot.send_message(message.chat.id, text, reply_markup=admin_panel())

@bot.message_handler(func=lambda m: m.text == "📊 Full Stats")
def full_stats(message):
    if not is_admin(message.from_user.id):
        return
    
    stats = db.get_stats()
    system = get_system_stats()
    
    text = f"""
╔══════════════════════════════════╗
║        📊 FULL STATS            ║
╠══════════════════════════════════╣
║ 👥 <b>USERS</b>                       ║
║ ├ Total: {stats['total_users']}                  ║
║ └ Active: {stats['total_users']}                  ║
╠══════════════════════════════════╣
║ 🤖 <b>BOTS</b>                        ║
║ ├ Total: {stats['total_bots']}                  ║
║ ├ Running: {stats['running_bots']}                ║
║ ├ Stopped: {stats['total_bots'] - stats['running_bots']}              ║
║ └ Deploys: {stats['total_deploys']}                  ║
╠══════════════════════════════════╣
║ 🖥️ <b>SYSTEM</b>                      ║
║ ├ CPU: {system['cpu']:.1f}% ({progress_bar(system['cpu'])})   ║
║ ├ RAM: {system['ram']:.1f}% ({progress_bar(system['ram'])})   ║
║ ├ Disk: {system['disk']:.1f}% ({progress_bar(system['disk'])})   ║
║ └ Uptime: {format_uptime(system['uptime'])}            ║
╠══════════════════════════════════╣
║ 💰 <b>FINANCE</b>                     ║
║ └ Total Revenue: $0.00              ║
╚══════════════════════════════════╝
"""
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: m.text == "👥 All Users")
def all_users(message):
    if not is_admin(message.from_user.id):
        return
    
    users = db.get_all_users()
    text = f"👥 <b>ALL USERS ({len(users)})</b>\n╔══════════════════════════════════╗\n"
    
    for user in users[:15]:
        status = "🟢" if not user[4] else "🔴"
        text += f"║ {status} <b>{user[1]}</b>\n"
        text += f"║    ID: {user[0]} | Credits: {user[3]}\n"
        text += "╠──────────────────────────────╣\n"
    
    if len(users) > 15:
        text += f"║ ... and {len(users)-15} more\n"
    
    text += "╚══════════════════════════════════╝"
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for user in users[:10]:
        markup.add(types.InlineKeyboardButton(f"📊 {user[1]}", callback_data=f"user_{user[0]}"))
    
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🤖 All Bots")
def all_bots(message):
    if not is_admin(message.from_user.id):
        return
    
    bots = db.get_all_bots()
    text = f"🤖 <b>ALL BOTS ({len(bots)})</b>\n╔══════════════════════════════════╗\n"
    
    for bot_data in bots[:10]:
        status_icon = "🟢" if bot_data[5] == "Running" else "🔴"
        text += f"║ {status_icon} <b>{bot_data[2]}</b>\n"
        text += f"║    Owner: {bot_data[12]}\n"
        text += f"║    Status: {bot_data[5]}\n"
        text += "╠──────────────────────────────╣\n"
    
    text += "╚══════════════════════════════════╝"
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for bot_data in bots[:5]:
        markup.add(types.InlineKeyboardButton(f"🤖 {bot_data[2]}", callback_data=f"admin_bot_{bot_data[0]}"))
    
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "📢 Broadcast")
def broadcast_menu(message):
    if not is_admin(message.from_user.id):
        return
    
    msg = bot.reply_to(message, "📢 Enter your broadcast message:")
    bot.register_next_step_handler(msg, process_broadcast)

@bot.message_handler(func=lambda m: m.text == "💾 Backup")
def backup_menu(message):
    if not is_admin(message.from_user.id):
        return
    
    backup_path = Path(Config.DB_NAME)
    if backup_path.exists():
        with open(backup_path, 'rb') as f:
            bot.send_document(message.chat.id, f, 
                            caption=f"💾 Database Backup\nSize: {backup_path.stat().st_size / 1024:.2f} KB")
    else:
        bot.reply_to(message, "❌ Database file not found!")

@bot.message_handler(func=lambda m: m.text == "📜 System Logs")
def system_logs(message):
    if not is_admin(message.from_user.id):
        return
    
    logs = db.get_logs(20)
    text = "<b>📜 SYSTEM LOGS</b>\n╔══════════════════════════════════╗\n"
    
    for log in logs:
        text += f"║ [{log[4][:16]}] {log[0]}\n"
        text += f"║   Admin: {log[1]} | User: {log[2] or 'N/A'}\n"
        text += "╠──────────────────────────────╣\n"
    
    text += "╚══════════════════════════════════╝"
    
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: m.text == "🔙 User Menu")
def back_to_user_menu(message):
    start_command(message)

# ==================== USER MENU HANDLERS ====================
@bot.message_handler(func=lambda m: m.text == "📤 Upload Bot")
def upload_bot(message):
    user = db.get_user(message.from_user.id)
    if user[5] <= 0:
        bot.reply_to(message, "❌ You've reached your bot limit!")
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
    
    if message.document.file_size > Config.MAX_FILE_SIZE:
        bot.reply_to(message, f"❌ File too large! Max 50MB")
        return
    
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded = bot.download_file(file_info.file_path)
        
        safe_name = f"{uuid.uuid4().hex[:8]}_{file_name}"
        file_path = Path(Config.PROJECT_DIR) / safe_name
        file_path.write_bytes(downloaded)
        
        msg = bot.reply_to(message, "✅ Uploaded!\n\nEnter bot name:")
        bot.register_next_step_handler(msg, save_bot, safe_name)
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

def save_bot(message, filename):
    user_id = message.from_user.id
    bot_name = message.text.strip()[:50]
    
    cursor = db.conn.cursor()
    cursor.execute("INSERT INTO bots (user_id, bot_name, filename, status) VALUES (?, ?, ?, ?)",
                  (user_id, bot_name, filename, "Uploaded"))
    
    # Update user bot limit
    user = db.get_user(user_id)
    cursor.execute("UPDATE users SET bots_limit=bots_limit-1 WHERE id=?", (user_id,))
    db.conn.commit()
    
    bot.send_message(message.chat.id, 
                    f"✅ Bot '{bot_name}' saved!\n\nUse '⚡ Deploy Bot' to start it.",
                    reply_markup=user_menu())

@bot.message_handler(func=lambda m: m.text == "🤖 My Bots")
def my_bots(message):
    user_id = message.from_user.id
    bots = db.get_user_bots(user_id)
    
    if not bots:
        bot.reply_to(message, "🤖 No bots found!\nUse 'Upload Bot' to create one.")
        return
    
    text = "🤖 <b>YOUR BOTS</b>\n╔══════════════════════════════════╗\n"
    
    for b in bots[:10]:
        status_icon = "🟢" if b[5] == "Running" else "🔴"
        text += f"║ {status_icon} <b>{b[2]}</b>\n"
        text += f"║    Status: {b[5]}\n"
        text += "╠──────────────────────────────╣\n"
    
    text += "╚══════════════════════════════════╝"
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b in bots:
        markup.add(types.InlineKeyboardButton(
            f"{b[2]} - {b[5]}", callback_data=f"user_bot_{b[0]}"
        ))
    
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "⚡ Deploy Bot")
def deploy_bot(message):
    user_id = message.from_user.id
    bots = db.get_user_bots(user_id)
    available = [b for b in bots if b[5] != "Running"]
    
    if not available:
        bot.reply_to(message, "📭 No bots available for deployment!")
        return
    
    text = "⚡ <b>DEPLOY BOT</b>\n╔══════════════════════════════════╗\n"
    for i, b in enumerate(available, 1):
        text += f"║ {i}. <b>{b[2]}</b>\n"
        text += "╠──────────────────────────────╣\n"
    
    text += "╚══════════════════════════════════╝\n\nEnter number to deploy:"
    
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
        
        cursor = db.conn.cursor()
        cursor.execute("UPDATE bots SET pid=?, status='Running', start_time=?, deploy_count=deploy_count+1 WHERE id=?",
                      (proc.pid, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), bot_id))
        db.conn.commit()
        
        bot.reply_to(message, f"✅ <b>{bot_name}</b> is RUNNING!\nPID: <code>{proc.pid}</code>")
        
    except:
        bot.reply_to(message, "❌ Invalid selection!")

@bot.message_handler(func=lambda m: m.text == "🎨 Templates")
def templates_menu(message):
    cursor = db.conn.cursor()
    cursor.execute("SELECT id, name, description FROM templates")
    templates = cursor.fetchall()
    
    text = "🎨 <b>TEMPLATES</b>\n╔══════════════════════════════════╗\n"
    
    for t in templates:
        text += f"║ 📦 <b>{t[1]}</b>\n"
        text += f"║    {t[2][:30]}...\n"
        text += "╠──────────────────────────────╣\n"
    
    text += "╚══════════════════════════════════╝"
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for t in templates:
        markup.add(types.InlineKeyboardButton(f"📦 {t[1]}", callback_data=f"template_{t[0]}"))
    
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "💰 Buy Credits")
def buy_credits(message):
    text = """
╔══════════════════════════════════╗
║        💰 BUY CREDITS           ║
╠══════════════════════════════════╣
║ 💎 100 CREDITS  →  $4.99        ║
║ 💎 500 CREDITS  →  $19.99       ║
║ 💎 1000 CREDITS →  $34.99       ║
║ 👑 UNLIMITED   →  $99.99        ║
╠══════════════════════════════════╣
║ ✨ FEATURES:                     ║
║ ✓ Deploy unlimited bots         ║
║ ✓ Priority support              ║
║ ✓ Advanced templates            ║
║ ✓ 24/7 uptime                  ║
╚══════════════════════════════════╝

Contact @aurponmodz to purchase!
"""
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: m.text == "📊 Dashboard")
def dashboard(message):
    user = db.get_user(message.from_user.id)
    bots = db.get_user_bots(message.from_user.id)
    stats = get_system_stats()
    
    running = len([b for b in bots if b[5] == "Running"])
    
    text = f"""
╔══════════════════════════════════╗
║        📊 DASHBOARD             ║
╠══════════════════════════════════╣
║ 👤 <b>ACCOUNT</b>                    ║
║ ├ Status: {'VIP' if user[6] else 'FREE'}                
║ ├ Credits: {user[4]}                 
║ ├ Bots: {len(bots)}/{user[5]}              
║ └ Running: {running}                  
╠══════════════════════════════════╣
║ 🖥️ <b>SERVER</b>                     ║
║ ├ CPU: {stats['cpu']:.1f}%                 
║ ├ RAM: {stats['ram']:.1f}%                 
║ ├ Disk: {stats['disk']:.1f}%                
║ └ Uptime: {format_uptime(stats['uptime'])}    
╠══════════════════════════════════╣
║ 🎁 <b>REFERRAL</b>                   ║
║ └ Code: <code>{user[8]}</code>           
╚══════════════════════════════════╝
"""
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: m.text == "❓ Help")
def help_command(message):
    text = """
╔══════════════════════════════════╗
║         ❓ HELP                  ║
╠══════════════════════════════════╣
║ 📤 UPLOAD BOT                     ║
║   Upload your Python bot file    ║
║                                  ║
║ 🤖 MY BOTS                        ║
║   View and manage your bots      ║
║                                  ║
║ ⚡ DEPLOY BOT                      ║
║   Start your uploaded bot        ║
║                                  ║
║ 🎨 TEMPLATES                      ║
║   Use ready-made templates       ║
║                                  ║
║ 💰 BUY CREDITS                    ║
║   Purchase more credits          ║
║                                  ║
║ 📊 DASHBOARD                      ║
║   View your statistics           ║
╚══════════════════════════════════╝

💬 Support: {Config.SUPPORT_ID}
"""
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: m.text == "ℹ️ About")
def about_command(message):
    text = f"""
╔══════════════════════════════════╗
║        ℹ️ ABOUT                 ║
╠══════════════════════════════════╣
║ {Config.BRAND_NAME}                 ║
║ Version: {Config.VERSION}                ║
╠══════════════════════════════════╣
║ ✨ FEATURES:                      ║
║ ✓ Easy bot deployment            ║
║ ✓ Template library               ║
║ ✓ Real-time monitoring           ║
║ ✓ Referral system                ║
║ ✓ Credit system                  ║
╠══════════════════════════════════╣
║ 👨‍💻 Developer: aurponmodz          ║
║ 💬 Support: {Config.SUPPORT_ID}       ║
╚══════════════════════════════════╝
"""
    bot.send_message(message.chat.id, text)

# ==================== CALLBACK HANDLERS ====================
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    data = call.data
    
    # Admin panel callbacks
    if data == "admin_users":
        users = db.get_all_users()
        text = f"👥 <b>USERS ({len(users)})</b>\n╔══════════════════════════════════╗\n"
        
        for user in users[:10]:
            status = "🟢" if not user[4] else "🔴"
            text += f"║ {status} <b>{user[1]}</b>\n"
            text += f"║    ID: {user[0]} | Credits: {user[3]}\n"
            text += "╠──────────────────────────────╣\n"
        
        text += "╚══════════════════════════════════╝"
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        for user in users[:10]:
            markup.add(types.InlineKeyboardButton(f"📊 {user[1]}", callback_data=f"user_{user[0]}"))
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="back_to_admin"))
        
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    
    elif data == "admin_bots":
        bots = db.get_all_bots()
        text = f"🤖 <b>BOTS ({len(bots)})</b>\n╔══════════════════════════════════╗\n"
        
        for bot_data in bots[:10]:
            status_icon = "🟢" if bot_data[5] == "Running" else "🔴"
            text += f"║ {status_icon} <b>{bot_data[2]}</b>\n"
            text += f"║    Owner: {bot_data[12]}\n"
            text += "╠──────────────────────────────╣\n"
        
        text += "╚══════════════════════════════════╝"
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        for bot_data in bots[:5]:
            markup.add(types.InlineKeyboardButton(f"🤖 {bot_data[2]}", callback_data=f"admin_bot_{bot_data[0]}"))
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="back_to_admin"))
        
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    
    elif data == "admin_stats":
        stats = db.get_stats()
        system = get_system_stats()
        
        text = f"""
<b>📊 SYSTEM STATISTICS</b>
╔══════════════════════════════════╗
║ 👥 <b>USERS</b>                       ║
║ ├ Total: {stats['total_users']}                  ║
╠══════════════════════════════════╣
║ 🤖 <b>BOTS</b>                        ║
║ ├ Total: {stats['total_bots']}                  ║
║ ├ Running: {stats['running_bots']}                ║
║ └ Deploys: {stats['total_deploys']}                  ║
╠══════════════════════════════════╣
║ 🖥️ <b>SYSTEM</b>                      ║
║ ├ CPU: {system['cpu']:.1f}% ({progress_bar(system['cpu'])})   ║
║ ├ RAM: {system['ram']:.1f}% ({progress_bar(system['ram'])})   ║
║ └ Uptime: {format_uptime(system['uptime'])}            ║
╚══════════════════════════════════╝
"""
        markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 Back", callback_data="back_to_admin"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    
    elif data == "admin_broadcast":
        msg = bot.send_message(call.message.chat.id, "📢 Enter broadcast message:")
        bot.register_next_step_handler(msg, process_broadcast_admin, call.message)
    
    elif data == "admin_backup":
        backup_path = Path(Config.DB_NAME)
        if backup_path.exists():
            with open(backup_path, 'rb') as f:
                bot.send_document(call.message.chat.id, f, 
                                caption=f"💾 Database Backup\nSize: {backup_path.stat().st_size / 1024:.2f} KB")
        bot.answer_callback_query(call.id, "Backup sent!")
    
    elif data == "admin_logs":
        logs = db.get_logs(20)
        text = "<b>📜 SYSTEM LOGS</b>\n╔══════════════════════════════════╗\n"
        
        for log in logs:
            text += f"║ [{log[4][:16]}] {log[0]}\n"
            text += f"║   Admin: {log[1]} | User: {log[2] or 'N/A'}\n"
            text += "╠──────────────────────────────╣\n"
        
        text += "╚══════════════════════════════════╝"
        
        markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 Back", callback_data="back_to_admin"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    
    elif data == "back_to_admin":
        admin_panel_menu(call.message)
    
    # User management callbacks
    elif data.startswith("user_"):
        user_id = int(data.split('_')[1])
        user = db.get_user(user_id)
        bots = db.get_user_bots(user_id)
        
        if user:
            text = f"""
<b>👤 USER DETAILS</b>
╔══════════════════════════════════╗
║ <b>INFO</b>                         ║
║ ├ ID: <code>{user[0]}</code>                 ║
║ ├ Username: @{user[1]}                 ║
║ └ Joined: {user[2][:10]}                ║
╠══════════════════════════════════╣
║ <b>ACCOUNT</b>                      ║
║ ├ Credits: {user[4]}                    ║
║ ├ Bots Limit: {user[5]}                   ║
║ ├ Status: {'🟢 Active' if not user[7] else '🔴 Banned'}           ║
║ └ Bots: {len(bots)}                    ║
╚══════════════════════════════════╝
"""
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                                reply_markup=user_controls(user_id))
    
    elif data.startswith("add_credits_"):
        user_id = int(data.split('_')[2])
        msg = bot.send_message(call.message.chat.id, f"Enter amount of credits to add for user {user_id}:")
        bot.register_next_step_handler(msg, process_add_credits, user_id, call.message)
    
    elif data.startswith("remove_credits_"):
        user_id = int(data.split('_')[2])
        msg = bot.send_message(call.message.chat.id, f"Enter amount of credits to remove from user {user_id}:")
        bot.register_next_step_handler(msg, process_remove_credits, user_id, call.message)
    
    elif data.startswith("extend_expiry_"):
        user_id = int(data.split('_')[2])
        msg = bot.send_message(call.message.chat.id, f"Enter days to extend for user {user_id}:")
        bot.register_next_step_handler(msg, process_extend_expiry, user_id, call.message)
    
    elif data.startswith("ban_"):
        user_id = int(data.split('_')[1])
        msg = bot.send_message(call.message.chat.id, f"Enter ban reason for user {user_id}:")
        bot.register_next_step_handler(msg, process_ban, user_id, call.message)
    
    elif data.startswith("unban_"):
        user_id = int(data.split('_')[1])
        db.unban_user(user_id)
        bot.answer_callback_query(call.id, f"✅ User {user_id} unbanned!")
        
        user = db.get_user(user_id)
        text = f"✅ User @{user[1]} has been unbanned!"
        bot.send_message(call.message.chat.id, text)
    
    elif data == "back_to_users":
        users = db.get_all_users()
        text = f"👥 <b>USERS ({len(users)})</b>\n╔══════════════════════════════════╗\n"
        
        for user in users[:10]:
            status = "🟢" if not user[4] else "🔴"
            text += f"║ {status} <b>{user[1]}</b>\n"
            text += f"║    ID: {user[0]} | Credits: {user[3]}\n"
            text += "╠──────────────────────────────╣\n"
        
        text += "╚══════════════════════════════════╝"
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        for user in users[:10]:
            markup.add(types.InlineKeyboardButton(f"📊 {user[1]}", callback_data=f"user_{user[0]}"))
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="back_to_admin"))
        
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    
    # Bot management callbacks
    elif data.startswith("admin_bot_"):
        bot_id = int(data.split('_')[2])
        cursor = db.conn.cursor()
        cursor.execute("SELECT id, bot_name, filename, status, user_id FROM bots WHERE id=?", (bot_id,))
        bot_data = cursor.fetchone()
        
        if bot_data:
            user = db.get_user(bot_data[4])
            text = f"""
<b>🤖 BOT DETAILS</b>
╔══════════════════════════════════╗
║ <b>Name:</b> {bot_data[1]}                 ║
║ <b>Owner:</b> @{user[1]}                 ║
║ <b>File:</b> {bot_data[2]}                 ║
║ <b>Status:</b> {bot_data[3]}                 ║
╚══════════════════════════════════╝
"""
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                                reply_markup=bot_controls(bot_id, bot_data[3]))
    
    elif data.startswith("stop_"):
        bot_id = int(data.split('_')[1])
        cursor = db.conn.cursor()
        cursor.execute("SELECT pid, bot_name FROM bots WHERE id=?", (bot_id,))
        bot_data = cursor.fetchone()
        
        if bot_data and bot_data[0]:
            try:
                os.kill(bot_data[0], signal.SIGTERM)
            except:
                pass
        
        cursor.execute("UPDATE bots SET pid=0, status='Stopped' WHERE id=?", (bot_id,))
        db.conn.commit()
        bot.answer_callback_query(call.id, f"⏸ {bot_data[1]} stopped!")
    
    elif data.startswith("start_"):
        bot_id = int(data.split('_')[1])
        cursor = db.conn.cursor()
        cursor.execute("SELECT bot_name, filename FROM bots WHERE id=?", (bot_id,))
        bot_data = cursor.fetchone()
        
        if bot_data:
            file_path = Path(Config.PROJECT_DIR) / bot_data[1]
            if file_path.exists():
                proc = subprocess.Popen(['python', str(file_path)], 
                                       start_new_session=True,
                                       stdout=subprocess.DEVNULL,
                                       stderr=subprocess.DEVNULL)
                cursor.execute("UPDATE bots SET pid=?, status='Running', start_time=? WHERE id=?",
                              (proc.pid, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), bot_id))
                db.conn.commit()
                bot.answer_callback_query(call.id, f"✅ {bot_data[0]} started!")
    
    elif data.startswith("restart_"):
        bot_id = int(data.split('_')[1])
        cursor = db.conn.cursor()
        cursor.execute("SELECT pid, bot_name, filename FROM bots WHERE id=?", (bot_id,))
        bot_data = cursor.fetchone()
        
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
            cursor.execute("UPDATE bots SET pid=?, status='Running', start_time=? WHERE id=?",
                          (proc.pid, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), bot_id))
            db.conn.commit()
            bot.answer_callback_query(call.id, f"🔄 {bot_data[1]} restarted!")
    
    elif data.startswith("export_"):
        bot_id = int(data.split('_')[1])
        cursor = db.conn.cursor()
        cursor.execute("SELECT bot_name, filename FROM bots WHERE id=?", (bot_id,))
        bot_data = cursor.fetchone()
        
        if bot_data:
            file_path = Path(Config.PROJECT_DIR) / bot_data[1]
            if file_path.exists():
                with open(file_path, 'rb') as f:
                    bot.send_document(call.message.chat.id, f, 
                                    caption=f"📦 Exported: {bot_data[0]}")
                bot.answer_callback_query(call.id, "Bot exported!")
    
    elif data.startswith("delete_"):
        bot_id = int(data.split('_')[1])
        cursor = db.conn.cursor()
        cursor.execute("SELECT pid, bot_name, filename FROM bots WHERE id=?", (bot_id,))
        bot_data = cursor.fetchone()
        
        if bot_data and bot_data[0]:
            try:
                os.kill(bot_data[0], signal.SIGKILL)
            except:
                pass
        
        file_path = Path(Config.PROJECT_DIR) / bot_data[2]
        if file_path.exists():
            file_path.unlink()
        
        cursor.execute("DELETE FROM bots WHERE id=?", (bot_id,))
        db.conn.commit()
        bot.answer_callback_query(call.id, f"🗑 {bot_data[1]} deleted!")
    
    elif data.startswith("stats_"):
        bot_id = int(data.split('_')[1])
        cursor = db.conn.cursor()
        cursor.execute("SELECT pid, bot_name, status FROM bots WHERE id=?", (bot_id,))
        bot_data = cursor.fetchone()
        
        if bot_data and bot_data[2] == "Running" and bot_data[0]:
            try:
                proc = psutil.Process(bot_data[0])
                cpu = proc.cpu_percent(interval=0.5)
                mem = proc.memory_percent()
                
                text = f"""
<b>📊 BOT STATISTICS</b>
╔══════════════════════════════════╗
║ <b>{bot_data[1]}</b>                     ║
╠══════════════════════════════════╣
║ 🖥️ <b>RESOURCES</b>                   ║
║ ├ CPU: {progress_bar(cpu)} {cpu:.1f}%    ║
║ ├ RAM: {progress_bar(mem)} {mem:.1f}%    ║
║ ├ PID: <code>{bot_data[0]}</code>                 ║
║ └ Status: 🟢 Running               ║
╚══════════════════════════════════╝
"""
                bot.send_message(call.message.chat.id, text)
            except:
                bot.answer_callback_query(call.id, "Cannot get stats!")
        else:
            bot.answer_callback_query(call.id, "Bot is not running!")
    
    elif data.startswith("template_"):
        template_id = int(data.split('_')[1])
        cursor = db.conn.cursor()
        cursor.execute("SELECT name, code FROM templates WHERE id=?", (template_id,))
        template = cursor.fetchone()
        
        if template:
            filename = f"template_{uuid.uuid4().hex[:8]}.py"
            file_path = Path(Config.PROJECT_DIR) / filename
            file_path.write_text(template[1])
            
            cursor.execute("UPDATE templates SET downloads=downloads+1 WHERE id=?", (template_id,))
            cursor.execute("INSERT INTO bots (user_id, bot_name, filename, status) VALUES (?, ?, ?, ?)",
                          (call.from_user.id, f"Template: {template[0]}", filename, "Uploaded"))
            db.conn.commit()
            
            bot.answer_callback_query(call.id, f"✅ Template '{template[0]}' added!")
            bot.send_message(call.message.chat.id, 
                           f"✅ Template '{template[0]}' saved!\n\nUse 'Deploy Bot' to start it.")
    
    elif data.startswith("user_bot_"):
        bot_id = int(data.split('_')[2])
        cursor = db.conn.cursor()
        cursor.execute("SELECT id, bot_name, filename, status, start_time FROM bots WHERE id=?", (bot_id,))
        bot_data = cursor.fetchone()
        
        if bot_data:
            uptime = "N/A"
            if bot_data[3] == "Running" and bot_data[4]:
                try:
                    start = datetime.strptime(bot_data[4], '%Y-%m-%d %H:%M:%S')
                    uptime = str(datetime.now() - start).split('.')[0]
                except:
                    pass
            
            text = f"""
<b>🤖 BOT DETAILS</b>
╔══════════════════════════════════╗
║ <b>Name:</b> {bot_data[1]}                 ║
║ <b>File:</b> {bot_data[2]}                 ║
║ <b>Status:</b> {bot_data[3]}                 ║
║ <b>Uptime:</b> {uptime}                 ║
╚══════════════════════════════════╝
"""
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                                reply_markup=bot_controls(bot_id, bot_data[3]))

# ==================== ADMIN PROCESSING FUNCTIONS ====================
def process_broadcast_admin(message, original_message):
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
    
    bot.send_message(original_message.chat.id, f"✅ Broadcast sent!\n\nSent: {success}\nFailed: {failed}")
    admin_panel_menu(original_message)

def process_add_credits(message, user_id, original_message):
    try:
        amount = int(message.text.strip())
        db.add_credits(user_id, amount)
        bot.send_message(message.chat.id, f"✅ Added {amount} credits to user {user_id}!")
        
        user = db.get_user(user_id)
        text = f"✅ User @{user[1]} now has {user[4]} credits!"
        bot.send_message(original_message.chat.id, text)
    except:
        bot.send_message(message.chat.id, "❌ Invalid amount!")

def process_remove_credits(message, user_id, original_message):
    try:
        amount = int(message.text.strip())
        db.remove_credits(user_id, amount)
        bot.send_message(message.chat.id, f"✅ Removed {amount} credits from user {user_id}!")
        
        user = db.get_user(user_id)
        text = f"✅ User @{user[1]} now has {user[4]} credits!"
        bot.send_message(original_message.chat.id, text)
    except:
        bot.send_message(message.chat.id, "❌ Invalid amount!")

def process_extend_expiry(message, user_id, original_message):
    try:
        days = int(message.text.strip())
        db.extend_expiry(user_id, days)
        bot.send_message(message.chat.id, f"✅ Extended expiry by {days} days for user {user_id}!")
        
        user = db.get_user(user_id)
        text = f"✅ User @{user[1]} expiry extended to {user[3][:10]}!"
        bot.send_message(original_message.chat.id, text)
    except:
        bot.send_message(message.chat.id, "❌ Invalid days!")

def process_ban(message, user_id, original_message):
    reason = message.text.strip()
    db.ban_user(user_id, reason)
    bot.send_message(message.chat.id, f"✅ User {user_id} banned!\nReason: {reason}")
    
    user = db.get_user(user_id)
    text = f"🔨 User @{user[1]} has been banned!\nReason: {reason}"
    bot.send_message(original_message.chat.id, text)

# ==================== FLASK ROUTES ====================
@app.route('/')
def home():
    stats = db.get_stats()
    return jsonify({
        "status": "online",
        "brand": Config.BRAND_NAME,
        "version": Config.VERSION,
        "stats": stats
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
        "credits": u[3],
        "banned": bool(u[4])
    } for u in users])

# ==================== BACKGROUND TASKS ====================
def cleanup_processes():
    while True:
        try:
            cursor = db.conn.cursor()
            cursor.execute("SELECT id, pid FROM bots WHERE status='Running'")
            running = cursor.fetchall()
            
            for bot_id, pid in running:
                if pid:
                    try:
                        os.kill(pid, 0)
                    except OSError:
                        cursor.execute("UPDATE bots SET status='Stopped', pid=0 WHERE id=?", (bot_id,))
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
