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
import csv
import io
from datetime import datetime, timedelta
from flask import Flask, jsonify, request, send_file
from telebot import types
from pathlib import Path
import random
import string
from collections import defaultdict
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO

# ==================== LOGGING SETUP ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==================== CONFIGURATION ====================
class Config:
    TOKEN = os.environ.get('BOT_TOKEN', '8754448627:AAFReyCErlSnESaSJOUzAt1Ut-n95w_xWDI')
    ADMIN_ID = int(os.environ.get('ADMIN_ID', 6487613131))
    PORT = int(os.environ.get('PORT', 10000))
    PROJECT_DIR = 'projects'
    DB_NAME = 'aurpon_bot.db'
    BACKUP_DIR = 'backups'
    LOGS_DIR = 'logs'
    
    BRAND_NAME = "𝐀𝐔𝐑𝐏𝐎𝐍 𝐃𝐄𝐗 𝐏𝐑𝐎"
    VERSION = "6.0.0"
    SUPPORT_ID = "@aurponmodz"
    BOT_USERNAME = "@aurpon_bot_host_bot"
    MAX_FILE_SIZE = 50 * 1024 * 1024
    
    # Create directories
    for dir_path in [PROJECT_DIR, BACKUP_DIR, LOGS_DIR]:
        Path(dir_path).mkdir(exist_ok=True)

