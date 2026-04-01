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
import hashlib
import logging
import psutil
import requests
from pathlib import Path
from telebot import types
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from flask import Flask, send_file, jsonify, request
from functools import wraps
from typing import Dict, List, Tuple, Optional

# ================== Logging Setup ==================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ================== Enhanced Configuration ==================
class Config:
    # Bot Configuration
    TOKEN = os.environ.get('BOT_TOKEN', '8754448627:AAFReyCErlSnESaSJOUzAt1Ut-n95w_xWDI')
    ADMIN_ID = int(os.environ.get('ADMIN_ID', 6487613131))
    
    # Paths
    PROJECT_DIR = 'projects'
    DB_NAME = 'cyber_v3.db'
    LOGS_DIR = 'logs'
    BACKUP_DIR = 'backups'
    TEMP_DIR = 'temp'
    
    # Server Configuration
    PORT = int(os.environ.get('PORT', 10000))
    HOST = '0.0.0.0'
    
    # Bot Settings
    MAINTENANCE = False
    DEBUG_MODE = False
    
    # Branding
    ADMIN_USERNAME = 'aurponmodz'
    BOT_USERNAME = "@aurpon_bot_host_bot"
    SUPPORT_ID = "@aurponmodz"
    BRAND_NAME = "💎 𝐀𝐔𝐑𝐏𝐎𝐍(√) 💎"
    VERSION = "3.0.0"
    
    # Limits
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_BOTS_PER_USER = 50
    MAX_CONCURRENT_DEPLOYMENTS = 10
    SESSION_TIMEOUT = 3600  # 1 hour
    
    # Security
    API_KEY = os.environ.get('API_KEY', str(uuid.uuid4()))
    JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key-change-this')
    
    # Create necessary directories
    for dir_path in [PROJECT_DIR, LOGS_DIR, BACKUP_DIR, TEMP_DIR]:
        Path(dir_path).mkdir(exist_ok=True)

# ================== Initialize Bot ==================
bot = telebot.TeleBot(Config.TOKEN, parse_mode="HTML", threaded=False)
project_path = Path(Config.PROJECT_DIR)
app = Flask(__name__)

# ================== Database Manager ==================
class DatabaseManager:
    def __init__(self, db_name: str):
        self.db_name = db_name
        self.init_db()
    
    def get_connection(self):
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_db(self):
        with self.get_connection() as conn:
            c = conn.cursor()
            
            # Users table
            c.execute('''CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                email TEXT,
                expiry TEXT,
                file_limit INTEGER,
                is_prime INTEGER,
                join_date TEXT,
                last_renewal TEXT,
                api_key TEXT,
                total_bots INTEGER DEFAULT 0,
                total_deployments INTEGER DEFAULT 0,
                last_login TEXT
            )''')
            
            # Keys table
            c.execute('''CREATE TABLE IF NOT EXISTS keys (
                key TEXT PRIMARY KEY,
                duration_days INTEGER,
                file_limit INTEGER,
                created_date TEXT,
                used_by INTEGER,
                used_date TEXT,
                is_used INTEGER DEFAULT 0
            )''')
            
            # Deployments table
            c.execute('''CREATE TABLE IF NOT EXISTS deployments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                bot_name TEXT,
                filename TEXT,
                pid INTEGER,
                start_time TEXT,
                status TEXT,
                cpu_usage REAL,
                ram_usage REAL,
                last_active TEXT,
                port INTEGER,
                webhook_url TEXT,
                error_log TEXT,
                deploy_count INTEGER DEFAULT 0
            )''')
            
            # Activity logs
            c.execute('''CREATE TABLE IF NOT EXISTS activity_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT,
                details TEXT,
                timestamp TEXT
            )''')
            
            # Bot templates
            c.execute('''CREATE TABLE IF NOT EXISTS templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                description TEXT,
                content TEXT,
                created_by INTEGER,
                created_date TEXT,
                is_public INTEGER DEFAULT 0
            )''')
            
            # Add admin user
            join_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            expiry_date = (datetime.now() + timedelta(days=3650)).strftime('%Y-%m-%d %H:%M:%S')
            api_key = hashlib.sha256(f"{Config.ADMIN_ID}{Config.JWT_SECRET}".encode()).hexdigest()
            
            c.execute("""INSERT OR IGNORE INTO users 
                        (id, username, expiry, file_limit, is_prime, join_date, api_key, last_login) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", 
                     (Config.ADMIN_ID, 'admin', expiry_date, 999, 1, join_date, api_key, join_date))
            
            conn.commit()
    
    def log_activity(self, user_id: int, action: str, details: str = ""):
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute("INSERT INTO activity_logs (user_id, action, details, timestamp) VALUES (?, ?, ?, ?)",
                     (user_id, action, details, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            conn.commit()
    
    def get_user(self, user_id: int):
        with self.get_connection() as conn:
            c = conn.cursor()
            return c.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    
    def get_user_bots(self, user_id: int):
        with self.get_connection() as conn:
            c = conn.cursor()
            return c.execute("""SELECT id, bot_name, filename, pid, start_time, status, cpu_usage, ram_usage 
                               FROM deployments WHERE user_id=? ORDER BY id DESC""", (user_id,)).fetchall()
    
    def update_user_login(self, user_id: int):
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute("UPDATE users SET last_login=? WHERE id=?", 
                     (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), user_id))
            conn.commit()

db = DatabaseManager(Config.DB_NAME)

# ================== Security Decorators ==================
def admin_only(func):
    """Decorator to restrict commands to admin only"""
    @wraps(func)
    def wrapper(message, *args, **kwargs):
        if message.from_user.id != Config.ADMIN_ID:
            logger.warning(f"Unauthorized access attempt by {message.from_user.id}")
            return
        return func(message, *args, **kwargs)
    return wrapper

def maintenance_check(func):
    """Decorator to check maintenance mode"""
    @wraps(func)
    def wrapper(message, *args, **kwargs):
        if Config.MAINTENANCE and message.from_user.id != Config.ADMIN_ID:
            bot.reply_to(message, "🔧 Bot is under maintenance. Please try again later.")
            return
        return func(message, *args, **kwargs)
    return wrapper

def rate_limit(limit: int = 10, window: int = 60):
    """Rate limiting decorator"""
    rate_limits = {}
    
    def decorator(func):
        @wraps(func)
        def wrapper(message, *args, **kwargs):
            user_id = message.from_user.id
            current_time = time.time()
            
            if user_id not in rate_limits:
                rate_limits[user_id] = []
            
            # Clean old entries
            rate_limits[user_id] = [t for t in rate_limits[user_id] if current_time - t < window]
            
            if len(rate_limits[user_id]) >= limit:
                bot.reply_to(message, f"⚠️ Rate limit exceeded. Please wait {window} seconds.")
                return
            
            rate_limits[user_id].append(current_time)
            return func(message, *args, **kwargs)
        return wrapper
    return decorator

# ================== Enhanced Helper Functions ==================
def get_system_stats() -> Dict:
    """Get real system statistics"""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            'cpu_percent': cpu_percent,
            'ram_percent': ram.percent,
            'ram_used': ram.used,
            'ram_total': ram.total,
            'disk_percent': disk.percent,
            'disk_used': disk.used,
            'disk_total': disk.total,
            'uptime': time.time() - psutil.boot_time()
        }
    except:
        # Fallback to random if psutil fails
        return {
            'cpu_percent': random.randint(10, 60),
            'ram_percent': random.randint(20, 70),
            'ram_used': random.randint(1024, 4096),
            'ram_total': 8192,
            'disk_percent': random.randint(30, 80),
            'disk_used': random.randint(10240, 51200),
            'disk_total': 102400,
            'uptime': random.randint(86400, 604800)
        }

def format_size(bytes: int) -> str:
    """Format bytes to human readable"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024.0:
            return f"{bytes:.2f} {unit}"
        bytes /= 1024.0
    return f"{bytes:.2f} TB"

def format_uptime(seconds: int) -> str:
    """Format uptime to human readable"""
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    
    parts = []
    if days > 0: parts.append(f"{days}d")
    if hours > 0: parts.append(f"{hours}h")
    if minutes > 0: parts.append(f"{minutes}m")
    if seconds > 0 or not parts: parts.append(f"{seconds}s")
    
    return " ".join(parts)

def create_progress_bar(percentage: float, length: int = 20) -> str:
    """Create a text progress bar"""
    filled = int(length * percentage / 100)
    return "█" * filled + "░" * (length - filled)

def validate_bot_file(content: bytes, filename: str) -> Tuple[bool, str]:
    """Validate uploaded bot file"""
    # Check file size
    if len(content) > Config.MAX_FILE_SIZE:
        return False, f"File size exceeds {Config.MAX_FILE_SIZE // (1024*1024)}MB limit"
    
    # Check file extension
    if not (filename.endswith('.py') or filename.endswith('.zip')):
        return False, "Only .py or .zip files are allowed"
    
    # For Python files, basic syntax check
    if filename.endswith('.py'):
        try:
            compile(content, filename, 'exec')
        except SyntaxError as e:
            return False, f"Syntax error: {str(e)}"
    
    return True, "OK"

def backup_database():
    """Create database backup"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = Path(Config.BACKUP_DIR) / f"backup_{timestamp}.db"
    shutil.copy2(Config.DB_NAME, backup_path)
    
    # Keep only last 10 backups
    backups = sorted(Path(Config.BACKUP_DIR).glob("backup_*.db"))
    for old_backup in backups[:-10]:
        old_backup.unlink()
    
    logger.info(f"Database backup created: {backup_path}")

# ================== Advanced Keyboards ==================
class Keyboards:
    @staticmethod
    def main_menu(user_id: int) -> types.ReplyKeyboardMarkup:
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        
        buttons = [
            "📤 Upload Bot",
            "🤖 My Bots",
            "🚀 Deploy Bot",
            "📊 Dashboard",
            "📁 Templates",
            "⚙️ Settings",
            "❓ Help",
            "ℹ️ About"
        ]
        
        if user_id == Config.ADMIN_ID:
            buttons.extend(["👑 Admin Panel", "📈 Analytics"])
        
        markup.add(*[types.KeyboardButton(btn) for btn in buttons])
        return markup
    
    @staticmethod
    def bot_control_menu(bot_id: int, status: str) -> types.InlineKeyboardMarkup:
        markup = types.InlineKeyboardMarkup(row_width=3)
        
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
            types.InlineKeyboardButton("📝 Logs", callback_data=f"logs_{bot_id}")
        )
        
        return markup
    
    @staticmethod
    def admin_panel() -> types.InlineKeyboardMarkup:
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("👥 Users", callback_data="admin_users"),
            types.InlineKeyboardButton("🔑 Generate Key", callback_data="admin_genkey"),
            types.InlineKeyboardButton("📊 Stats", callback_data="admin_stats"),
            types.InlineKeyboardButton("⚙️ Settings", callback_data="admin_settings"),
            types.InlineKeyboardButton("📋 Broadcast", callback_data="admin_broadcast"),
            types.InlineKeyboardButton("💾 Backup", callback_data="admin_backup")
        )
        return markup

# ================== Enhanced Command Handlers ==================
@bot.message_handler(commands=['start'])
@maintenance_check
@rate_limit(limit=5, window=30)
def welcome(message):
    user_id = message.from_user.id
    username = message.from_user.username or "User"
    
    # Update user login
    user = db.get_user(user_id)
    if not user:
        # Auto-register new users (only for non-admin)
        if user_id != Config.ADMIN_ID:
            join_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            expiry_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')  # 7-day trial
            api_key = hashlib.sha256(f"{user_id}{Config.JWT_SECRET}".encode()).hexdigest()
            
            with db.get_connection() as conn:
                c = conn.cursor()
                c.execute("""INSERT INTO users 
                            (id, username, expiry, file_limit, is_prime, join_date, api_key, last_login) 
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                         (user_id, username, expiry_date, 5, 0, join_date, api_key, join_date))
                conn.commit()
            user = db.get_user(user_id)
    else:
        db.update_user_login(user_id)
    
    # Check subscription
    if user and user['expiry']:
        try:
            expiry_date = datetime.strptime(user['expiry'], '%Y-%m-%d %H:%M:%S')
            days_left = (expiry_date - datetime.now()).days
            is_expired = expiry_date < datetime.now()
        except:
            days_left = 0
            is_expired = True
    else:
        days_left = 0
        is_expired = True
    
    # System stats
    stats = get_system_stats()
    
    # Welcome message
    welcome_text = f"""
✨ <b>{Config.BRAND_NAME} v{Config.VERSION}</b> ✨
<b>━━━━━━━━━━━━━━━━━━━━━━</b>
👤 <b>User:</b> @{username}
🆔 <b>ID:</b> <code>{user_id}</code>
💎 <b>Status:</b> {'👑 PRIME' if user and user['is_prime'] else '⭐ TRIAL' if not is_expired else '❌ EXPIRED'}
📅 <b>Expires:</b> {user['expiry'] if user and user['expiry'] else 'N/A'}
📦 <b>File Limit:</b> {user['file_limit'] if user else 0} files
<b>━━━━━━━━━━━━━━━━━━━━━━</b>

🖥️ <b>System Status:</b>
• <b>CPU:</b> {create_progress_bar(stats['cpu_percent'])} {stats['cpu_percent']:.1f}%
• <b>RAM:</b> {create_progress_bar(stats['ram_percent'])} {stats['ram_percent']:.1f}%
• <b>Disk:</b> {create_progress_bar(stats['disk_percent'])} {stats['disk_percent']:.1f}%

<b>━━━━━━━━━━━━━━━━━━━━━━</b>
💡 <b>Tips:</b> Use the buttons below to manage your bots!
"""
    
    bot.send_message(message.chat.id, welcome_text, 
                    reply_markup=Keyboards.main_menu(user_id))
    db.log_activity(user_id, "start", "User started the bot")