# ==================== DATABASE MANAGER ====================
class DatabaseManager:
    def __init__(self):
        self.conn = sqlite3.connect(Config.DB_NAME, check_same_thread=False)
        self.init_db()
    
    def init_db(self):
        cursor = self.conn.cursor()
        
        # Users table with all fields
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            join_date TEXT,
            expiry_date TEXT,
            credits INTEGER DEFAULT 100,
            bots_limit INTEGER DEFAULT 5,
            is_admin INTEGER DEFAULT 0,
            is_banned INTEGER DEFAULT 0,
            ban_reason TEXT,
            referral_code TEXT,
            referred_by INTEGER,
            total_referrals INTEGER DEFAULT 0,
            total_spent REAL DEFAULT 0,
            last_active TEXT,
            language TEXT DEFAULT 'en',
            notifications INTEGER DEFAULT 1,
            theme TEXT DEFAULT 'dark'
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
            last_active TEXT,
            cpu_usage REAL,
            ram_usage REAL,
            deploy_count INTEGER DEFAULT 0,
            error_log TEXT,
            auto_restart INTEGER DEFAULT 0,
            port INTEGER
        )''')
        
        # Transactions table
        cursor.execute('''CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            type TEXT,
            status TEXT,
            transaction_id TEXT,
            payment_method TEXT,
            created_at TEXT
        )''')
        
        # Templates table
        cursor.execute('''CREATE TABLE IF NOT EXISTS templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            description TEXT,
            code TEXT,
            category TEXT,
            downloads INTEGER DEFAULT 0,
            rating REAL DEFAULT 0,
            created_by INTEGER,
            created_at TEXT
        )''')
        
        # System logs
        cursor.execute('''CREATE TABLE IF NOT EXISTS system_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT,
            admin_id INTEGER,
            user_id INTEGER,
            details TEXT,
            ip_address TEXT,
            created_at TEXT
        )''')
        
        # Backup logs
        cursor.execute('''CREATE TABLE IF NOT EXISTS backups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            size INTEGER,
            created_by INTEGER,
            created_at TEXT
        )''')
        
        # Add admin user
        admin_expiry = (datetime.now() + timedelta(days=3650)).strftime('%Y-%m-%d %H:%M:%S')
        referral_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        
        cursor.execute("INSERT OR IGNORE INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                      (Config.ADMIN_ID, 'admin', 'Administrator',
                       datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                       admin_expiry, 999999, 999, 1, 0, None,
                       referral_code, None, 0, 0,
                       datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                       'en', 1, 'dark'))
        
        # Add default templates
        self.add_default_templates()
        
        self.conn.commit()
    
    def add_default_templates(self):
        cursor = self.conn.cursor()
        
        templates = [
            ("Echo Bot", "Simple echo bot that replies with same message", 
             "import telebot\nTOKEN = 'YOUR_BOT_TOKEN'\nbot = telebot.TeleBot(TOKEN)\n\n@bot.message_handler(func=lambda m: True)\ndef echo(message):\n    bot.reply_to(message, message.text)\n\nbot.infinity_polling()",
             "basic", Config.ADMIN_ID),
            
            ("Weather Bot", "Get weather information for any city",
             "import telebot\nimport requests\n\nTOKEN = 'YOUR_BOT_TOKEN'\nbot = telebot.TeleBot(TOKEN)\n\n@bot.message_handler(commands=['weather'])\ndef weather(message):\n    city = message.text.replace('/weather', '').strip()\n    if city:\n        api_key = 'YOUR_API_KEY'\n        url = f'http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric'\n        data = requests.get(url).json()\n        temp = data['main']['temp']\n        bot.reply_to(message, f'Weather in {city}: {temp}°C')\n\nbot.infinity_polling()",
             "utility", Config.ADMIN_ID),
            
            ("Calculator Bot", "Perform mathematical calculations",
             "import telebot\n\nTOKEN = 'YOUR_BOT_TOKEN'\nbot = telebot.TeleBot(TOKEN)\n\n@bot.message_handler(func=lambda m: True)\ndef calculate(message):\n    try:\n        result = eval(message.text)\n        bot.reply_to(message, f'Result: {result}')\n    except:\n        bot.reply_to(message, 'Invalid expression!')\n\nbot.infinity_polling()",
             "utility", Config.ADMIN_ID),
            
            ("Quote Bot", "Send random quotes",
             "import telebot\nimport random\n\nTOKEN = 'YOUR_BOT_TOKEN'\nbot = telebot.TeleBot(TOKEN)\n\nquotes = [\n    'The only limit is your mind.',\n    'Stay positive, work hard.',\n    'Believe you can and you're halfway there.'\n]\n\n@bot.message_handler(commands=['quote'])\ndef quote(message):\n    bot.reply_to(message, random.choice(quotes))\n\nbot.infinity_polling()",
             "entertainment", Config.ADMIN_ID)
        ]
        
        for t in templates:
            cursor.execute("INSERT OR IGNORE INTO templates (name, description, code, category, downloads, rating, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                          (t[0], t[1], t[2], t[3], 0, 0, t[4], datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        
        self.conn.commit()
    
    def get_user(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id=?", (user_id,))
        return cursor.fetchone()
    
    def get_all_users(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, username, join_date, expiry_date, credits, is_banned FROM users ORDER BY id DESC")
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
        active_users = cursor.execute("SELECT COUNT(*) FROM users WHERE last_active > datetime('now', '-7 day')").fetchone()[0]
        banned_users = cursor.execute("SELECT COUNT(*) FROM users WHERE is_banned=1").fetchone()[0]
        
        total_bots = cursor.execute("SELECT COUNT(*) FROM bots").fetchone()[0]
        running_bots = cursor.execute("SELECT COUNT(*) FROM bots WHERE status='Running'").fetchone()[0]
        
        total_deploys = cursor.execute("SELECT SUM(deploy_count) FROM bots").fetchone()[0] or 0
        total_revenue = cursor.execute("SELECT SUM(amount) FROM transactions WHERE status='completed'").fetchone()[0] or 0
        
        return {
            'total_users': total_users,
            'active_users': active_users,
            'banned_users': banned_users,
            'total_bots': total_bots,
            'running_bots': running_bots,
            'total_deploys': total_deploys,
            'total_revenue': total_revenue
        }
    
    def ban_user(self, user_id, reason):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE users SET is_banned=1, ban_reason=? WHERE id=?", (reason, user_id))
        self.conn.commit()
        self.log_action(Config.ADMIN_ID, 'ban_user', user_id, f"Banned: {reason}")
    
    def unban_user(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE users SET is_banned=0, ban_reason=NULL WHERE id=?", (user_id,))
        self.conn.commit()
        self.log_action(Config.ADMIN_ID, 'unban_user', user_id, "Unbanned")
    
    def add_credits(self, user_id, amount):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE users SET credits=credits+? WHERE id=?", (amount, user_id))
        self.conn.commit()
        self.log_action(Config.ADMIN_ID, 'add_credits', user_id, f"Added {amount} credits")
    
    def remove_credits(self, user_id, amount):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE users SET credits=credits-? WHERE id=?", (amount, user_id))
        self.conn.commit()
        self.log_action(Config.ADMIN_ID, 'remove_credits', user_id, f"Removed {amount} credits")
    
    def extend_expiry(self, user_id, days):
        cursor = self.conn.cursor()
        user = self.get_user(user_id)
        if user and user[4]:
            current_expiry = datetime.strptime(user[4], '%Y-%m-%d %H:%M:%S')
            new_expiry = current_expiry + timedelta(days=days)
        else:
            new_expiry = datetime.now() + timedelta(days=days)
        
        cursor.execute("UPDATE users SET expiry_date=? WHERE id=?", (new_expiry.strftime('%Y-%m-%d %H:%M:%S'), user_id))
        self.conn.commit()
        self.log_action(Config.ADMIN_ID, 'extend_expiry', user_id, f"Extended by {days} days")
    
    def log_action(self, admin_id, action, user_id, details):
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO system_logs (action, admin_id, user_id, details, created_at) VALUES (?, ?, ?, ?, ?)",
                      (action, admin_id, user_id, details, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        self.conn.commit()
    
    def backup_database(self, admin_id):
        backup_filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        backup_path = Path(Config.BACKUP_DIR) / backup_filename
        shutil.copy2(Config.DB_NAME, backup_path)
        
        size = backup_path.stat().st_size
        
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO backups (filename, size, created_by, created_at) VALUES (?, ?, ?, ?)",
                      (backup_filename, size, admin_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        self.conn.commit()
        
        return backup_path

db = DatabaseManager()

# ==================== BOT INITIALIZATION ====================
bot = telebot.TeleBot(Config.TOKEN, parse_mode="HTML")
app = Flask(__name__)

# ==================== HELPER FUNCTIONS ====================
def is_admin(user_id):
    user = db.get_user(user_id)
    return user and user[7] == 1

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
        return {'cpu': 25, 'ram': 40, 'ram_used': 2e9, 'ram_total': 8e9, 'disk': 50, 'disk_used': 50e9, 'disk_total': 100e9, 'uptime': 86400}

def format_bytes(bytes):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024.0:
            return f"{bytes:.2f} {unit}"
        bytes /= 1024.0
    return f"{bytes:.2f} TB"

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
def main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    
    buttons = [
        "📤 Upload Bot", "🤖 My Bots",
        "⚡ Deploy Bot", "🎨 Templates",
        "💰 Buy Credits", "📊 Dashboard",
        "❓ Help", "ℹ️ About"
    ]
    
    if is_admin(user_id):
        buttons.extend(["👑 Admin Panel", "📈 Full Stats"])
    
    markup.add(*[types.KeyboardButton(btn) for btn in buttons])
    return markup

def admin_panel():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("👥 Users", callback_data="admin_users"),
        types.InlineKeyboardButton("🤖 Bots", callback_data="admin_bots"),
        types.InlineKeyboardButton("💰 Revenue", callback_data="admin_revenue"),
        types.InlineKeyboardButton("📊 Stats", callback_data="admin_stats"),
        types.InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast"),
        types.InlineKeyboardButton("💾 Backup", callback_data="admin_backup"),
        types.InlineKeyboardButton("📜 Logs", callback_data="admin_logs"),
        types.InlineKeyboardButton("⚙️ Settings", callback_data="admin_settings"),
        types.InlineKeyboardButton("🎨 Templates", callback_data="admin_templates"),
        types.InlineKeyboardButton("📈 Analytics", callback_data="admin_analytics")
    )
    return markup

def user_control_menu(user_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("💰 Add Credits", callback_data=f"add_credits_{user_id}"),
        types.InlineKeyboardButton("💎 Remove Credits", callback_data=f"remove_credits_{user_id}"),
        types.InlineKeyboardButton("📅 Extend Expiry", callback_data=f"extend_expiry_{user_id}"),
        types.InlineKeyboardButton("🔨 Ban User", callback_data=f"ban_user_{user_id}"),
        types.InlineKeyboardButton("🔓 Unban User", callback_data=f"unban_user_{user_id}"),
        types.InlineKeyboardButton("📊 User Stats", callback_data=f"user_stats_{user_id}"),
        types.InlineKeyboardButton("🔙 Back", callback_data="admin_users_back")
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
        types.InlineKeyboardButton("🗑 Delete", callback_data=f"delete_{bot_id}"),
        types.InlineKeyboardButton("📝 Logs", callback_data=f"logs_{bot_id}")
    )
    
    return markup

# ==================== MESSAGE HANDLERS ====================
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    username = message.from_user.username or "User"
    full_name = message.from_user.first_name or "User"
    
    user = db.get_user(user_id)
    if not user:
        referral_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        expiry = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
        
        cursor = db.conn.cursor()
        cursor.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                      (user_id, username, full_name,
                       datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                       expiry, 100, 5, 0, 0, None,
                       referral_code, None, 0, 0,
                       datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                       'en', 1, 'dark'))
        db.conn.commit()
        user = db.get_user(user_id)
    
    stats = get_system_stats()
    
    text = f"""
╔══════════════════════════════════╗
║  {Config.BRAND_NAME} v{Config.VERSION}  ║
╠══════════════════════════════════╣
║ 👤 <b>USER INFO</b>                  ║
║ ├ ID: <code>{user_id}</code>                 ║
║ ├ Name: @{username}                 ║
║ └ Status: {'👑 ADMIN' if user[7] else '⭐ USER'}             ║
╠══════════════════════════════════╣
║ 💎 <b>ACCOUNT</b>                    ║
║ ├ Credits: {user[5]}                    ║
║ ├ Bots Limit: {user[6]}                   ║
║ └ Banned: {'✅ No' if not user[8] else '❌ Yes'}                 ║
╠══════════════════════════════════╣
║ 🖥️ <b>SYSTEM</b>                      ║
║ ├ CPU: {progress_bar(stats['cpu'])} {stats['cpu']:.0f}%    ║
║ ├ RAM: {progress_bar(stats['ram'])} {stats['ram']:.0f}%    ║
║ ├ Disk: {progress_bar(stats['disk'])} {stats['disk']:.0f}%    ║
║ └ Uptime: {format_uptime(stats['uptime'])}            ║
╚══════════════════════════════════╝

🎁 <b>Referral Code:</b> <code>{user[10]}</code>
Share and get 50 credits per referral!
"""
    
    bot.send_message(message.chat.id, text, reply_markup=main_menu(user_id))

@bot.message_handler(func=lambda m: m.text == "👑 Admin Panel")
def admin_panel_menu(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ Admin access only!")
        return
    
    stats = db.get_stats()
    system_stats = get_system_stats()
    
    text = f"""
╔══════════════════════════════════╗
║        👑 ADMIN PANEL           ║
╠══════════════════════════════════╣
║ 📊 <b>STATISTICS</b>                 ║
║ ├ Users: {stats['total_users']}                    ║
║ ├ Active: {stats['active_users']} (7d)             ║
║ ├ Banned: {stats['banned_users']}                   ║
║ ├ Bots: {stats['total_bots']}/{stats['running_bots']} running   ║
║ ├ Deploys: {stats['total_deploys']}                  ║
║ └ Revenue: ${stats['total_revenue']:.2f}               ║
╠══════════════════════════════════╣
║ 🖥️ <b>SYSTEM</b>                     ║
║ ├ CPU: {system_stats['cpu']:.1f}%                  ║
║ ├ RAM: {system_stats['ram']:.1f}% ({format_bytes(system_stats['ram_used'])}/{format_bytes(system_stats['ram_total'])}) ║
║ ├ Disk: {system_stats['disk']:.1f}%                  ║
║ └ Uptime: {format_uptime(system_stats['uptime'])}            ║
╚══════════════════════════════════╝

Select an option below:
"""
    
    bot.send_message(message.chat.id, text, reply_markup=admin_panel())

@bot.message_handler(func=lambda m: m.text == "📈 Full Stats")
def full_stats(message):
    if not is_admin(message.from_user.id):
        return
    
    # Create chart
    plt.style.use('dark_background')
    fig, axes = plt.subplots(2, 2, figsize=(10, 8))
    
    # User growth (simulated)
    dates = [(datetime.now() - timedelta(days=i)).strftime('%m/%d') for i in range(7, -1, -1)]
    users = [random.randint(100, 200) for _ in range(8)]
    
    axes[0, 0].plot(dates, users, marker='o', color='#00ff00')
    axes[0, 0].set_title('User Growth')
    axes[0, 0].set_xlabel('Date')
    axes[0, 0].set_ylabel('Users')
    axes[0, 0].tick_params(rotation=45)
    
    # Bot distribution
    stats = db.get_stats()
    labels = ['Running', 'Stopped', 'Uploaded']
    sizes = [stats['running_bots'], stats['total_bots'] - stats['running_bots'], 0]
    axes[0, 1].pie(sizes, labels=labels, autopct='%1.1f%%', colors=['#00ff00', '#ff0000', '#ffff00'])
    axes[0, 1].set_title('Bot Status')
    
    # Revenue (simulated)
    revenue = [random.randint(50, 200) for _ in range(8)]
    axes[1, 0].bar(dates, revenue, color='#ff6600')
    axes[1, 0].set_title('Daily Revenue ($)')
    axes[1, 0].set_xlabel('Date')
    axes[1, 0].set_ylabel('Revenue')
    axes[1, 0].tick_params(rotation=45)
    
    # System resources
    system = get_system_stats()
    resources = ['CPU', 'RAM', 'Disk']
    usage = [system['cpu'], system['ram'], system['disk']]
    axes[1, 1].barh(resources, usage, color='#00ff00')
    axes[1, 1].set_title('System Resources (%)')
    axes[1, 1].set_xlabel('Usage')
    
    plt.tight_layout()
    
    # Save chart
    img_buffer = BytesIO()
    plt.savefig(img_buffer, format='png', dpi=100, bbox_inches='tight')
    img_buffer.seek(0)
    plt.close()
    
    bot.send_photo(message.chat.id, img_buffer, caption="📊 Full Analytics Dashboard")
    
    # Send detailed stats
    text = f"""
<b>📈 DETAILED STATISTICS</b>
╔══════════════════════════════════╗
║ <b>USERS</b>                         ║
║ ├ Total: {stats['total_users']}                  ║
║ ├ Active (7d): {stats['active_users']}              ║
║ └ Banned: {stats['banned_users']}                  ║
╠══════════════════════════════════╣
║ <b>BOTS</b>                          ║
║ ├ Total: {stats['total_bots']}                  ║
║ ├ Running: {stats['running_bots']}                ║
║ └ Total Deploys: {stats['total_deploys']}           ║
╠══════════════════════════════════╣
║ <b>FINANCE</b>                       ║
║ └ Total Revenue: ${stats['total_revenue']:.2f}            ║
╚══════════════════════════════════╝
"""
    bot.send_message(message.chat.id, text)

# ==================== USER MANAGEMENT ====================
def show_users_page(message, page=0, per_page=10):
    users = db.get_all_users()
    total_pages = (len(users) + per_page - 1) // per_page
    
    start = page * per_page
    end = start + per_page
    page_users = users[start:end]
    
    text = f"<b>👥 USERS (Page {page + 1}/{total_pages})</b>\n╔══════════════════════════════════╗\n"
    
    for user in page_users:
        status = "🟢" if not user[5] else "🔴"
        text += f"║ {status} <b>{user[1]}</b> (ID: {user[0]})\n"
        text += f"║    Credits: {user[4]} | Banned: {'Yes' if user[5] else 'No'}\n"
        text += "╠──────────────────────────────╣\n"
    
    text += "╚══════════════════════════════════╝"
    
    markup = types.InlineKeyboardMarkup(row_width=3)
    
    if page > 0:
        markup.add(types.InlineKeyboardButton("◀️ Prev", callback_data=f"users_page_{page-1}"))
    if page < total_pages - 1:
        markup.add(types.InlineKeyboardButton("Next ▶️", callback_data=f"users_page_{page+1}"))
    
    for user in page_users:
        markup.add(types.InlineKeyboardButton(f"📊 {user[1]}", callback_data=f"user_{user[0]}"))
    
    markup.add(types.InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_back"))
    
    bot.edit_message_text(text, message.chat.id, message.message_id, reply_markup=markup)

# ==================== CALLBACK HANDLERS ====================
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    action = call.data
    
    if action == "admin_users":
        users = db.get_all_users()
        text = f"<b>👥 USERS ({len(users)})</b>\n╔══════════════════════════════════╗\n"
        
        for user in users[:10]:
            status = "🟢" if not user[5] else "🔴"
            text += f"║ {status} <b>{user[1]}</b>\n"
            text += f"║    ID: {user[0]} | Credits: {user[4]}\n"
            text += "╠──────────────────────────────╣\n"
        
        if len(users) > 10:
            text += f"║ ... and {len(users)-10} more\n"
        
        text += "╚══════════════════════════════════╝"
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        for user in users[:10]:
            markup.add(types.InlineKeyboardButton(f"📊 {user[1]}", callback_data=f"user_{user[0]}"))
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="admin_back"))
        
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    
    elif action == "admin_bots":
        bots = db.get_all_bots()
        text = f"<b>🤖 BOTS ({len(bots)})</b>\n╔══════════════════════════════════╗\n"
        
        for bot_data in bots[:10]:
            status_icon = "🟢" if bot_data[5] == "Running" else "🔴"
            text += f"║ {status_icon} <b>{bot_data[2]}</b>\n"
            text += f"║    Owner: {bot_data[15]}\n"
            text += f"║    Status: {bot_data[5]}\n"
            text += "╠──────────────────────────────╣\n"
        
        text += "╚══════════════════════════════════╝"
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        for bot_data in bots[:5]:
            markup.add(types.InlineKeyboardButton(f"🤖 {bot_data[2]}", callback_data=f"admin_bot_{bot_data[0]}"))
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="admin_back"))
        
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    
    elif action == "admin_stats":
        stats = db.get_stats()
        system = get_system_stats()
        
        text = f"""
<b>📊 SYSTEM STATISTICS</b>
╔══════════════════════════════════╗
║ <b>USERS</b>                         ║
║ ├ Total: {stats['total_users']}                  ║
║ ├ Active (7d): {stats['active_users']}              ║
║ ├ Banned: {stats['banned_users']}                  ║
║ └ Growth: +{random.randint(5, 15)}% this week        ║
╠══════════════════════════════════╣
║ <b>BOTS</b>                          ║
║ ├ Total: {stats['total_bots']}                  ║
║ ├ Running: {stats['running_bots']}                ║
║ ├ Stopped: {stats['total_bots'] - stats['running_bots']}              ║
║ └ Deploys: {stats['total_deploys']}                  ║
╠══════════════════════════════════╣
║ <b>SYSTEM</b>                        ║
║ ├ CPU: {system['cpu']:.1f}% ({progress_bar(system['cpu'])})   ║
║ ├ RAM: {system['ram']:.1f}% ({progress_bar(system['ram'])})   ║
║ ├ Disk: {system['disk']:.1f}% ({progress_bar(system['disk'])})   ║
║ └ Uptime: {format_uptime(system['uptime'])}            ║
╠══════════════════════════════════╣
║ <b>FINANCE</b>                       ║
║ └ Revenue: ${stats['total_revenue']:.2f}                ║
╚══════════════════════════════════╝
"""
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, 
                            reply_markup=types.InlineKeyboardMarkup().add(
                                types.InlineKeyboardButton("🔙 Back", callback_data="admin_back")
                            ))
    
    elif action == "admin_revenue":
        stats = db.get_stats()
        
        text = f"""
<b>💰 REVENUE REPORT</b>
╔══════════════════════════════════╗
║ <b>TOTAL</b>                        ║
║ ├ Revenue: ${stats['total_revenue']:.2f}               ║
║ ├ Avg per user: ${stats['total_revenue']/stats['total_users'] if stats['total_users'] > 0 else 0:.2f}        ║
║ └ Projected: ${stats['total_revenue'] * 1.2:.2f} (next month)    ║
╠══════════════════════════════════╣
║ <b>PACKAGES</b>                     ║
║ ├ Basic (100cr): ${stats['total_revenue'] * 0.3:.2f}              ║
║ ├ Pro (500cr): ${stats['total_revenue'] * 0.4:.2f}               ║
║ └ Enterprise (1000cr): ${stats['total_revenue'] * 0.3:.2f}        ║
╠══════════════════════════════════╣
║ <b>TOP USERS</b>                    ║
║ ├ Coming soon...                  ║
╚══════════════════════════════════╝
"""
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                            reply_markup=types.InlineKeyboardMarkup().add(
                                types.InlineKeyboardButton("🔙 Back", callback_data="admin_back")
                            ))
    
    elif action == "admin_backup":
        backup_path = db.backup_database(call.from_user.id)
        
        with open(backup_path, 'rb') as f:
            bot.send_document(call.message.chat.id, f, 
                            caption=f"💾 Backup created: {backup_path.name}\nSize: {format_bytes(backup_path.stat().st_size)}")
        
        bot.edit_message_text("✅ Backup created and sent!", call.message.chat.id, call.message.message_id,
                            reply_markup=types.InlineKeyboardMarkup().add(
                                types.InlineKeyboardButton("🔙 Back", callback_data="admin_back")
                            ))
    
    elif action.startswith("user_"):
        user_id = int(action.split('_')[1])
        user = db.get_user(user_id)
        bots = db.get_user_bots(user_id)
        
        if user:
            text = f"""
<b>👤 USER DETAILS</b>
╔══════════════════════════════════╗
║ <b>INFO</b>                         ║
║ ├ ID: <code>{user[0]}</code>                 ║
║ ├ Username: @{user[1]}                 ║
║ ├ Name: {user[2]}               ║
║ └ Joined: {user[3][:10]}                ║
╠══════════════════════════════════╣
║ <b>ACCOUNT</b>                      ║
║ ├ Credits: {user[5]}                    ║
║ ├ Bots Limit: {user[6]}                   ║
║ ├ Status: {'🟢 Active' if not user[8] else '🔴 Banned'}           ║
║ └ Expiry: {user[4][:10] if user[4] else 'Never'}           ║
╠══════════════════════════════════╣
║ <b>STATS</b>                        ║
║ ├ Bots: {len(bots)}                    ║
║ ├ Running: {len([b for b in bots if b[5] == 'Running'])}                ║
║ ├ Referrals: {user[12]}                  ║
║ └ Last Active: {user[14][:10] if user[14] else 'Never'}       ║
╚══════════════════════════════════╝
"""
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                                reply_markup=user_control_menu(user_id))
    
    elif action.startswith("add_credits_"):
        user_id = int(action.split('_')[2])
        msg = bot.send_message(call.message.chat.id, f"Enter amount of credits to add for user {user_id}:")
        bot.register_next_step_handler(msg, process_add_credits, user_id, call.message)
    
    elif action.startswith("ban_user_"):
        user_id = int(action.split('_')[2])
        msg = bot.send_message(call.message.chat.id, f"Enter ban reason for user {user_id}:")
        bot.register_next_step_handler(msg, process_ban_user, user_id, call.message)
    
    elif action.startswith("unban_user_"):
        user_id = int(action.split('_')[2])
        db.unban_user(user_id)
        bot.answer_callback_query(call.id, f"✅ User {user_id} unbanned!")
        
        user = db.get_user(user_id)
        text = f"""
<b>👤 USER DETAILS</b>
╔══════════════════════════════════╗
║ <b>INFO</b>                         ║
║ ├ ID: <code>{user[0]}</code>                 ║
║ ├ Username: @{user[1]}                 ║
║ └ Status: {'🟢 Active' if not user[8] else '🔴 Banned'}           ║
╚══════════════════════════════════╝
"""
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                            reply_markup=user_control_menu(user_id))
    
    elif action == "admin_back":
        admin_panel_menu(call.message)
    
    elif action.startswith("start_"):
        bot_id = int(action.split('_')[1])
        start_bot_process(call, bot_id)
    
    elif action.startswith("stop_"):
        bot_id = int(action.split('_')[1])
        stop_bot_process(call, bot_id)
    
    elif action.startswith("restart_"):
        bot_id = int(action.split('_')[1])
        restart_bot_process(call, bot_id)
    
    elif action.startswith("export_"):
        bot_id = int(action.split('_')[1])
        export_bot_process(call, bot_id)
    
    elif action.startswith("delete_"):
        bot_id = int(action.split('_')[1])
        delete_bot_process(call, bot_id)
    
    elif action.startswith("stats_"):
        bot_id = int(action.split('_')[1])
        show_bot_stats(call, bot_id)
    
    elif action == "admin_broadcast":
        msg = bot.send_message(call.message.chat.id, "📢 Enter broadcast message:")
        bot.register_next_step_handler(msg, process_broadcast, call.message)
    
    elif action == "admin_logs":
        cursor = db.conn.cursor()
        cursor.execute("SELECT action, admin_id, user_id, details, created_at FROM system_logs ORDER BY id DESC LIMIT 20")
        logs = cursor.fetchall()
        
        text = "<b>📜 SYSTEM LOGS</b>\n╔══════════════════════════════════╗\n"
        for log in logs:
            text += f"║ [{log[4][:16]}] {log[0]}\n"
            text += f"║   Admin: {log[1]} | User: {log[2] or 'N/A'}\n"
            text += "╠──────────────────────────────╣\n"
        
        text += "╚══════════════════════════════════╝"
        
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                            reply_markup=types.InlineKeyboardMarkup().add(
                                types.InlineKeyboardButton("🔙 Back", callback_data="admin_back")
                            ))
    
    bot.answer_callback_query(call.id)

# ==================== BOT OPERATIONS ====================
def start_bot_process(call, bot_id):
    cursor = db.conn.cursor()
    cursor.execute("SELECT user_id, bot_name, filename FROM bots WHERE id=?", (bot_id,))
    bot_data = cursor.fetchone()
    
    if not bot_data:
        return
    
    file_path = Path(Config.PROJECT_DIR) / bot_data[2]
    if not file_path.exists():
        bot.answer_callback_query(call.id, "File not found!")
        return
    
    proc = subprocess.Popen(['python', str(file_path)], 
                           start_new_session=True,
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)
    
    cursor.execute("UPDATE bots SET pid=?, status='Running', start_time=? WHERE id=?",
                  (proc.pid, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), bot_id))
    db.conn.commit()
    
    bot.answer_callback_query(call.id, f"✅ {bot_data[1]} started!")

def stop_bot_process(call, bot_id):
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

def restart_bot_process(call, bot_id):
    stop_bot_process(call, bot_id)
    time.sleep(1)
    start_bot_process(call, bot_id)

def export_bot_process(call, bot_id):
    cursor = db.conn.cursor()
    cursor.execute("SELECT bot_name, filename FROM bots WHERE id=?", (bot_id,))
    bot_data = cursor.fetchone()
    
    if not bot_data:
        return
    
    file_path = Path(Config.PROJECT_DIR) / bot_data[1]
    if file_path.exists():
        with open(file_path, 'rb') as f:
            bot.send_document(call.message.chat.id, f, 
                            caption=f"📦 Exported: {bot_data[0]}")
        bot.answer_callback_query(call.id, "Bot exported!")
    else:
        bot.answer_callback_query(call.id, "File not found!")

def delete_bot_process(call, bot_id):
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
    
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass

def show_bot_stats(call, bot_id):
    cursor = db.conn.cursor()
    cursor.execute("SELECT pid, bot_name, status, cpu_usage, ram_usage FROM bots WHERE id=?", (bot_id,))
    bot_data = cursor.fetchone()
    
    if not bot_data or bot_data[2] != "Running":
        bot.answer_callback_query(call.id, "Bot is not running!")
        return
    
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
║ └ Threads: {proc.num_threads()}               ║
╠══════════════════════════════════╣
║ 📈 <b>PERFORMANCE</b>                  ║
║ ├ Memory RSS: {format_bytes(proc.memory_info().rss)}        ║
║ └ Status: {'🟢 Running' if bot_data[2] == 'Running' else '🔴 Stopped'}        ║
╚══════════════════════════════════╝
"""
        bot.send_message(call.message.chat.id, text)
        
    except Exception as e:
        bot.answer_callback_query(call.id, f"Error: {str(e)[:50]}")

# ==================== ADMIN PROCESSING ====================
def process_add_credits(message, user_id, original_message):
    try:
        amount = int(message.text.strip())
        db.add_credits(user_id, amount)
        bot.send_message(message.chat.id, f"✅ Added {amount} credits to user {user_id}!")
        
        user = db.get_user(user_id)
        text = f"""
<b>👤 USER DETAILS</b>
╔══════════════════════════════════╗
║ <b>INFO</b>                         ║
║ ├ ID: <code>{user[0]}</code>                 ║
║ ├ Username: @{user[1]}                 ║
║ └ Credits: {user[5]} (Updated)           ║
╚══════════════════════════════════╝
"""
        bot.send_message(original_message.chat.id, text, reply_markup=user_control_menu(user_id))
    except:
        bot.send_message(message.chat.id, "❌ Invalid amount!")

def process_ban_user(message, user_id, original_message):
    reason = message.text.strip()
    db.ban_user(user_id, reason)
    bot.send_message(message.chat.id, f"✅ User {user_id} banned!\nReason: {reason}")
    
    user = db.get_user(user_id)
    text = f"""
<b>👤 USER DETAILS</b>
╔══════════════════════════════════╗
║ <b>INFO</b>                         ║
║ ├ ID: <code>{user[0]}</code>                 ║
║ ├ Username: @{user[1]}                 ║
║ └ Status: 🔴 Banned                ║
╚══════════════════════════════════╝
"""
    bot.send_message(original_message.chat.id, text, reply_markup=user_control_menu(user_id))

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
    
    bot.send_message(original_message.chat.id, f"✅ Broadcast sent!\n\nSent: {success}\nFailed: {failed}")
    admin_panel_menu(original_message)

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

@app.route('/api/users')
def api_users():
    users = db.get_all_users()
    return jsonify([{
        "id": u[0],
        "username": u[1],
        "credits": u[4],
        "banned": bool(u[5])
    } for u in users])

@app.route('/api/stats')
def api_stats():
    return jsonify(db.get_stats())

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
    app.run(host='0.0.0.0', port=Config.PORT, debug=False)    VERSION = "5.0.0"
    SUPPORT_ID = "@aurponmodz"
    BOT_USERNAME = "@aurpon_bot_host_bot"
    MAX_FILE_SIZE = 50 * 1024 * 1024
    
    # Create directories
    for dir_path in [PROJECT_DIR]:
        Path(dir_path).mkdir(exist_ok=True)

# ==================== DATABASE ====================
class DatabaseManager:
    def __init__(self):
        self.conn = sqlite3.connect(Config.DB_NAME, check_same_thread=False)
        self.init_db()
    
    def init_db(self):
        cursor = self.conn.cursor()
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            join_date TEXT,
            expiry_date TEXT,
            credits INTEGER DEFAULT 100,
            bots_limit INTEGER DEFAULT 5,
            is_vip INTEGER DEFAULT 0,
            referral_code TEXT
        )''')
        
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
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            description TEXT,
            code TEXT,
            downloads INTEGER DEFAULT 0
        )''')
        
        # Add admin
        cursor.execute("INSERT OR IGNORE INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                      (Config.ADMIN_ID, 'admin', datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                       (datetime.now() + timedelta(days=3650)).strftime('%Y-%m-%d %H:%M:%S'),
                       999999, 999, 1, 'ADMIN'))
        
        # Add templates
        templates = [
            ("Echo Bot", "Simple echo bot", 
             '''import telebot