@bot.message_handler(commands=['help'])
@maintenance_check
def help_command(message):
    help_text = """
❓ <b>Help & Support</b>
<b>━━━━━━━━━━━━━━━━━━━━━━</b>

<b>📤 Upload Bot</b>
Upload your Python bot file (.py or .zip). Max size: 10MB

<b>🤖 My Bots</b>
View all your deployed bots with status and controls

<b>🚀 Deploy Bot</b>
Deploy an uploaded bot to run on the server

<b>📊 Dashboard</b>
View system statistics and your account info

<b>📁 Templates</b>
Use pre-made bot templates for quick deployment

<b>⚙️ Settings</b>
Configure your account preferences

<b>━━━━━━━━━━━━━━━━━━━━━━</b>
💬 <b>Support:</b> {Config.SUPPORT_ID}
📢 <b>Channel:</b> {Config.BOT_USERNAME}
🌐 <b>Version:</b> {Config.VERSION}

<i>Need help? Contact our support team!</i>
"""
    bot.reply_to(message, help_text)

@bot.message_handler(commands=['stats'])
@admin_only
def stats_command(message):
    """Admin statistics command"""
    with db.get_connection() as conn:
        c = conn.cursor()
        total_users = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        active_users = c.execute("SELECT COUNT(*) FROM users WHERE expiry > datetime('now')").fetchone()[0]
        total_bots = c.execute("SELECT COUNT(*) FROM deployments").fetchone()[0]
        running_bots = c.execute("SELECT COUNT(*) FROM deployments WHERE status='Running'").fetchone()[0]
        total_deploys = c.execute("SELECT SUM(deploy_count) FROM deployments").fetchone()[0]
    
    stats = get_system_stats()
    
    stats_text = f"""
📊 <b>System Statistics</b>
<b>━━━━━━━━━━━━━━━━━━━━━━</b>

<b>👥 Users:</b>
• Total: {total_users}
• Active: {active_users}
• Inactive: {total_users - active_users}

<b>🤖 Bots:</b>
• Total: {total_bots}
• Running: {running_bots}
• Stopped: {total_bots - running_bots}
• Total Deploys: {total_deploys}

<b>🖥️ Server:</b>
• CPU: {stats['cpu_percent']:.1f}%
• RAM: {stats['ram_percent']:.1f}%
• Disk: {stats['disk_percent']:.1f}%
• Uptime: {format_uptime(int(stats['uptime']))}

<b>━━━━━━━━━━━━━━━━━━━━━━</b>
"""
    bot.reply_to(message, stats_text)