TOKEN = "YOUR_BOT_TOKEN"
bot = telebot.TeleBot(TOKEN)
@bot.message_handler(func=lambda m: True)
def echo(message):
    bot.reply_to(message, message.text)
bot.infinity_polling()'''),
            
            ("Weather Bot", "Get weather info",
             '''import telebot, requests
TOKEN = "YOUR_BOT_TOKEN"
bot = telebot.TeleBot(TOKEN)
@bot.message_handler(commands=['weather'])
def weather(message):
    city = message.text.replace('/weather', '').strip()
    if city:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&units=metric&appid=YOUR_API_KEY"
        data = requests.get(url).json()
        temp = data['main']['temp']
        bot.reply_to(message, f"Weather: {temp}°C")
bot.infinity_polling()'''),
            
            ("Calculator Bot", "Math calculator",
             '''import telebot
TOKEN = "YOUR_BOT_TOKEN"
bot = telebot.TeleBot(TOKEN)
@bot.message_handler(func=lambda m: True)
def calc(message):
    try:
        result = eval(message.text)
        bot.reply_to(message, f"Result: {result}")
    except:
        bot.reply_to(message, "Invalid!")
bot.infinity_polling()''')
        ]
        
        for t in templates:
            cursor.execute("INSERT OR IGNORE INTO templates (name, description, code) VALUES (?, ?, ?)", t)
        
        self.conn.commit()
    
    def get_user(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id=?", (user_id,))
        return cursor.fetchone()
    
    def get_user_bots(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM bots WHERE user_id=? ORDER BY id DESC", (user_id,))
        return cursor.fetchall()
    
    def add_credits(self, user_id, amount):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE users SET credits=credits+? WHERE id=?", (amount, user_id))
        self.conn.commit()

db = DatabaseManager()

# ==================== BOT INITIALIZATION ====================
bot = telebot.TeleBot(Config.TOKEN, parse_mode="HTML")
app = Flask(__name__)

# ==================== KEYBOARDS ====================
def main_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    buttons = [
        "📤 UPLOAD BOT", "🤖 MY BOTS",
        "⚡ DEPLOY BOT", "🎨 TEMPLATES",
        "💰 BUY CREDITS", "📊 DASHBOARD",
        "❓ HELP", "ℹ️ ABOUT"
    ]
    markup.add(*[types.KeyboardButton(btn) for btn in buttons])
    return markup

def bot_controls(bot_id, status):
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    if status == "Running":
        markup.add(
            types.InlineKeyboardButton("⏸ STOP", callback_data=f"stop_{bot_id}"),
            types.InlineKeyboardButton("🔄 RESTART", callback_data=f"restart_{bot_id}")
        )
    else:
        markup.add(
            types.InlineKeyboardButton("▶️ START", callback_data=f"start_{bot_id}"),
            types.InlineKeyboardButton("📊 STATS", callback_data=f"stats_{bot_id}")
        )
    
    markup.add(
        types.InlineKeyboardButton("📦 EXPORT", callback_data=f"export_{bot_id}"),
        types.InlineKeyboardButton("🗑 DELETE", callback_data=f"delete_{bot_id}")
    )
    
    return markup

# ==================== HELPER FUNCTIONS ====================
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
    return "▓" * filled + "░" * (length - filled)

# ==================== MESSAGE HANDLERS ====================
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    username = message.from_user.username or "User"
    
    user = db.get_user(user_id)
    if not user:
        referral_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        cursor = db.conn.cursor()
        expiry = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                      (user_id, username, datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                       expiry, 100, 5, 0, referral_code))
        db.conn.commit()
        user = db.get_user(user_id)
    
    stats = get_system_stats()
    
    text = f"""
╔══════════════════════════════╗
║  {Config.BRAND_NAME} v{Config.VERSION}  ║
╠══════════════════════════════╣
║ 👤 <b>USER:</b> @{username}          
║ 💎 <b>STATUS:</b> {'VIP' if user[6] else 'FREE'}              
║ 💰 <b>CREDITS:</b> {user[4]}                 
║ 📦 <b>BOTS LIMIT:</b> {user[5]}                
╠══════════════════════════════╣
║ 🖥️ <b>SYSTEM</b>                   
║ CPU: {progress_bar(stats['cpu'])} {stats['cpu']:.0f}%    
║ RAM: {progress_bar(stats['ram'])} {stats['ram']:.0f}%    
║ UPTIME: {format_uptime(stats['uptime'])}    
╚══════════════════════════════╝

🎁 <b>Referral Code:</b> <code>{user[7]}</code>
Share and get 50 credits per referral!
"""
    
    bot.send_message(message.chat.id, text, reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "📤 UPLOAD BOT")
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
                    f"✅ Bot '{bot_name}' saved!\n\nUse '⚡ DEPLOY BOT' to start it.",
                    reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "🤖 MY BOTS")
def my_bots(message):
    user_id = message.from_user.id
    bots = db.get_user_bots(user_id)
    
    if not bots:
        bot.reply_to(message, "🤖 No bots found!\nUse 'UPLOAD BOT' to create one.")
        return
    
    text = "╔══════════════════════════════╗\n║        🤖 MY BOTS          ║\n╠══════════════════════════════╣\n"
    
    for i, b in enumerate(bots[:10], 1):
        status_icon = "🟢" if b[5] == "Running" else "🔴"
        text += f"║ {i}. {status_icon} <b>{b[2]}</b>\n"
        text += f"║    Status: {b[5]}\n"
        if b[7]:
            text += f"║    Deploys: {b[7]}\n"
        text += "╠──────────────────────────────╣\n"
    
    text += "╚══════════════════════════════╝\n\nSelect a bot:"
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b in bots:
        markup.add(types.InlineKeyboardButton(
            f"{b[2]} - {b[5]}", callback_data=f"manage_{b[0]}"
        ))
    
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "⚡ DEPLOY BOT")
def deploy_bot(message):
    user_id = message.from_user.id
    bots = db.get_user_bots(user_id)
    available = [b for b in bots if b[5] != "Running"]
    
    if not available:
        bot.reply_to(message, "📭 No bots available for deployment!")
        return
    
    text = "╔══════════════════════════════╗\n║       ⚡ DEPLOY BOT        ║\n╠══════════════════════════════╣\n"
    for i, b in enumerate(available, 1):
        text += f"║ {i}. <b>{b[2]}</b>\n"
        text += f"║    File: {b[3]}\n"
        text += "╠──────────────────────────────╣\n"
    
    text += "╚══════════════════════════════╝\n\nEnter number to deploy:"
    
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
        
        cursor = db.conn.cursor()
        cursor.execute("UPDATE bots SET pid=?, status='Running', start_time=?, deploy_count=deploy_count+1 WHERE id=?",
                      (proc.pid, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), bot_id))
        db.conn.commit()
        
        bot.reply_to(message, f"✅ <b>{bot_name}</b> is RUNNING!\nPID: <code>{proc.pid}</code>")
        
    except:
        bot.reply_to(message, "❌ Invalid selection!")

@bot.message_handler(func=lambda m: m.text == "🎨 TEMPLATES")
def templates_menu(message):
    cursor = db.conn.cursor()
    cursor.execute("SELECT id, name, description FROM templates ORDER BY downloads DESC")
    templates = cursor.fetchall()
    
    text = "╔══════════════════════════════╗\n║       🎨 TEMPLATES        ║\n╠══════════════════════════════╣\n"
    
    for t in templates[:5]:
        text += f"║ 📦 <b>{t[1]}</b>\n"
        text += f"║    {t[2][:30]}...\n"
        text += "╠──────────────────────────────╣\n"
    
    text += "╚══════════════════════════════╝\n\nSelect a template:"
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for t in templates:
        markup.add(types.InlineKeyboardButton(f"📦 {t[1]}", callback_data=f"template_{t[0]}"))
    
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "💰 BUY CREDITS")
def buy_credits(message):
    text = """
╔══════════════════════════════╗
║      💰 BUY CREDITS         ║
╠══════════════════════════════╣
║ 💎 100 CREDITS  →  $4.99    ║
║ 💎 500 CREDITS  →  $19.99   ║
║ 💎 1000 CREDITS →  $34.99   ║
║ 👑 UNLIMITED   →  $99.99    ║
╠══════════════════════════════╣
║ ✨ FEATURES:                 ║
║ ✓ Deploy unlimited bots     ║
║ ✓ Priority support          ║
║ ✓ Advanced templates        ║
║ ✓ 24/7 uptime              ║
╚══════════════════════════════╝

Contact @aurponmodz to purchase!
"""
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: m.text == "📊 DASHBOARD")
def dashboard(message):
    user = db.get_user(message.from_user.id)
    bots = db.get_user_bots(message.from_user.id)
    stats = get_system_stats()
    
    running = len([b for b in bots if b[5] == "Running"])
    
    text = f"""
╔══════════════════════════════╗
║        📊 DASHBOARD         ║
╠══════════════════════════════╣
║ 👤 ACCOUNT                   ║
║ ├ Status: {'VIP' if user[6] else 'FREE'}                
║ ├ Credits: {user[4]}                 
║ ├ Bots: {len(bots)}/{user[5]}              
║ └ Running: {running}                  
╠══════════════════════════════╣
║ 🖥️ SERVER                    ║
║ ├ CPU: {stats['cpu']:.1f}%                 
║ ├ RAM: {stats['ram']:.1f}%                 
║ ├ Disk: {stats['disk']:.1f}%                
║ └ Uptime: {format_uptime(stats['uptime'])}    
╠══════════════════════════════╣
║ 🎁 REFERRAL                  ║
║ └ Code: <code>{user[7]}</code>           
╚══════════════════════════════╝
"""
    
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: m.text == "❓ HELP")
def help_command(message):
    text = """
╔══════════════════════════════╗
║         ❓ HELP             ║
╠══════════════════════════════╣
║ 📤 UPLOAD BOT                ║
║   Upload your Python bot    ║
║                             ║
║ 🤖 MY BOTS                   ║
║   View and manage bots      ║
║                             ║
║ ⚡ DEPLOY BOT                ║
║   Start your bot            ║
║                             ║
║ 🎨 TEMPLATES                 ║
║   Use ready templates       ║
║                             ║
║ 💰 BUY CREDITS               ║
║   Purchase more credits     ║
║                             ║
║ 📊 DASHBOARD                 ║
║   View statistics           ║
╚══════════════════════════════╝

💬 Support: {Config.SUPPORT_ID}
📢 Channel: {Config.BOT_USERNAME}
"""
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: m.text == "ℹ️ ABOUT")
def about_command(message):
    text = f"""
╔══════════════════════════════╗
║        ℹ️ ABOUT             ║
╠══════════════════════════════╣
║ {Config.BRAND_NAME}             ║
║ Version: {Config.VERSION}                ║
╠══════════════════════════════╣
║ ✨ FEATURES:                 ║
║ ✓ Easy bot deployment       ║
║ ✓ AI bot generator          ║
║ ✓ Template library          ║
║ ✓ Real-time monitoring      ║
║ ✓ Referral system           ║
╠══════════════════════════════╣
║ 👨‍💻 Developer: aurponmodz     ║
║ 💬 Support: {Config.SUPPORT_ID}    ║
╚══════════════════════════════╝
"""
    bot.send_message(message.chat.id, text)

# ==================== CALLBACK HANDLERS ====================
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    action = call.data
    
    if action.startswith("manage_"):
        bot_id = int(action.split('_')[1])
        show_bot_details(call, bot_id)
    
    elif action.startswith("start_"):
        bot_id = int(action.split('_')[1])
        start_bot(call, bot_id)
    
    elif action.startswith("stop_"):
        bot_id = int(action.split('_')[1])
        stop_bot(call, bot_id)
    
    elif action.startswith("restart_"):
        bot_id = int(action.split('_')[1])
        restart_bot(call, bot_id)
    
    elif action.startswith("stats_"):
        bot_id = int(action.split('_')[1])
        show_stats(call, bot_id)
    
    elif action.startswith("export_"):
        bot_id = int(action.split('_')[1])
        export_bot(call, bot_id)
    
    elif action.startswith("delete_"):
        bot_id = int(action.split('_')[1])
        delete_bot(call, bot_id)
    
    elif action.startswith("template_"):
        template_id = int(action.split('_')[1])
        use_template(call, template_id)
    
    bot.answer_callback_query(call.id)

def show_bot_details(call, bot_id):
    cursor = db.conn.cursor()
    cursor.execute("SELECT id, bot_name, filename, status, start_time, deploy_count FROM bots WHERE id=?", (bot_id,))
    bot_data = cursor.fetchone()
    
    if not bot_data:
        return
    
    uptime = "N/A"
    if bot_data[3] == "Running" and bot_data[4]:
        try:
            start = datetime.strptime(bot_data[4], '%Y-%m-%d %H:%M:%S')
            uptime = str(datetime.now() - start).split('.')[0]
        except:
            pass
    
    text = f"""
╔══════════════════════════════╗
║      🤖 BOT DETAILS         ║
╠══════════════════════════════╣
║ Name: {bot_data[1]}                
║ File: {bot_data[2]}                
║ Status: {'🟢 RUNNING' if bot_data[3] == 'Running' else '🔴 STOPPED'}          
║ Uptime: {uptime}                  
║ Deploys: {bot_data[5]}                 
╚══════════════════════════════╝
"""
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                         reply_markup=bot_controls(bot_id, bot_data[3]))

def start_bot(call, bot_id):
    cursor = db.conn.cursor()
    cursor.execute("SELECT user_id, bot_name, filename FROM bots WHERE id=?", (bot_id,))
    bot_data = cursor.fetchone()
    
    if not bot_data or bot_data[0] != call.from_user.id:
        return
    
    file_path = Path(Config.PROJECT_DIR) / bot_data[2]
    if not file_path.exists():
        bot.answer_callback_query(call.id, "File not found!")
        return
    
    proc = subprocess.Popen(['python', str(file_path)], 
                           start_new_session=True,
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)
    
    cursor.execute("UPDATE bots SET pid=?, status='Running', start_time=? WHERE id=?",
                  (proc.pid, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), bot_id))
    db.conn.commit()
    
    bot.answer_callback_query(call.id, f"✅ {bot_data[1]} started!")
    show_bot_details(call, bot_id)

def stop_bot(call, bot_id):
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
    show_bot_details(call, bot_id)

def restart_bot(call, bot_id):
    stop_bot(call, bot_id)
    time.sleep(1)
    start_bot(call, bot_id)

def show_stats(call, bot_id):
    cursor = db.conn.cursor()
    cursor.execute("SELECT pid, bot_name, status FROM bots WHERE id=?", (bot_id,))
    bot_data = cursor.fetchone()
    
    if not bot_data or bot_data[2] != "Running":
        bot.answer_callback_query(call.id, "Bot is not running!")
        return
    
    try:
        proc = psutil.Process(bot_data[0])
        cpu = proc.cpu_percent(interval=0.5)
        mem = proc.memory_percent()
        
        text = f"""
╔══════════════════════════════╗
║      📊 BOT STATS           ║
╠══════════════════════════════╣
║ Name: {bot_data[1]}                
║ PID: {bot_data[0]}                   
║ CPU: {progress_bar(cpu)} {cpu:.1f}%    
║ RAM: {progress_bar(mem)} {mem:.1f}%    
║ Threads: {proc.num_threads()}               
╚══════════════════════════════╝
"""
        bot.send_message(call.message.chat.id, text)
        
    except Exception as e:
        bot.answer_callback_query(call.id, f"Error: {str(e)[:50]}")

def export_bot(call, bot_id):
    cursor = db.conn.cursor()
    cursor.execute("SELECT bot_name, filename FROM bots WHERE id=?", (bot_id,))
    bot_data = cursor.fetchone()
    
    if not bot_data:
        return
    
    file_path = Path(Config.PROJECT_DIR) / bot_data[1]
    if file_path.exists():
        with open(file_path, 'rb') as f:
            bot.send_document(call.message.chat.id, f, 
                            caption=f"📦 Exported: {bot_data[0]}")
        bot.answer_callback_query(call.id, "Bot exported!")
    else:
        bot.answer_callback_query(call.id, "File not found!")

def delete_bot(call, bot_id):
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
    
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass
    
    bot.send_message(call.message.chat.id, f"✅ Bot '{bot_data[1]}' deleted.")

def use_template(call, template_id):
    cursor = db.conn.cursor()
    cursor.execute("SELECT name, code FROM templates WHERE id=?", (template_id,))
    template = cursor.fetchone()
    
    if not template:
        return
    
    cursor.execute("UPDATE templates SET downloads=downloads+1 WHERE id=?", (template_id,))
    db.conn.commit()
    
    filename = f"template_{uuid.uuid4().hex[:8]}.py"
    file_path = Path(Config.PROJECT_DIR) / filename
    file_path.write_text(template[1])
    
    cursor.execute("INSERT INTO bots (user_id, bot_name, filename, status) VALUES (?, ?, ?, ?)",
                  (call.from_user.id, f"Template: {template[0]}", filename, "Uploaded"))
    db.conn.commit()
    
    bot.answer_callback_query(call.id, f"✅ Template '{template[0]}' added!")
    bot.send_message(call.message.chat.id, 
                    f"✅ Template '{template[0]}' saved!\n\nUse 'DEPLOY BOT' to start it.",
                    reply_markup=main_menu())

# ==================== FLASK ROUTES ====================
@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "brand": Config.BRAND_NAME,
        "version": Config.VERSION,
        "timestamp": datetime.now().isoformat()
    })

@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

# ==================== BACKGROUND TASKS ====================
def cleanup_processes():
    """Clean up orphaned processes"""
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
    """Run Telegram bot with proper error handling"""
    logger.info(f"Starting {Config.BRAND_NAME} v{Config.VERSION}")
    
    # Remove webhook first (important for polling)
    try:
        bot.remove_webhook()
        logger.info("Webhook removed successfully")
    except Exception as e:
        logger.error(f"Failed to remove webhook: {e}")
    
    time.sleep(2)  # Wait for webhook removal
    
    # Start polling with error handling
    while True:
        try:
            logger.info("Starting bot polling...")
            bot.infinity_polling(timeout=30, long_polling_timeout=30)
        except Exception as e:
            logger.error(f"Bot polling error: {e}")
            logger.info("Restarting polling in 10 seconds...")
            time.sleep(10)

if __name__ == '__main__':
    # Start cleanup thread
    cleanup_thread = threading.Thread(target=cleanup_processes, daemon=True)
    cleanup_thread.start()
    logger.info("Cleanup thread started")
    
    # Start bot thread
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    logger.info("Bot thread started")
    
    # Start Flask server
    logger.info(f"Starting Flask server on port {Config.PORT}")
    app.run(host='0.0.0.0', port=Config.PORT, debug=False)    # Paths
    PROJECT_DIR = 'projects'
    DB_NAME = 'aurpon_bot.db'
    LOGS_DIR = 'logs'
    BACKUP_DIR = 'backups'
    TEMP_DIR = 'temp'
    
    # Branding
    BRAND_NAME = "𝐀𝐔𝐑𝐏𝐎𝐍 𝐃𝐄𝐗"
    BRAND_EMOJI = "💎"
    VERSION = "5.0.0"
    SUPPORT_ID = "@aurponmodz"
    BOT_USERNAME = "@aurpon_bot_host_bot"
    
    # Limits
    MAX_FILE_SIZE = 50 * 1024 * 1024
    MAX_BOTS_PER_USER = 50
    FREE_TRIAL_DAYS = 7
    
    # Colors & Themes
    PRIMARY_COLOR = "#00ff00"
    SECONDARY_COLOR = "#ff00ff"
    BG_COLOR = "#000000"
    TEXT_COLOR = "#ffffff"
    
    # Create directories
    for dir_path in [PROJECT_DIR, LOGS_DIR, BACKUP_DIR, TEMP_DIR]:
        Path(dir_path).mkdir(exist_ok=True)

# ==================== DATABASE MANAGER ====================
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
            full_name TEXT,
            join_date TEXT,
            expiry_date TEXT,
            credits INTEGER DEFAULT 100,
            bots_limit INTEGER DEFAULT 5,
            is_vip INTEGER DEFAULT 0,
            referred_by INTEGER,
            referral_code TEXT,
            total_referrals INTEGER DEFAULT 0,
            last_active TEXT,
            banned INTEGER DEFAULT 0
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
            last_active TEXT,
            cpu_usage REAL,
            ram_usage REAL,
            deploy_count INTEGER DEFAULT 0,
            error_log TEXT,
            auto_restart INTEGER DEFAULT 0
        )''')
        
        # Transactions table
        cursor.execute('''CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            type TEXT,
            status TEXT,
            transaction_id TEXT,
            created_at TEXT
        )''')
        
        # Templates table
        cursor.execute('''CREATE TABLE IF NOT EXISTS templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            description TEXT,
            code TEXT,
            category TEXT,
            downloads INTEGER DEFAULT 0,
            created_by INTEGER
        )''')
        
        # Add default templates
        self.add_default_templates()
        
        # Add admin user
        admin_expiry = (datetime.now() + timedelta(days=3650)).strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("INSERT OR IGNORE INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                      (Config.ADMIN_ID, 'admin', 'Administrator', 
                       datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                       admin_expiry, 999999, 999, 1, None, 'ADMIN', 0,
                       datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 0))
        
        self.conn.commit()
    
    def add_default_templates(self):
        cursor = self.conn.cursor()
        
        templates = [
            ("Echo Bot", "Simple echo bot that replies with the same message", 
             '''import telebot
TOKEN = "YOUR_BOT_TOKEN"
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(func=lambda m: True)
def echo(message):
    bot.reply_to(message, message.text)

bot.infinity_polling()''', "basic", 0, Config.ADMIN_ID),
            
            ("Weather Bot", "Get weather information for any city",
             '''import telebot
import requests
TOKEN = "YOUR_BOT_TOKEN"
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['weather'])
def weather(message):
    city = message.text.replace('/weather', '').strip()
    if city:
        api_key = "YOUR_API_KEY"
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
        response = requests.get(url).json()
        temp = response['main']['temp']
        bot.reply_to(message, f"Weather in {city}: {temp}°C")
    else:
        bot.reply_to(message, "Usage: /weather <city>")

bot.infinity_polling()''', "utility", 0, Config.ADMIN_ID),
            
            ("Calculator Bot", "Perform mathematical calculations",
             '''import telebot
import re
TOKEN = "YOUR_BOT_TOKEN"
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(func=lambda m: True)
def calculate(message):
    try:
        result = eval(message.text)
        bot.reply_to(message, f"Result: {result}")
    except:
        bot.reply_to(message, "Invalid expression!")

bot.infinity_polling()''', "utility", 0, Config.ADMIN_ID)
        ]
        
        for template in templates:
            cursor.execute("INSERT OR IGNORE INTO templates (name, description, code, category, downloads, created_by) VALUES (?, ?, ?, ?, ?, ?)",
                          template)
        
        self.conn.commit()
    
    def get_user(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id=?", (user_id,))
        return cursor.fetchone()
    
    def update_user_activity(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE users SET last_active=? WHERE id=?", 
                      (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), user_id))
        self.conn.commit()
    
    def add_credits(self, user_id, amount):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE users SET credits=credits+? WHERE id=?", (amount, user_id))
        self.conn.commit()
    
    def get_user_bots(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM bots WHERE user_id=? ORDER BY id DESC", (user_id,))
        return cursor.fetchall()
    
    def log_transaction(self, user_id, amount, type, status, transaction_id=None):
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO transactions (user_id, amount, type, status, transaction_id, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                      (user_id, amount, type, status, transaction_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        self.conn.commit()

db = DatabaseManager()

# ==================== BOT INITIALIZATION ====================
bot = telebot.TeleBot(Config.TOKEN, parse_mode="HTML")
app = Flask(__name__)

# ==================== ADVANCED KEYBOARDS ====================
class Keyboards:
    @staticmethod
    def main_menu():
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        buttons = [
            "🤖 CREATE BOT", "📁 MY BOTS",
            "⚡ DEPLOY", "💰 BUY CREDITS",
            "📊 DASHBOARD", "🎨 TEMPLATES",
            "🔧 SETTINGS", "❓ HELP"
        ]
        markup.add(*[types.KeyboardButton(btn) for btn in buttons])
        return markup
    
    @staticmethod
    def admin_menu():
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        buttons = [
            "👥 USERS", "📊 STATS",
            "🔑 GENERATE KEY", "📢 BROADCAST",
            "💾 BACKUP", "⚙️ SETTINGS",
            "🏠 BACK"
        ]
        markup.add(*[types.KeyboardButton(btn) for btn in buttons])
        return markup
    
    @staticmethod
    def bot_controls(bot_id, status):
        markup = types.InlineKeyboardMarkup(row_width=2)
        
        if status == "Running":
            markup.add(
                types.InlineKeyboardButton("⏸ STOP", callback_data=f"stop_{bot_id}"),
                types.InlineKeyboardButton("🔄 RESTART", callback_data=f"restart_{bot_id}")
            )
        else:
            markup.add(
                types.InlineKeyboardButton("▶️ START", callback_data=f"start_{bot_id}"),
                types.InlineKeyboardButton("⚙️ CONFIG", callback_data=f"config_{bot_id}")
            )
        
        markup.add(
            types.InlineKeyboardButton("📊 STATS", callback_data=f"stats_{bot_id}"),
            types.InlineKeyboardButton("📦 EXPORT", callback_data=f"export_{bot_id}"),
            types.InlineKeyboardButton("🗑 DELETE", callback_data=f"delete_{bot_id}"),
            types.InlineKeyboardButton("📝 LOGS", callback_data=f"logs_{bot_id}")
        )
        
        return markup
    
    @staticmethod
    def payment_plans():
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("💎 100 CREDITS - $4.99", callback_data="buy_100"),
            types.InlineKeyboardButton("💎 500 CREDITS - $19.99", callback_data="buy_500"),
            types.InlineKeyboardButton("👑 1000 CREDITS - $34.99", callback_data="buy_1000"),
            types.InlineKeyboardButton("🌟 UNLIMITED - $99.99", callback_data="buy_unlimited")
        )
        return markup

# ==================== ANIMATED MESSAGES ====================
class Animations:
    @staticmethod
    def loading_animation():
        frames = ["◐", "◓", "◑", "◒"]
        return frames
    
    @staticmethod
    def progress_bar(percent, length=20):
        filled = int(length * percent / 100)
        bar = "▓" * filled + "░" * (length - filled)
        return bar

# ==================== COMMAND HANDLERS ====================
@bot.message_handler(commands=['start', 'menu'])
def start_command(message):
    user_id = message.from_user.id
    username = message.from_user.username or "User"
    full_name = message.from_user.first_name or "User"
    
    # Check if user exists
    user = db.get_user(user_id)
    if not user:
        # Generate referral code
        referral_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        
        # Create new user
        cursor = db.conn.cursor()
        expiry = (datetime.now() + timedelta(days=Config.FREE_TRIAL_DAYS)).strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("INSERT INTO users (id, username, full_name, join_date, expiry_date, credits, bots_limit, referral_code) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                      (user_id, username, full_name, datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                       expiry, 100, 5, referral_code))
        db.conn.commit()
        user = db.get_user(user_id)
        
        # Check if referred
        if 'start' in message.text and '_' in message.text:
            try:
                ref_code = message.text.split('_')[1]
                cursor.execute("SELECT id FROM users WHERE referral_code=?", (ref_code,))
                ref_user = cursor.fetchone()
                if ref_user:
                    cursor.execute("UPDATE users SET credits=credits+50, total_referrals=total_referrals+1 WHERE id=?", (ref_user[0],))
                    cursor.execute("UPDATE users SET credits=credits+25 WHERE id=?", (user_id,))
                    db.conn.commit()
                    bot.send_message(user_id, "🎉 You got 25 free credits from referral!")
            except:
                pass
    
    db.update_user_activity(user_id)
    
    # Get system stats
    stats = get_system_stats()
    
    # Welcome message with animation
    welcome_text = f"""
{Config.BRAND_EMOJI} <b>{Config.BRAND_NAME}</b> {Config.BRAND_EMOJI}
╔══════════════════════════════╗
║  <b>WELCOME BACK!</b>            ║
╚══════════════════════════════╝

👤 <b>USER INFO</b>
├ ID: <code>{user_id}</code>
├ Name: @{username}
├ Status: {'👑 VIP' if user[6] else '⭐ FREE'}
├ Credits: {user[4]} 💎
└ Bots Limit: {user[5]}

📊 <b>SYSTEM STATUS</b>
├ CPU: {Animations.progress_bar(stats['cpu'])} {stats['cpu']:.0f}%
├ RAM: {Animations.progress_bar(stats['ram'])} {stats['ram']:.0f}%
└ UPTIME: {format_uptime(stats['uptime'])}

🎁 <b>REFERRAL BONUS</b>
Share your referral code: <code>{user[9]}</code>
Each referral gives you 50 credits!

💡 <i>Use the buttons below to get started!</i>
"""
    
    bot.send_message(message.chat.id, welcome_text, reply_markup=Keyboards.main_menu())

@bot.message_handler(func=lambda m: m.text == "🤖 CREATE BOT")
def create_bot_menu(message):
    text = """
🤖 <b>CREATE NEW BOT</b>
╔══════════════════════════════╗
║  Choose how to create your   ║
║  bot:                        ║
╚══════════════════════════════╝

📤 <b>Upload File</b>
- Send your .py file
- Max size: 50MB

🎨 <b>Use Template</b>
- Choose from templates
- Quick setup

🤖 <b>AI Generate</b>
- Describe your bot
- AI creates it

⚡ <b>Quick Deploy</b>
- Deploy existing bot
"""
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📤 UPLOAD FILE", callback_data="upload_file"),
        types.InlineKeyboardButton("🎨 USE TEMPLATE", callback_data="use_template"),
        types.InlineKeyboardButton("🤖 AI GENERATE", callback_data="ai_generate"),
        types.InlineKeyboardButton("⚡ QUICK DEPLOY", callback_data="quick_deploy")
    )
    
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "📁 MY BOTS")
def my_bots_menu(message):
    user_id = message.from_user.id
    bots = db.get_user_bots(user_id)
    
    if not bots:
        text = """
🤖 <b>NO BOTS FOUND</b>
╔══════════════════════════════╗
║  You haven't created any     ║
║  bots yet!                   ║
╚══════════════════════════════╝

Use 'CREATE BOT' to get started!
"""
        bot.send_message(message.chat.id, text)
        return
    
    text = f"""
🤖 <b>YOUR BOTS</b> ({len(bots)})
╔══════════════════════════════╗
"""
    
    for i, bot_data in enumerate(bots[:5], 1):
        status_icon = "🟢" if bot_data[5] == "Running" else "🔴"
        text += f"║ {i}. {status_icon} <b>{bot_data[2]}</b>\n"
        if bot_data[7]:
            text += f"║    Last active: {bot_data[7][:10]}\n"
    
    if len(bots) > 5:
        text += f"║ ... and {len(bots)-5} more\n"
    
    text += "╚══════════════════════════════╝\n\nSelect a bot to manage:"
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for bot_data in bots:
        markup.add(types.InlineKeyboardButton(
            f"{bot_data[2]} - {bot_data[5]}",
            callback_data=f"manage_{bot_data[0]}"
        ))
    
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "⚡ DEPLOY")
def deploy_menu(message):
    user_id = message.from_user.id
    bots = db.get_user_bots(user_id)
    available = [b for b in bots if b[5] != "Running"]
    
    if not available:
        bot.reply_to(message, "📭 No bots available for deployment!\nCreate a bot first.")
        return
    
    text = "⚡ <b>DEPLOY BOT</b>\n╔══════════════════════════════╗\n"
    for i, b in enumerate(available, 1):
        text += f"║ {i}. <b>{b[2]}</b>\n"
        text += f"║    File: {b[3]}\n"
        text += f"║    Status: {b[5]}\n\n"
    
    text += "╚══════════════════════════════╝\n\nSelect bot number to deploy:"
    
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
        
        # Send loading animation
        msg = bot.reply_to(message, "🚀 Deploying bot... ◐")
        
        # Start the bot
        proc = subprocess.Popen(['python', str(file_path)], 
                               start_new_session=True,
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
        
        cursor = db.conn.cursor()
        cursor.execute("UPDATE bots SET pid=?, status='Running', start_time=?, deploy_count=deploy_count+1 WHERE id=?",
                      (proc.pid, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), bot_id))
        db.conn.commit()
        
        # Update message
        bot.edit_message_text(f"✅ <b>{bot_name}</b> is now RUNNING!\nPID: <code>{proc.pid}</code>\n\nUse 'MY BOTS' to manage it.",
                             message.chat.id, msg.message_id)
        
    except:
        bot.reply_to(message, "❌ Invalid selection!")

@bot.message_handler(func=lambda m: m.text == "💰 BUY CREDITS")
def buy_credits_menu(message):
    user = db.get_user(message.from_user.id)
    
    text = f"""
💰 <b>BUY CREDITS</b>
╔══════════════════════════════╗
║  Current Credits: {user[4]} 💎  ║
╚══════════════════════════════╝

<b>💎 PREMIUM PLANS</b>
┌──────────────────────────────┐
│ 100 CREDITS  →  $4.99        │
│ 500 CREDITS  →  $19.99       │
│ 1000 CREDITS →  $34.99       │
│ UNLIMITED    →  $99.99       │
└──────────────────────────────┘

<b>✨ FEATURES</b>
✓ Deploy unlimited bots
✓ Priority support
✓ Advanced templates
✓ AI assistant access
✓ 24/7 uptime

Select a plan below:
"""
    
    bot.send_message(message.chat.id, text, reply_markup=Keyboards.payment_plans())

@bot.message_handler(func=lambda m: m.text == "📊 DASHBOARD")
def dashboard_menu(message):
    user_id = message.from_user.id
    user = db.get_user(user_id)
    bots = db.get_user_bots(user_id)
    stats = get_system_stats()
    
    running = len([b for b in bots if b[5] == "Running"])
    
    text = f"""
📊 <b>DASHBOARD</b>
╔══════════════════════════════╗

<b>👤 ACCOUNT INFO</b>
├ Username: @{user[1]}
├ Status: {'👑 VIP' if user[6] else '⭐ FREE'}
├ Credits: {user[4]} 💎
├ Bots Limit: {user[5]}
├ Bots Used: {len(bots)}/{user[5]}
└ Running: {running}

<b>💰 FINANCIAL</b>
├ Total Spent: $0.00
├ Referrals: {user[10]}
└ Referral Code: <code>{user[9]}</code>

<b>🖥️ SERVER</b>
├ CPU: {stats['cpu']:.1f}%
├ RAM: {stats['ram']:.1f}%
├ Disk: {stats['disk']:.1f}%
└ Uptime: {format_uptime(stats['uptime'])}

<b>🎯 TODAY'S STATS</b>
├ Active Users: {get_active_users()}
├ Total Deploys: {get_total_deploys()}
└ System Load: {stats['cpu']:.0f}%

╚══════════════════════════════╝
"""
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📈 DETAILED STATS", callback_data="detailed_stats"),
        types.InlineKeyboardButton("💰 TOP UP", callback_data="top_up"),
        types.InlineKeyboardButton("📜 TRANSACTIONS", callback_data="transactions"),
        types.InlineKeyboardButton("🎁 REFERRAL", callback_data="referral")
    )
    
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🎨 TEMPLATES")
def templates_menu(message):
    cursor = db.conn.cursor()
    cursor.execute("SELECT id, name, description, category, downloads FROM templates ORDER BY downloads DESC LIMIT 10")
    templates = cursor.fetchall()
    
    text = f"""
🎨 <b>BOT TEMPLATES</b>
╔══════════════════════════════╗
║  Choose a template to start  ║
║  building your bot quickly!  ║
╚══════════════════════════════╝

"""
    
    for t in templates:
        text += f"""
<b>{t[1]}</b> [{t[3]}]
├ {t[2][:50]}...
└ 📥 {t[4]} downloads

"""
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for t in templates:
        markup.add(types.InlineKeyboardButton(f"📦 {t[1]}", callback_data=f"template_{t[0]}"))
    
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🔧 SETTINGS")
def settings_menu(message):
    user = db.get_user(message.from_user.id)
    
    text = f"""
⚙️ <b>SETTINGS</b>
╔══════════════════════════════╗

<b>🔐 ACCOUNT</b>
├ Auto Restart: {'ON' if user[12] else 'OFF'}
├ Notifications: ON
└ Theme: Dark

<b>🤖 BOT SETTINGS</b>
├ Default Timeout: 60s
├ Max Memory: 512MB
└ Auto Cleanup: ON

<b>🔔 NOTIFICATIONS</b>
├ Bot Events: ON
├ Credit Alerts: ON
└ System Alerts: ON

╚══════════════════════════════╝
"""
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🔐 AUTO RESTART", callback_data="toggle_autorestart"),
        types.InlineKeyboardButton("🔔 NOTIFICATIONS", callback_data="toggle_notifications"),
        types.InlineKeyboardButton("🎨 THEME", callback_data="change_theme"),
        types.InlineKeyboardButton("🗑 CLEAR DATA", callback_data="clear_data")
    )
    
    bot.send_message(message.chat.id, text, reply_markup=markup)