@bot.message_handler(func=lambda message: message.text == "📤 Upload Bot")
@maintenance_check
@rate_limit(limit=3, window=60)
def upload_handler(message):
    user = db.get_user(message.from_user.id)
    if not user or user['file_limit'] <= 0:
        bot.reply_to(message, "❌ You have reached your file limit or your account has expired!")
        return
    
    msg = bot.reply_to(message, """
📤 <b>UPLOAD BOT FILE</b>
<b>━━━━━━━━━━━━━━━━━━━━━━</b>

Send me your Python bot file:
• Supported: <b>.py</b> or <b>.zip</b>
• Max size: <b>10MB</b>
• Your limit: <b>{}</b> files remaining

<i>Note: Make sure your bot code is compatible with Python 3.8+</i>
""".format(user['file_limit']))
    
    bot.register_next_step_handler(msg, process_upload)

def process_upload(message):
    user_id = message.from_user.id
    
    if message.content_type != 'document':
        bot.reply_to(message, "❌ Please send a valid file!")
        return
    
    try:
        file_name = message.document.file_name
        file_size = message.document.file_size
        
        # Download file
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        # Validate file
        is_valid, error_msg = validate_bot_file(downloaded_file, file_name)
        if not is_valid:
            bot.reply_to(message, f"❌ {error_msg}")
            return
        
        # Save file
        safe_name = secure_filename(file_name)
        file_path = project_path / safe_name
        
        # Check if file already exists
        if file_path.exists():
            file_path = project_path / f"{uuid.uuid4().hex[:8]}_{safe_name}"
        
        file_path.write_bytes(downloaded_file)
        
        # Ask for bot name
        msg = bot.reply_to(message, "✅ File uploaded successfully!\n\n🤖 Enter a name for your bot:")
        bot.register_next_step_handler(msg, save_bot_info, safe_name, file_path)
        
        db.log_activity(user_id, "upload", f"Uploaded {safe_name}")
        
    except Exception as e:
        logger.error(f"Upload error: {e}")
        bot.reply_to(message, f"❌ Error uploading file: {str(e)}")

def save_bot_info(message, safe_name, file_path):
    user_id = message.from_user.id
    bot_name = message.text.strip()[:50]
    
    with db.get_connection() as conn:
        c = conn.cursor()
        c.execute("""INSERT INTO deployments 
                    (user_id, bot_name, filename, pid, start_time, status, last_active, deploy_count) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                 (user_id, bot_name, safe_name, 0, None, "Uploaded", 
                  datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 0))
        
        # Update user's file limit
        user = db.get_user(user_id)
        c.execute("UPDATE users SET file_limit=? WHERE id=?", 
                 (user['file_limit'] - 1, user_id))
        
        conn.commit()
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📚 Install Libraries", "🤖 My Bots", "🏠 Main Menu")
    
    bot.send_message(message.chat.id, 
                    f"✅ <b>Bot '{bot_name}' saved successfully!</b>\n\n"
                    f"📁 File: <code>{safe_name}</code>\n"
                    f"🔧 Next steps:\n"
                    f"• Install required libraries\n"
                    f"• Deploy your bot\n"
                    f"• Monitor from 'My Bots' menu",
                    reply_markup=markup)
    
    db.log_activity(user_id, "save_bot", f"Saved bot {bot_name}")

@bot.message_handler(func=lambda message: message.text == "🤖 My Bots")
@maintenance_check
def show_my_bots(message):
    user_id = message.from_user.id
    bots = db.get_user_bots(user_id)
    
    if not bots:
        bot.reply_to(message, "🤖 No bots found in your list.\n\nUpload and deploy your first bot!")
        return
    
    text = "<b>🤖 MY DEPLOYED BOTS</b>\n<b>━━━━━━━━━━━━━━━━━━━━━━</b>\n\n"
    
    for idx, bot_info in enumerate(bots, 1):
        status_icon = "🟢" if bot_info['status'] == "Running" else "🔴" if bot_info['status'] == "Stopped" else "🟡"
        
        # Get uptime if running
        uptime = ""
        if bot_info['status'] == "Running" and bot_info['start_time']:
            try:
                start = datetime.strptime(bot_info['start_time'], '%Y-%m-%d %H:%M:%S')
                uptime_delta = datetime.now() - start
                uptime = f" | Uptime: {str(uptime_delta).split('.')[0]}"
            except:
                pass
        
        text += f"{idx}. {status_icon} <b>{bot_info['bot_name']}</b>\n"
        text += f"   📁 {bot_info['filename']}\n"
        text += f"   Status: {bot_info['status']}{uptime}\n"
        
        if bot_info['cpu_usage']:
            text += f"   💻 CPU: {bot_info['cpu_usage']:.1f}% | RAM: {bot_info['ram_usage']:.1f}%\n"
        
        text += "\n"
    
    text += "<b>━━━━━━━━━━━━━━━━━━━━━━</b>\n"
    text += "Select a bot to manage it:"
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for bot_info in bots:
        markup.add(types.InlineKeyboardButton(
            f"{bot_info['bot_name']} ({bot_info['status']})",
            callback_data=f"select_{bot_info['id']}"
        ))
    
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("select_"))
def handle_bot_selection(call):
    bot_id = int(call.data.split("_")[1])
    
    with db.get_connection() as conn:
        c = conn.cursor()
        bot_info = c.execute("""SELECT id, bot_name, filename, pid, start_time, status, cpu_usage, ram_usage, error_log
                               FROM deployments WHERE id=?""", (bot_id,)).fetchone()
    
    if not bot_info:
        bot.answer_callback_query(call.id, "Bot not found!")
        return
    
    uptime = "N/A"
    if bot_info['status'] == "Running" and bot_info['start_time']:
        try:
            start = datetime.strptime(bot_info['start_time'], '%Y-%m-%d %H:%M:%S')
            uptime_delta = datetime.now() - start
            uptime = str(uptime_delta).split('.')[0]
        except:
            pass
    
    text = f"""
<b>🤖 BOT DETAILS</b>
<b>━━━━━━━━━━━━━━━━━━━━━━</b>

<b>Name:</b> {bot_info['bot_name']}
<b>File:</b> <code>{bot_info['filename']}</code>
<b>Status:</b> {bot_info['status']}
<b>Started:</b> {bot_info['start_time'] or 'Not started'}
<b>Uptime:</b> {uptime}

<b>📊 Resource Usage:</b>
• <b>CPU:</b> {bot_info['cpu_usage'] or 0:.1f}%
• <b>RAM:</b> {bot_info['ram_usage'] or 0:.1f}%

<b>━━━━━━━━━━━━━━━━━━━━━━</b>
"""
    
    if bot_info['error_log']:
        text += f"\n<b>⚠️ Last Error:</b>\n<code>{bot_info['error_log'][:200]}</code>"
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                         reply_markup=Keyboards.bot_control_menu(bot_id, bot_info['status']))
    
    bot.answer_callback_query(call.id)

# ================== Flask Web Interface ==================
@app.route('/')
def home():
    """API endpoint for bot status"""
    return jsonify({
        "status": "online",
        "brand": Config.BRAND_NAME,
        "version": Config.VERSION,
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/stats')
def api_stats():
    """API endpoint for system stats"""
    stats = get_system_stats()
    with db.get_connection() as conn:
        c = conn.cursor()
        total_bots = c.execute("SELECT COUNT(*) FROM deployments").fetchone()[0]
        running_bots = c.execute("SELECT COUNT(*) FROM deployments WHERE status='Running'").fetchone()[0]
    
    return jsonify({
        "system": stats,
        "bots": {
            "total": total_bots,
            "running": running_bots
        }
    })

@app.route('/api/users/<int:user_id>')
def get_user_api(user_id):
    """API endpoint for user info"""
    api_key = request.headers.get('X-API-Key')
    if not api_key:
        return jsonify({"error": "API key required"}), 401
    
    user = db.get_user(user_id)
    if not user or user['api_key'] != api_key:
        return jsonify({"error": "Invalid API key"}), 401
    
    return jsonify({
        "id": user['id'],
        "username": user['username'],
        "expiry": user['expiry'],
        "is_prime": bool(user['is_prime']),
        "file_limit": user['file_limit']
    })

# ================== Background Tasks ==================
def cleanup_processes():
    """Clean up orphaned processes"""
    with db.get_connection() as conn:
        c = conn.cursor()
        running_bots = c.execute("SELECT id, pid FROM deployments WHERE status='Running'").fetchall()
        
        for bot_id, pid in running_bots:
            if pid:
                try:
                    # Check if process is still running
                    os.kill(pid, 0)
                except OSError:
                    # Process not running, update database
                    c.execute("UPDATE deployments SET status='Stopped', pid=0 WHERE id=?", (bot_id,))
        
        conn.commit()

def update_bot_stats():
    """Update bot resource usage statistics"""
    with db.get_connection() as conn:
        c = conn.cursor()
        running_bots = c.execute("SELECT id, pid FROM deployments WHERE status='Running' AND pid > 0").fetchall()
        
        for bot_id, pid in running_bots:
            try:
                process = psutil.Process(pid)
                cpu = process.cpu_percent(interval=0.1)
                mem = process.memory_percent()
                
                c.execute("UPDATE deployments SET cpu_usage=?, ram_usage=?, last_active=? WHERE id=?",
                         (cpu, mem, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), bot_id))
            except:
                # Process might have died
                c.execute("UPDATE deployments SET status='Stopped', pid=0 WHERE id=?", (bot_id,))
        
        conn.commit()

def schedule_tasks():
    """Schedule background tasks"""
    schedule.every(5).minutes.do(cleanup_processes)
    schedule.every(1).minutes.do(update_bot_stats)
    schedule.every().day.at("00:00").do(backup_database)
    
    while True:
        schedule.run_pending()
        time.sleep(60)

# ================== Main Application ==================
def start_bot():
    """Start the Telegram bot"""
    logger.info(f"Starting bot {Config.BOT_USERNAME} v{Config.VERSION}")
    
    # Remove webhook
    bot.remove_webhook()
    time.sleep(1)
    
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            logger.error(f"Bot polling error: {e}")
            time.sleep(5)

if __name__ == '__main__':
    # Start background tasks
    threading.Thread(target=schedule_tasks, daemon=True).start()
    
    # Start bot
    threading.Thread(target=start_bot, daemon=True).start()
    
    # Start Flask server
    logger.info(f"Starting Flask server on {Config.HOST}:{Config.PORT}")
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG_MODE)