# ==================== CALLBACK HANDLERS ====================
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    action = call.data
    
    if action == "upload_file":
        msg = bot.send_message(call.message.chat.id, "📤 Send your Python bot file (.py)\nMax size: 50MB")
        bot.register_next_step_handler(msg, handle_upload)
    
    elif action == "use_template":
        templates_menu(call.message)
    
    elif action == "ai_generate":
        msg = bot.send_message(call.message.chat.id, "🤖 Describe the bot you want to create:\n\nExample: 'Create a weather bot that shows temperature'")
        bot.register_next_step_handler(msg, handle_ai_generate)
    
    elif action == "quick_deploy":
        deploy_menu(call.message)
    
    elif action.startswith("manage_"):
        bot_id = int(action.split('_')[1])
        show_bot_details(call.message, bot_id)
    
    elif action.startswith("start_"):
        bot_id = int(action.split('_')[1])
        start_bot_process(call, bot_id)
    
    elif action.startswith("stop_"):
        bot_id = int(action.split('_')[1])
        stop_bot_process(call, bot_id)
    
    elif action.startswith("restart_"):
        bot_id = int(action.split('_')[1])
        restart_bot_process(call, bot_id)
    
    elif action.startswith("stats_"):
        bot_id = int(action.split('_')[1])
        show_bot_stats(call, bot_id)
    
    elif action.startswith("export_"):
        bot_id = int(action.split('_')[1])
        export_bot(call, bot_id)
    
    elif action.startswith("delete_"):
        bot_id = int(action.split('_')[1])
        delete_bot(call, bot_id)
    
    elif action.startswith("template_"):
        template_id = int(action.split('_')[1])
        use_template(call, template_id)
    
    elif action.startswith("buy_"):
        credits = int(action.split('_')[1])
        process_payment(call, credits)
    
    elif action == "detailed_stats":
        show_detailed_stats(call)
    
    elif action == "referral":
        show_referral_info(call)
    
    bot.answer_callback_query(call.id)

# ==================== HELPER FUNCTIONS ====================
def handle_upload(message):
    if not message.document:
        bot.reply_to(message, "❌ Please send a file!")
        return
    
    file_name = message.document.file_name
    if not file_name.endswith('.py'):
        bot.reply_to(message, "❌ Only .py files are allowed!")
        return
    
    if message.document.file_size > Config.MAX_FILE_SIZE:
        bot.reply_to(message, f"❌ File too large! Max {Config.MAX_FILE_SIZE//(1024*1024)}MB")
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
    db.conn.commit()
    
    bot.send_message(message.chat.id, 
                    f"✅ Bot '{bot_name}' saved!\n\nUse '⚡ DEPLOY' to start it.",
                    reply_markup=Keyboards.main_menu())

def handle_ai_generate(message):
    description = message.text
    
    # AI-generated bot code template
    code = f'''
import telebot
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = "YOUR_BOT_TOKEN"
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# Bot description: {description}
# Generated by Aurpon Bot Host

@bot.message_handler(commands=['start'])
def start(message):
    welcome_text = """
✨ <b>Welcome to AI Generated Bot!</b> ✨

{description}

Use /help for available commands.
"""
    bot.reply_to(message, welcome_text)

@bot.message_handler(commands=['help'])
def help_command(message):
    help_text = """
<b>Available Commands:</b>
/start - Start the bot
/help - Show this help
/about - About this bot
"""
    bot.reply_to(message, help_text)

@bot.message_handler(commands=['about'])
def about(message):
    about_text = """
<b>About This Bot</b>
Generated by Aurpon Bot Host AI
Version: 1.0.0
"""
    bot.reply_to(message, about_text)

@bot.message_handler(func=lambda m: True)
def echo(message):
    bot.reply_to(message, message.text)

if __name__ == '__main__':
    print("Bot started!")
    bot.infinity_polling()
'''
    
    # Save generated code
    filename = f"ai_{uuid.uuid4().hex[:8]}.py"
    file_path = Path(Config.PROJECT_DIR) / filename
    file_path.write_text(code)
    
    # Save to database
    cursor = db.conn.cursor()
    cursor.execute("INSERT INTO bots (user_id, bot_name, filename, status) VALUES (?, ?, ?, ?)",
                  (message.from_user.id, f"AI Bot {datetime.now().strftime('%H:%M')}", filename, "Uploaded"))
    db.conn.commit()
    
    bot.send_document(message.chat.id, open(file_path, 'rb'),
                     caption=f"✅ AI Bot Generated!\n\nUse '⚡ DEPLOY' to start it.")

def show_bot_details(message, bot_id):
    cursor = db.conn.cursor()
    cursor.execute("SELECT id, bot_name, filename, status, start_time, deploy_count FROM bots WHERE id=?", (bot_id,))
    bot_data = cursor.fetchone()
    
    if not bot_data:
        return
    
    uptime = "N/A"
    if bot_data[3] == "Running" and bot_data[4]:
        try:
            start = datetime.strptime(bot_data[4], '%Y-%m-%d %H:%M:%S')
            uptime = str(datetime.now() - start).split('.')[0]
        except:
            pass
    
    text = f"""
<b>🤖 BOT DETAILS</b>
╔══════════════════════════════╗

<b>Name:</b> {bot_data[1]}
<b>File:</b> <code>{bot_data[2]}</code>
<b>Status:</b> {'🟢 RUNNING' if bot_data[3] == 'Running' else '🔴 STOPPED'}
<b>Started:</b> {bot_data[4] or 'Never'}
<b>Uptime:</b> {uptime}
<b>Deploys:</b> {bot_data[5]}

╚══════════════════════════════╝
"""
    
    bot.edit_message_text(text, message.chat.id, message.message_id,
                         reply_markup=Keyboards.bot_controls(bot_id, bot_data[3]))

def start_bot_process(call, bot_id):
    cursor = db.conn.cursor()
    cursor.execute("SELECT user_id, bot_name, filename FROM bots WHERE id=?", (bot_id,))
    bot_data = cursor.fetchone()
    
    if not bot_data or bot_data[0] != call.from_user.id:
        return
    
    file_path = Path(Config.PROJECT_DIR) / bot_data[2]
    if not file_path.exists():
        bot.answer_callback_query(call.id, "File not found!")
        return
    
    proc = subprocess.Popen(['python', str(file_path)], 
                           start_new_session=True,
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)
    
    cursor.execute("UPDATE bots SET pid=?, status='Running', start_time=? WHERE id=?",
                  (proc.pid, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), bot_id))
    db.conn.commit()
    
    bot.answer_callback_query(call.id, f"✅ {bot_data[1]} started!")
    
    # Update message
    show_bot_details(call.message, bot_id)

def stop_bot_process(call, bot_id):
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
    show_bot_details(call.message, bot_id)

def restart_bot_process(call, bot_id):
    stop_bot_process(call, bot_id)
    time.sleep(1)
    start_bot_process(call, bot_id)

def show_bot_stats(call, bot_id):
    cursor = db.conn.cursor()
    cursor.execute("SELECT pid, bot_name, status, cpu_usage, ram_usage FROM bots WHERE id=?", (bot_id,))
    bot_data = cursor.fetchone()
    
    if not bot_data or bot_data[2] != "Running":
        bot.answer_callback_query(call.id, "Bot is not running!")
        return
    
    try:
        proc = psutil.Process(bot_data[0])
        cpu = proc.cpu_percent(interval=0.5)
        mem = proc.memory_percent()
        
        # Update database
        cursor.execute("UPDATE bots SET cpu_usage=?, ram_usage=? WHERE id=?", (cpu, mem, bot_id))
        db.conn.commit()
        
        text = f"""
📊 <b>{bot_data[1]} STATISTICS</b>
╔══════════════════════════════╗

<b>🖥️ RESOURCE USAGE</b>
├ CPU: {Animations.progress_bar(cpu)} {cpu:.1f}%
├ RAM: {Animations.progress_bar(mem)} {mem:.1f}%
├ PID: <code>{bot_data[0]}</code>
└ Status: 🟢 RUNNING

<b>📈 PERFORMANCE</b>
├ Threads: {proc.num_threads()}
├ Open Files: {proc.num_fds() if hasattr(proc, 'num_fds') else 'N/A'}
└ Memory RSS: {proc.memory_info().rss / 1024 / 1024:.1f} MB

╚══════════════════════════════╝
"""
        bot.send_message(call.message.chat.id, text)
        
    except Exception as e:
        bot.answer_callback_query(call.id, f"Error: {str(e)[:50]}")

def export_bot(call, bot_id):
    cursor = db.conn.cursor()
    cursor.execute("SELECT bot_name, filename FROM bots WHERE id=?", (bot_id,))
    bot_data = cursor.fetchone()
    
    if not bot_data:
        return
    
    file_path = Path(Config.PROJECT_DIR) / bot_data[1]
    if file_path.exists():
        with open(file_path, 'rb') as f:
            bot.send_document(call.message.chat.id, f, 
                            caption=f"📦 Exported: {bot_data[0]}\n\nCreated by Aurpon Bot Host")
        bot.answer_callback_query(call.id, "Bot exported!")
    else:
        bot.answer_callback_query(call.id, "File not found!")

def delete_bot(call, bot_id):
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
    
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass
    
    bot.send_message(call.message.chat.id, f"✅ Bot '{bot_data[1]}' has been deleted.")

def use_template(call, template_id):
    cursor = db.conn.cursor()
    cursor.execute("SELECT name, code FROM templates WHERE id=?", (template_id,))
    template = cursor.fetchone()
    
    if not template:
        return
    
    # Update download count
    cursor.execute("UPDATE templates SET downloads=downloads+1 WHERE id=?", (template_id,))
    db.conn.commit()
    
    # Save template as bot
    filename = f"template_{uuid.uuid4().hex[:8]}.py"
    file_path = Path(Config.PROJECT_DIR) / filename
    file_path.write_text(template[1])
    
    cursor.execute("INSERT INTO bots (user_id, bot_name, filename, status) VALUES (?, ?, ?, ?)",
                  (call.from_user.id, f"Template: {template[0]}", filename, "Uploaded"))
    db.conn.commit()
    
    bot.answer_callback_query(call.id, f"✅ Template '{template[0]}' added!")
    bot.send_message(call.message.chat.id, 
                    f"✅ Template '{template[0]}' saved!\n\nUse '⚡ DEPLOY' to start it.",
                    reply_markup=Keyboards.main_menu())

def process_payment(call, credits):
    # Here you would integrate with payment gateway
    # For now, just add credits (demo only)
    db.add_credits(call.from_user.id, credits)
    db.log_transaction(call.from_user.id, credits, "purchase", "completed")
    
    bot.answer_callback_query(call.id, f"✅ Added {credits} credits!")
    bot.send_message(call.message.chat.id, 
                    f"✅ Payment processed!\nAdded {credits} credits to your account.\n\nThank you for your purchase!")

def show_detailed_stats(call):
    user = db.get_user(call.from_user.id)
    bots = db.get_user_bots(call.from_user.id)
    
    text = f"""
📈 <b>DETAILED STATISTICS</b>
╔══════════════════════════════╗

<b>🤖 BOT STATISTICS</b>
├ Total Bots: {len(bots)}
├ Running: {len([b for b in bots if b[5] == "Running"])}
├ Stopped: {len([b for b in bots if b[5] == "Stopped"])}
└ Total Deploys: {sum(b[11] for b in bots)}

<b>💰 CREDIT USAGE</b>
├ Current Balance: {user[4]} 💎
├ Total Spent: N/A
└ Credits Used: N/A

<b>📅 ACCOUNT AGE</b>
├ Joined: {user[2][:10]}
├ Expires: {user[3][:10] if user[3] else 'Never'}
└ Days Left: {calculate_days_left(user[3])}

╚══════════════════════════════╝
"""
    bot.send_message(call.message.chat.id, text)

def show_referral_info(call):
    user = db.get_user(call.from_user.id)
    
    text = f"""
🎁 <b>REFERRAL PROGRAM</b>
╔══════════════════════════════╗

<b>YOUR REFERRAL CODE:</b>
<code>{user[9]}</code>

<b>REFERRAL LINK:</b>
<code>https://t.me/{Config.BOT_USERNAME[1:]}?start={user[9]}</code>

<b>STATISTICS</b>
├ Total Referrals: {user[10]}
├ Credits Earned: {user[10] * 50}
└ Total Rewards: {user[10] * 50} 💎

<b>HOW IT WORKS</b>
1. Share your referral link
2. Friends join using your link
3. You get 50 credits each!
4. Friend gets 25 free credits!

╚══════════════════════════════╝
"""
    bot.send_message(call.message.chat.id, text)

def calculate_days_left(expiry):
    if not expiry:
        return "Unlimited"
    try:
        expiry_date = datetime.strptime(expiry, '%Y-%m-%d %H:%M:%S')
        days = (expiry_date - datetime.now()).days
        return f"{days} days" if days > 0 else "Expired"
    except:
        return "Unknown"

# ==================== SYSTEM FUNCTIONS ====================
def get_system_stats():
    try:
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/').percent
        uptime = time.time() - psutil.boot_time()
        return {'cpu': cpu, 'ram': ram, 'disk': disk, 'uptime': uptime}
    except:
        return {'cpu': 25, 'ram': 40, 'disk': 50, 'uptime': 86400}

def get_active_users():
    cursor = db.conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users WHERE last_active > datetime('now', '-1 day')")
    return cursor.fetchone()[0]

def get_total_deploys():
    cursor = db.conn.cursor()
    cursor.execute("SELECT SUM(deploy_count) FROM bots")
    result = cursor.fetchone()[0]
    return result or 0

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

# ==================== FLASK ROUTES ====================
@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "brand": Config.BRAND_NAME,
        "version": Config.VERSION,
        "features": [
            "Bot Hosting",
            "AI Bot Generator",
            "Template Library",
            "Real-time Monitoring",
            "Referral Program"
        ],
        "uptime": format_uptime(get_system_stats()['uptime'])
    })

@app.route('/api/stats')
def api_stats():
    cursor = db.conn.cursor()
    total_users = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_bots = cursor.execute("SELECT COUNT(*) FROM bots").fetchone()[0]
    running_bots = cursor.execute("SELECT COUNT(*) FROM bots WHERE status='Running'").fetchone()[0]
    
    return jsonify({
        "users": total_users,
        "bots": total_bots,
        "running": running_bots,
        "system": get_system_stats()
    })

@app.route('/api/user/<int:user_id>')
def api_user(user_id):
    user = db.get_user(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    return jsonify({
        "id": user[0],
        "username": user[1],
        "credits": user[4],
        "bots_limit": user[5],
        "is_vip": bool(user[6]),
        "referrals": user[10]
    })

# ==================== MAIN ====================
def run_bot():
    logger.info(f"Starting {Config.BRAND_NAME} v{Config.VERSION}")
    bot.remove_webhook()
    
    while True:
        try:
            bot.infinity_polling(timeout=60)
        except Exception as e:
            logger.error(f"Bot error: {e}")
            time.sleep(5)

if __name__ == '__main__':
    # Start cleanup thread
    threading.Thread(target=cleanup_processes, daemon=True).start()
    
    # Start bot
    threading.Thread(target=run_bot, daemon=True).start()
    
    # Start Flask
    logger.info(f"Starting web server on port {Config.PORT}")
    app.run(host='0.0.0.0', port=Config.PORT, debug=False)
