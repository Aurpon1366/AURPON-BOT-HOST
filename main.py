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
import asyncio
import aiohttp
import redis
import socket
import netifaces
import docker
import git
import yaml
import base64
import secrets
import string
from pathlib import Path
from telebot import types
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from flask import Flask, send_file, jsonify, request, render_template
from functools import wraps
from collections import defaultdict
from ratelimit import limits, sleep_and_retry
from prometheus_client import Counter, Gauge, generate_latest, CollectorRegistry
from cryptography.fernet import Fernet
from apscheduler.schedulers.background import BackgroundScheduler
from celery import Celery
import redis.asyncio as aioredis
import qrcode
from io import BytesIO
from PIL import Image
import matplotlib.pyplot as plt
import pandas as pd
from wordcloud import WordCloud
import plotly.graph_objects as go
import plotly.express as px
from jinja2 import Template
import markdown
from weasyprint import HTML
import asyncio
import aiofiles
import httpx
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import yfinance as yf
import praw
import tweepy
import discord
import asyncio
from telethon import TelegramClient
from instabot import Bot as InstaBot
from youtube_upload.client import YoutubeUploader
import openai
import anthropic
import google.generativeai as genai
import torch
import transformers
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
import numpy as np
import cv2
from deepface import DeepFace
import speech_recognition as sr
from gtts import gTTS
import pygame
from moviepy.editor import VideoFileClip, AudioFileClip
import whisper
import langdetect
from googletrans import Translator
import spacy
from textblob import TextBlob
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
import schedule as schedule_lib
import email
import imaplib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import paramiko
import scp
import boto3
from azure.storage.blob import BlobServiceClient
from google.cloud import storage
import stripe
import paypalrestsdk
import razorpay
from coinbase_commerce.client import Client as CoinbaseClient
import web3
from web3 import Web3
import solana
from solders.keypair import Keypair
import hashlib
import jwt
import oauthlib
import requests_oauthlib
import authlib
import pyotp
import qrcode
import phonenumbers
from phonenumbers import carrier, geocoder, timezone
import pycountry
import currencyapicom
import forex_python.converter
import geopy
from geopy.geocoders import Nominatim
import folium
import openrouteservice
import json
import xmltodict
import feedparser
import pypdf
import docx
from pptx import Presentation
import openpyxl
import xlrd
import csv
import pandas as pd
import numpy as np
import matplotlib
import seaborn as sns
import plotly
import bokeh
import altair
import dash
from dash import dcc, html
import jupyter
import notebook
import streamlit
import gradio as gr
import fastapi
import uvicorn
import gunicorn
import nginx
import apache
import caddy
import traefik
import kubernetes
import helm
import docker
import podman
import ansible
import terraform
import pulumi
import cdktf
import aws_cdk
import serverless
import cloudflare
import vercel
import netlify
import heroku
import digitalocean
import linode
import vultr
import scaleway
import ovh
import hetzner
import aws
import azure
import gcp
import alibaba
import oracle
import ibm
import tencent
import digital_ocean
import linode_api
import vultr_api
import scaleway_api
import ovh_api
import hetzner_api
import aws_api
import azure_api
import gcp_api

# ================== Configuration ==================
class Config:
    # Bot Configuration
    TOKEN = os.environ.get('BOT_TOKEN', '8754448627:AAFReyCErlSnESaSJOUzAt1Ut-n95w_xWDI')
    ADMIN_ID = int(os.environ.get('ADMIN_ID', 6487613131))
    
    # Paths
    PROJECT_DIR = 'projects'
    DB_NAME = 'cyber_v4.db'
    LOGS_DIR = 'logs'
    BACKUP_DIR = 'backups'
    TEMP_DIR = 'temp'
    CACHE_DIR = 'cache'
    MODELS_DIR = 'models'
    
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
    BRAND_NAME = "💎 𝐀𝐔𝐑𝐏𝐎𝐍 𝐃𝐄𝐗 𝐏𝐑𝐎 💎"
    VERSION = "4.0.0"
    
    # Limits
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    MAX_BOTS_PER_USER = 100
    MAX_CONCURRENT_DEPLOYMENTS = 50
    SESSION_TIMEOUT = 3600
    
    # API Keys (Add your own)
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
    ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
    GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY', '')
    STRIPE_API_KEY = os.environ.get('STRIPE_API_KEY', '')
    PAYPAL_CLIENT_ID = os.environ.get('PAYPAL_CLIENT_ID', '')
    RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID', '')
    COINBASE_API_KEY = os.environ.get('COINBASE_API_KEY', '')
    WEB3_INFURA_URL = os.environ.get('WEB3_INFURA_URL', '')
    
    # Security
    SECRET_KEY = os.environ.get('SECRET_KEY', secrets.token_urlsafe(32))
    ENCRYPTION_KEY = Fernet.generate_key()
    JWT_SECRET = os.environ.get('JWT_SECRET', secrets.token_urlsafe(32))
    
    # Database
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379')
    MONGODB_URL = os.environ.get('MONGODB_URL', 'mongodb://localhost:27017')
    
    # Cloud Storage
    AWS_ACCESS_KEY = os.environ.get('AWS_ACCESS_KEY', '')
    AWS_SECRET_KEY = os.environ.get('AWS_SECRET_KEY', '')
    AWS_BUCKET_NAME = os.environ.get('AWS_BUCKET_NAME', '')
    AZURE_CONNECTION_STRING = os.environ.get('AZURE_CONNECTION_STRING', '')
    GCP_CREDENTIALS = os.environ.get('GCP_CREDENTIALS', '')
    
    # Create directories
    for dir_path in [PROJECT_DIR, LOGS_DIR, BACKUP_DIR, TEMP_DIR, CACHE_DIR, MODELS_DIR]:
        Path(dir_path).mkdir(exist_ok=True)

# ================== Initialize Bot ==================
bot = telebot.TeleBot(Config.TOKEN, parse_mode="HTML")
project_path = Path(Config.PROJECT_DIR)
app = Flask(__name__)
app.config['SECRET_KEY'] = Config.SECRET_KEY

# Initialize Redis
try:
    redis_client = redis.from_url(Config.REDIS_URL)
except:
    redis_client = None

# ================== Advanced Database Manager ==================
class AdvancedDatabaseManager:
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
            
            # Users table with more fields
            c.execute('''CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                email TEXT,
                full_name TEXT,
                phone TEXT,
                country TEXT,
                expiry TEXT,
                file_limit INTEGER,
                is_prime INTEGER,
                join_date TEXT,
                last_renewal TEXT,
                api_key TEXT,
                total_bots INTEGER DEFAULT 0,
                total_deployments INTEGER DEFAULT 0,
                last_login TEXT,
                credits INTEGER DEFAULT 0,
                referrals INTEGER DEFAULT 0,
                referred_by INTEGER,
                banned INTEGER DEFAULT 0,
                ban_reason TEXT,
                two_factor_enabled INTEGER DEFAULT 0,
                two_factor_secret TEXT,
                notification_settings TEXT,
                theme TEXT DEFAULT 'dark'
            )''')
            
            # Keys table
            c.execute('''CREATE TABLE IF NOT EXISTS keys (
                key TEXT PRIMARY KEY,
                duration_days INTEGER,
                file_limit INTEGER,
                created_date TEXT,
                used_by INTEGER,
                used_date TEXT,
                is_used INTEGER DEFAULT 0,
                key_type TEXT DEFAULT 'premium',
                price REAL,
                currency TEXT DEFAULT 'USD'
            )''')
            
            # Deployments table with more fields
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
                disk_usage REAL,
                network_rx REAL,
                network_tx REAL,
                last_active TEXT,
                port INTEGER,
                webhook_url TEXT,
                error_log TEXT,
                deploy_count INTEGER DEFAULT 0,
                version TEXT,
                language TEXT DEFAULT 'python',
                requirements TEXT,
                env_vars TEXT,
                auto_restart INTEGER DEFAULT 0,
                max_memory INTEGER DEFAULT 512,
                max_cpu INTEGER DEFAULT 100,
                health_check_url TEXT,
                health_status TEXT
            )''')
            
            # Activity logs
            c.execute('''CREATE TABLE IF NOT EXISTS activity_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT,
                details TEXT,
                ip_address TEXT,
                user_agent TEXT,
                timestamp TEXT
            )''')
            
            # Bot templates
            c.execute('''CREATE TABLE IF NOT EXISTS templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                description TEXT,
                content TEXT,
                requirements TEXT,
                created_by INTEGER,
                created_date TEXT,
                updated_date TEXT,
                is_public INTEGER DEFAULT 0,
                category TEXT,
                tags TEXT,
                downloads INTEGER DEFAULT 0,
                rating REAL DEFAULT 0,
                reviews INTEGER DEFAULT 0
            )''')
            
            # Payments
            c.execute('''CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount REAL,
                currency TEXT,
                payment_method TEXT,
                transaction_id TEXT,
                status TEXT,
                created_date TEXT,
                expiry_date TEXT
            )''')
            
            # Analytics
            c.execute('''CREATE TABLE IF NOT EXISTS analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                total_users INTEGER,
                active_users INTEGER,
                total_bots INTEGER,
                running_bots INTEGER,
                total_deployments INTEGER,
                total_revenue REAL
            )''')
            
            # Add admin user
            join_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            expiry_date = (datetime.now() + timedelta(days=3650)).strftime('%Y-%m-%d %H:%M:%S')
            api_key = hashlib.sha256(f"{Config.ADMIN_ID}{Config.JWT_SECRET}".encode()).hexdigest()
            
            c.execute("""INSERT OR IGNORE INTO users 
                        (id, username, expiry, file_limit, is_prime, join_date, api_key, last_login, credits) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""", 
                     (Config.ADMIN_ID, 'admin', expiry_date, 9999, 1, join_date, api_key, join_date, 999999))
            
            conn.commit()
    
    def log_activity(self, user_id: int, action: str, details: str = "", ip: str = "", ua: str = ""):
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute("""INSERT INTO activity_logs 
                        (user_id, action, details, ip_address, user_agent, timestamp) 
                        VALUES (?, ?, ?, ?, ?, ?)""",
                     (user_id, action, details, ip, ua, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            conn.commit()
    
    def get_user(self, user_id: int):
        with self.get_connection() as conn:
            c = conn.cursor()
            return c.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    
    def get_user_bots(self, user_id: int):
        with self.get_connection() as conn:
            c = conn.cursor()
            return c.execute("""SELECT id, bot_name, filename, pid, start_time, status, 
                               cpu_usage, ram_usage, port, version 
                               FROM deployments WHERE user_id=? ORDER BY id DESC""", 
                           (user_id,)).fetchall()
    
    def update_user_credits(self, user_id: int, credits: int):
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute("UPDATE users SET credits=credits+? WHERE id=?", (credits, user_id))
            conn.commit()

db = AdvancedDatabaseManager(Config.DB_NAME)

# ================== Advanced Features ==================

class AIAssistant:
    """AI Assistant for bot management"""
    
    def __init__(self):
        self.translator = Translator()
        self.nlp = spacy.load("en_core_web_sm") if spacy.util.is_package("en_core_web_sm") else None
        self.sia = SentimentIntensityAnalyzer() if nltk.sentiment.SentimentIntensityAnalyzer else None
        
        # Initialize AI models
        if Config.OPENAI_API_KEY:
            openai.api_key = Config.OPENAI_API_KEY
        if Config.ANTHROPIC_API_KEY:
            self.anthropic = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)
        if Config.GOOGLE_API_KEY:
            genai.configure(api_key=Config.GOOGLE_API_KEY)
            self.gemini = genai.GenerativeModel('gemini-pro')
    
    async def generate_bot_code(self, description: str, framework: str = "telegram") -> str:
        """Generate bot code using AI"""
        prompt = f"""
        Generate a complete Python Telegram bot with the following requirements:
        Description: {description}
        Framework: python-telegram-bot
        Features: error handling, logging, database integration
        Make it production-ready with comments.
        """
        
        try:
            if Config.OPENAI_API_KEY:
                response = openai.ChatCompletion.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=2000
                )
                return response.choices[0].message.content
            elif Config.GOOGLE_API_KEY:
                response = self.gemini.generate_content(prompt)
                return response.text
            else:
                return self._generate_template_bot(description)
        except Exception as e:
            return f"Error generating code: {str(e)}"
    
    def _generate_template_bot(self, description: str) -> str:
        """Generate template bot code"""
        return f'''
import telebot
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = "YOUR_BOT_TOKEN"
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Welcome! I'm your AI-generated bot.\\nDescription: {description}")

@bot.message_handler(func=lambda m: True)
def echo(message):
    bot.reply_to(message, message.text)

if __name__ == '__main__':
    bot.infinity_polling()
'''
    
    async def analyze_sentiment(self, text: str) -> dict:
        """Analyze text sentiment"""
        if self.sia:
            scores = self.sia.polarity_scores(text)
            return {
                'sentiment': 'positive' if scores['compound'] > 0.05 else 'negative' if scores['compound'] < -0.05 else 'neutral',
                'scores': scores
            }
        return {'sentiment': 'unknown', 'scores': {}}
    
    async def translate_text(self, text: str, target_lang: str = 'en') -> str:
        """Translate text"""
        try:
            return self.translator.translate(text, dest=target_lang).text
        except:
            return text
    
    async def extract_entities(self, text: str) -> dict:
        """Extract entities from text"""
        if self.nlp:
            doc = self.nlp(text)
            entities = {}
            for ent in doc.ents:
                if ent.label_ not in entities:
                    entities[ent.label_] = []
                entities[ent.label_].append(ent.text)
            return entities
        return {}

class BotAnalytics:
    """Advanced analytics for bots"""
    
    def __init__(self):
        self.registry = CollectorRegistry()
        self.bot_counter = Counter('bots_total', 'Total bots', registry=self.registry)
        self.deployment_counter = Counter('deployments_total', 'Total deployments', registry=self.registry)
        self.active_bots_gauge = Gauge('active_bots', 'Active bots', registry=self.registry)
    
    def track_deployment(self, user_id: int, bot_name: str):
        """Track bot deployment"""
        self.deployment_counter.inc()
        self.bot_counter.inc()
        
        # Log to database
        with db.get_connection() as conn:
            c = conn.cursor()
            c.execute("""INSERT INTO analytics (date, total_bots, running_bots) 
                        VALUES (?, ?, ?)""",
                     (datetime.now().strftime('%Y-%m-%d'), 1, 1))
            conn.commit()
    
    def get_metrics(self) -> dict:
        """Get current metrics"""
        return {
            'total_bots': self.bot_counter._value.get(),
            'total_deployments': self.deployment_counter._value.get(),
            'active_bots': self.active_bots_gauge._value.get()
        }
    
    def generate_report(self, days: int = 30) -> dict:
        """Generate analytics report"""
        with db.get_connection() as conn:
            c = conn.cursor()
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Get daily stats
            c.execute("""SELECT date, total_users, active_users, total_bots, total_deployments 
                        FROM analytics WHERE date >= ? ORDER BY date""", 
                     (start_date.strftime('%Y-%m-%d'),))
            data = c.fetchall()
            
            # Convert to DataFrame for analysis
            df = pd.DataFrame(data, columns=['date', 'total_users', 'active_users', 'total_bots', 'total_deployments'])
            
            return {
                'daily_data': df.to_dict('records'),
                'summary': {
                    'total_users': df['total_users'].max() if not df.empty else 0,
                    'avg_active': df['active_users'].mean() if not df.empty else 0,
                    'total_bots': df['total_bots'].max() if not df.empty else 0,
                    'growth_rate': self._calculate_growth(df['total_bots']) if not df.empty else 0
                }
            }
    
    def _calculate_growth(self, series) -> float:
        """Calculate growth rate"""
        if len(series) < 2:
            return 0
        first = series.iloc[0]
        last = series.iloc[-1]
        if first == 0:
            return 0
        return ((last - first) / first) * 100

class PaymentProcessor:
    """Handle payments and subscriptions"""
    
    def __init__(self):
        # Initialize payment gateways
        if Config.STRIPE_API_KEY:
            stripe.api_key = Config.STRIPE_API_KEY
        
        if Config.PAYPAL_CLIENT_ID:
            paypalrestsdk.configure({
                "mode": "sandbox",
                "client_id": Config.PAYPAL_CLIENT_ID,
                "client_secret": Config.PAYPAL_SECRET
            })
        
        if Config.RAZORPAY_KEY_ID:
            self.razorpay_client = razorpay.Client(auth=(Config.RAZORPAY_KEY_ID, Config.RAZORPAY_SECRET))
        
        if Config.COINBASE_API_KEY:
            self.coinbase_client = CoinbaseClient(api_key=Config.COINBASE_API_KEY)
    
    def create_payment_intent(self, amount: float, currency: str = "USD", user_id: int) -> dict:
        """Create payment intent"""
        try:
            if Config.STRIPE_API_KEY:
                intent = stripe.PaymentIntent.create(
                    amount=int(amount * 100),
                    currency=currency.lower(),
                    metadata={'user_id': user_id}
                )
                return {
                    'client_secret': intent.client_secret,
                    'payment_id': intent.id
                }
        except Exception as e:
            return {'error': str(e)}
    
    def create_subscription(self, user_id: int, plan: str) -> dict:
        """Create subscription"""
        plans = {
            'basic': {'days': 30, 'price': 9.99, 'bots': 5},
            'pro': {'days': 90, 'price': 24.99, 'bots': 20},
            'enterprise': {'days': 365, 'price': 99.99, 'bots': 100}
        }
        
        if plan not in plans:
            return {'error': 'Invalid plan'}
        
        plan_data = plans[plan]
        expiry = (datetime.now() + timedelta(days=plan_data['days'])).strftime('%Y-%m-%d %H:%M:%S')
        
        with db.get_connection() as conn:
            c = conn.cursor()
            c.execute("UPDATE users SET expiry=?, file_limit=? WHERE id=?", 
                     (expiry, plan_data['bots'], user_id))
            conn.commit()
        
        return {
            'success': True,
            'expiry': expiry,
            'bots_limit': plan_data['bots']
        }

class Web3Manager:
    """Blockchain and Web3 integration"""
    
    def __init__(self):
        if Config.WEB3_INFURA_URL:
            self.w3 = Web3(Web3.HTTPProvider(Config.WEB3_INFURA_URL))
        else:
            self.w3 = None
    
    def create_wallet(self) -> dict:
        """Create Ethereum wallet"""
        if not self.w3:
            return {'error': 'Web3 not configured'}
        
        account = self.w3.eth.account.create()
        return {
            'address': account.address,
            'private_key': account.key.hex(),
            'mnemonic': None
        }
    
    def get_balance(self, address: str) -> float:
        """Get ETH balance"""
        if not self.w3:
            return 0
        try:
            balance = self.w3.eth.get_balance(address)
            return self.w3.from_wei(balance, 'ether')
        except:
            return 0
    
    def create_nft(self, name: str, description: str, image_url: str) -> dict:
        """Create NFT metadata"""
        metadata = {
            "name": name,
            "description": description,
            "image": image_url,
            "attributes": [
                {"trait_type": "Created by", "value": "Aurpon Bot Host"},
                {"trait_type": "Date", "value": datetime.now().strftime('%Y-%m-%d')}
            ]
        }
        return metadata

class SocialMediaManager:
    """Social media integration"""
    
    def __init__(self):
        # Telegram client
        self.tg_client = TelegramClient('session', api_id, api_hash) if hasattr(Config, 'API_ID') else None
        
        # Twitter client
        if hasattr(Config, 'TWITTER_API_KEY'):
            auth = tweepy.OAuthHandler(Config.TWITTER_API_KEY, Config.TWITTER_API_SECRET)
            auth.set_access_token(Config.TWITTER_ACCESS_TOKEN, Config.TWITTER_ACCESS_SECRET)
            self.twitter = tweepy.API(auth)
        
        # Instagram bot
        self.insta_bot = InstaBot() if hasattr(Config, 'INSTA_USERNAME') else None
    
    async def post_to_social(self, content: str, platforms: list) -> dict:
        """Post to multiple social platforms"""
        results = {}
        
        if 'telegram' in platforms and self.tg_client:
            try:
                await self.tg_client.send_message('channel', content)
                results['telegram'] = 'success'
            except Exception as e:
                results['telegram'] = str(e)
        
        if 'twitter' in platforms and hasattr(self, 'twitter'):
            try:
                self.twitter.update_status(content)
                results['twitter'] = 'success'
            except Exception as e:
                results['twitter'] = str(e)
        
        return results

class MLModelManager:
    """Machine learning model management"""
    
    def __init__(self):
        self.models = {}
        self.load_models()
    
    def load_models(self):
        """Load pre-trained models"""
        try:
            # Load sentiment analysis model
            self.models['sentiment'] = transformers.pipeline('sentiment-analysis')
        except:
            pass
    
    def analyze_image(self, image_path: str) -> dict:
        """Analyze image using DeepFace"""
        try:
            result = DeepFace.analyze(img_path=image_path, actions=['age', 'gender', 'emotion'])
            return result[0] if result else {}
        except:
            return {}
    
    def transcribe_audio(self, audio_path: str) -> str:
        """Transcribe audio using Whisper"""
        try:
            model = whisper.load_model("base")
            result = model.transcribe(audio_path)
            return result["text"]
        except:
            return ""
    
    def generate_wordcloud(self, text: str) -> BytesIO:
        """Generate word cloud from text"""
        wordcloud = WordCloud(width=800, height=400, background_color='white').generate(text)
        
        img_buffer = BytesIO()
        wordcloud.to_image().save(img_buffer, format='PNG')
        img_buffer.seek(0)
        return img_buffer

class BackupManager:
    """Advanced backup management"""
    
    def __init__(self):
        self.backup_dir = Path(Config.BACKUP_DIR)
        
        # Cloud storage clients
        if Config.AWS_ACCESS_KEY:
            self.s3 = boto3.client('s3', 
                                   aws_access_key_id=Config.AWS_ACCESS_KEY,
                                   aws_secret_access_key=Config.AWS_SECRET_KEY)
        
        if Config.AZURE_CONNECTION_STRING:
            self.azure = BlobServiceClient.from_connection_string(Config.AZURE_CONNECTION_STRING)
        
        if Config.GCP_CREDENTIALS:
            self.gcp = storage.Client.from_service_account_json(Config.GCP_CREDENTIALS)
    
    def create_backup(self, backup_type: str = 'full') -> dict:
        """Create system backup"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = self.backup_dir / f"backup_{backup_type}_{timestamp}"
        
        try:
            # Backup database
            shutil.copy2(Config.DB_NAME, backup_path / 'database.db')
            
            # Backup projects
            shutil.copytree(Config.PROJECT_DIR, backup_path / 'projects')
            
            # Backup configs
            shutil.copytree(Config.LOGS_DIR, backup_path / 'logs')
            
            # Create metadata
            metadata = {
                'type': backup_type,
                'timestamp': timestamp,
                'version': Config.VERSION,
                'files': [str(f) for f in backup_path.rglob('*') if f.is_file()]
            }
            
            with open(backup_path / 'metadata.json', 'w') as f:
                json.dump(metadata, f)
            
            # Create zip archive
            zip_path = self.backup_dir / f"backup_{backup_type}_{timestamp}.zip"
            shutil.make_archive(str(zip_path).replace('.zip', ''), 'zip', backup_path)
            
            # Upload to cloud
            self.upload_to_cloud(zip_path)
            
            # Cleanup
            shutil.rmtree(backup_path)
            
            return {
                'success': True,
                'path': str(zip_path),
                'size': zip_path.stat().st_size
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def upload_to_cloud(self, file_path: Path):
        """Upload backup to cloud storage"""
        try:
            if hasattr(self, 's3'):
                self.s3.upload_file(str(file_path), Config.AWS_BUCKET_NAME, file_path.name)
            
            if hasattr(self, 'azure'):
                container = self.azure.get_container_client('backups')
                with open(file_path, 'rb') as data:
                    container.upload_blob(name=file_path.name, data=data)
            
            if hasattr(self, 'gcp'):
                bucket = self.gcp.bucket(Config.GCP_BUCKET_NAME)
                blob = bucket.blob(f"backups/{file_path.name}")
                blob.upload_from_filename(str(file_path))
        except Exception as e:
            logger.error(f"Cloud upload failed: {e}")

# ================== Enhanced Keyboards ==================
class AdvancedKeyboards:
    @staticmethod
    def main_menu(user_id: int) -> types.ReplyKeyboardMarkup:
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        
        buttons = [
            "📤 Upload Bot", "🤖 My Bots", "🚀 Deploy Bot",
            "📊 Dashboard", "💰 Buy Credits", "🎨 Templates",
            "🤖 AI Assistant", "📈 Analytics", "⚙️ Settings",
            "🔗 Social Media", "💎 NFT Creator", "🌐 Web3",
            "🎵 Audio Tools", "🖼️ Image Tools", "📝 Text Tools",
            "📧 Email Tools", "☁️ Cloud Storage", "🔐 Security",
            "❓ Help", "ℹ️ About"
        ]
        
        if user_id == Config.ADMIN_ID:
            buttons.extend(["👑 Admin Panel", "📊 Full Analytics", "💾 Backup"])
        
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
            types.InlineKeyboardButton("📝 Logs", callback_data=f"logs_{bot_id}"),
            types.InlineKeyboardButton("⚙️ Config", callback_data=f"config_{bot_id}"),
            types.InlineKeyboardButton("📈 Monitor", callback_data=f"monitor_{bot_id}")
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
            types.InlineKeyboardButton("💾 Backup", callback_data="admin_backup"),
            types.InlineKeyboardButton("💰 Revenue", callback_data="admin_revenue"),
            types.InlineKeyboardButton("🤖 Bot Templates", callback_data="admin_templates"),
            types.InlineKeyboardButton("🌐 System Logs", callback_data="admin_logs"),
            types.InlineKeyboardButton("🔧 Maintenance", callback_data="admin_maintenance")
        )
        return markup

# ================== Message Handlers ==================
@bot.message_handler(commands=['start'])
def welcome(message):
    uid = message.from_user.id
    username = message.from_user.username or "User"
    
    user = db.get_user(uid)
    if not user and uid != Config.ADMIN_ID:
        join_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        expiry_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
        with db.get_connection() as conn:
            c = conn.cursor()
            c.execute("""INSERT INTO users 
                        (id, username, expiry, file_limit, is_prime, join_date, last_login, credits) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                     (uid, username, expiry_date, 10, 0, join_date, join_date, 100))
        user = db.get_user(uid)
    
    stats = get_system_stats()
    
    text = f"""
✨ <b>{Config.BRAND_NAME} v{Config.VERSION}</b> ✨
<b>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</b>

👤 <b>User:</b> @{username}
🆔 <b>ID:</b> <code>{uid}</code>
💎 <b>Status:</b> 👑 PRIME ADMIN
💰 <b>Credits:</b> {user[14] if user else 0}
📦 <b>File Limit:</b> {user[3] if user else 0} files

<b>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</b>

🖥️ <b>System Status:</b>
• <b>CPU:</b> {create_progress_bar(stats['cpu_percent'])} {stats['cpu_percent']:.1f}%
• <b>RAM:</b> {create_progress_bar(stats['ram_percent'])} {stats['ram_percent']:.1f}%
• <b>Disk:</b> {create_progress_bar(stats['disk_percent'])} {stats['disk_percent']:.1f}%
• <b>Uptime:</b> {format_uptime(int(stats['uptime']))}

<b>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</b>
💡 Use the buttons below to access all features!
"""
    bot.send_message(message.chat.id, text, reply_markup=AdvancedKeyboards.main_menu(uid))

@bot.message_handler(func=lambda message: message.text == "🤖 AI Assistant")
def ai_assistant(message):
    msg = bot.reply_to(message, "🤖 AI Assistant\n\nWhat would you like me to help with?\n\nSend me your request (e.g., 'Create a weather bot')")
    bot.register_next_step_handler(msg, process_ai_request)

async def process_ai_request(message):
    request_text = message.text
    ai = AIAssistant()
    
    bot.send_message(message.chat.id, "🤖 Generating response... Please wait.")
    
    if "bot" in request_text.lower() or "create" in request_text.lower():
        code = await ai.generate_bot_code(request_text)
        
        # Save generated code
        filename = f"ai_generated_{uuid.uuid4().hex[:8]}.py"
        file_path = project_path / filename
        file_path.write_text(code)
        
        # Save to database
        with db.get_connection() as conn:
            c = conn.cursor()
            c.execute("""INSERT INTO deployments 
                        (user_id, bot_name, filename, status, last_active) 
                        VALUES (?, ?, ?, ?, ?)""",
                     (message.from_user.id, "AI Generated Bot", filename, "Uploaded", 
                      datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            conn.commit()
        
        bot.send_document(message.chat.id, open(file_path, 'rb'), 
                         caption=f"✅ Bot generated successfully!\n\nUse 'Deploy Bot' to start it.")
    else:
        # Analyze sentiment
        sentiment = await ai.analyze_sentiment(request_text)
        translation = await ai.translate_text(request_text)
        entities = await ai.extract_entities(request_text)
        
        response = f"""
📊 <b>Analysis Results</b>
<b>━━━━━━━━━━━━━━━━━━━━━━</b>

🎭 <b>Sentiment:</b> {sentiment['sentiment'].upper()}
📈 <b>Confidence:</b> {sentiment['scores'].get('compound', 0):.2f}

🌐 <b>Translation:</b>
{translation}

🏷️ <b>Entities:</b>
{json.dumps(entities, indent=2) if entities else 'None detected'}

<b>━━━━━━━━━━━━━━━━━━━━━━</b>
"""
        bot.send_message(message.chat.id, response)

@bot.message_handler(func=lambda message: message.text == "💰 Buy Credits")
def buy_credits(message):
    text = """
💰 <b>BUY CREDITS</b>
<b>━━━━━━━━━━━━━━━━━━━━━━</b>

Select a package:

<b>💎 Basic Pack - $4.99</b>
• 100 Credits
• 30 Days Access
• 5 Bots Limit

<b>💎 Pro Pack - $9.99</b>
• 250 Credits
• 90 Days Access
• 20 Bots Limit

<b>💎 Enterprise Pack - $19.99</b>
• 1000 Credits
• 365 Days Access
• Unlimited Bots

<b>━━━━━━━━━━━━━━━━━━━━━━</b>
Select a package to proceed:
"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("💎 Basic - $4.99", callback_data="buy_basic"),
        types.InlineKeyboardButton("🚀 Pro - $9.99", callback_data="buy_pro"),
        types.InlineKeyboardButton("👑 Enterprise - $19.99", callback_data="buy_enterprise")
    )
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "🎨 Templates")
def show_templates(message):
    with db.get_connection() as conn:
        c = conn.cursor()
        templates = c.execute("SELECT id, name, description, downloads, rating FROM templates WHERE is_public=1 ORDER BY downloads DESC LIMIT 10").fetchall()
    
    if not templates:
        bot.reply_to(message, "No templates available yet.")
        return
    
    text = "<b>🎨 POPULAR TEMPLATES</b>\n<b>━━━━━━━━━━━━━━━━━━━━━━</b>\n\n"
    
    for t in templates:
        text += f"<b>{t[1]}</b>\n"
        text += f"📝 {t[2][:50]}...\n"
        text += f"⭐ {t[4]:.1f} | 📥 {t[3]} downloads\n\n"
    
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda message: message.text == "📈 Analytics")
def show_analytics(message):
    analytics = BotAnalytics()
    report = analytics.generate_report(7)
    
    text = f"""
📊 <b>WEEKLY ANALYTICS</b>
<b>━━━━━━━━━━━━━━━━━━━━━━</b>

👥 <b>Users:</b> {report['summary']['total_users']}
📈 <b>Growth:</b> {report['summary']['growth_rate']:.1f}%
🤖 <b>Total Bots:</b> {report['summary']['total_bots']}
📊 <b>Avg Active:</b> {report['summary']['avg_active']:.0f}

<b>━━━━━━━━━━━━━━━━━━━━━━</b>

📅 <b>Daily Breakdown:</b>
"""
    
    for day in report['daily_data'][-7:]:
        text += f"\n{day['date']}: {day['total_bots']} bots | {day['active_users']} active"
    
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda message: message.text == "💎 NFT Creator")
def nft_creator(message):
    msg = bot.reply_to(message, "💎 NFT Creator\n\nSend me an image to create an NFT")
    bot.register_next_step_handler(msg, process_nft_creation)

def process_nft_creation(message):
    if message.content_type != 'photo':
        bot.reply_to(message, "Please send a photo!")
        return
    
    web3_manager = Web3Manager()
    
    # Get the largest photo
    photo = message.photo[-1]
    file_info = bot.get_file(photo.file_id)
    downloaded = bot.download_file(file_info.file_path)
    
    # Save image
    image_path = Config.TEMP_DIR / f"nft_{uuid.uuid4().hex}.jpg"
    image_path.write_bytes(downloaded)
    
    # Create NFT metadata
    metadata = web3_manager.create_nft(
        name=f"Aurpon NFT #{uuid.uuid4().hex[:8]}",
        description="Created with Aurpon Bot Host",
        image_url=str(image_path)
    )
    
    # Save metadata
    metadata_path = Config.TEMP_DIR / f"metadata_{uuid.uuid4().hex}.json"
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f)
    
    # Send back to user
    with open(metadata_path, 'rb') as f:
        bot.send_document(message.chat.id, f, 
                         caption="✅ NFT Metadata Created!\n\nYou can now mint this NFT on any blockchain.")
    
    # Cleanup
    image_path.unlink()
    metadata_path.unlink()

@bot.message_handler(func=lambda message: message.text == "🎵 Audio Tools")
def audio_tools(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🎤 Speech to Text", callback_data="audio_stt"),
        types.InlineKeyboardButton("🔊 Text to Speech", callback_data="audio_tts"),
        types.InlineKeyboardButton("🎵 Music Analysis", callback_data="audio_music"),
        types.InlineKeyboardButton("📝 Transcription", callback_data="audio_transcribe")
    )
    bot.send_message(message.chat.id, "🎵 Audio Tools\n\nSelect an option:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "🖼️ Image Tools")
def image_tools(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🔍 Analyze Face", callback_data="image_face"),
        types.InlineKeyboardButton("🎨 Generate Art", callback_data="image_art"),
        types.InlineKeyboardButton("✏️ Remove BG", callback_data="image_remove_bg"),
        types.InlineKeyboardButton("🖌️ Enhance", callback_data="image_enhance")
    )
    bot.send_message(message.chat.id, "🖼️ Image Tools\n\nSelect an option:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "🌐 Web3")
def web3_tools(message):
    w3_manager = Web3Manager()
    wallet = w3_manager.create_wallet()
    
    if 'error' in wallet:
        bot.reply_to(message, "Web3 not configured. Please contact admin.")
        return
    
    text = f"""
🌐 <b>WEB3 WALLET CREATED</b>
<b>━━━━━━━━━━━━━━━━━━━━━━</b>

📫 <b>Address:</b>
<code>{wallet['address']}</code>

🔑 <b>Private Key:</b>
<code>{wallet['private_key'][:20]}...</code>

<b>━━━━━━━━━━━━━━━━━━━━━━</b>
⚠️ Keep your private key safe!
"""
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda message: message.text == "🔐 Security")
def security_settings(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🔑 2FA Setup", callback_data="security_2fa"),
        types.InlineKeyboardButton("🔒 Change Password", callback_data="security_password"),
        types.InlineKeyboardButton("📱 API Keys", callback_data="security_api"),
        types.InlineKeyboardButton("🔐 Session Control", callback_data="security_session")
    )
    bot.send_message(message.chat.id, "🔐 Security Settings\n\nSelect an option:", reply_markup=markup)

# ================== Callback Handlers ==================
@bot.callback_query_handler(func=lambda call: True)
def handle_all_callbacks(call):
    action = call.data
    
    if action.startswith("buy_"):
        plan = action.replace("buy_", "")
        processor = PaymentProcessor()
        result = processor.create_subscription(call.from_user.id, plan)
        
        if result.get('success'):
            bot.answer_callback_query(call.id, "Purchase successful!")
            bot.send_message(call.message.chat.id, 
                           f"✅ Subscription activated!\nExpires: {result['expiry']}")
        else:
            bot.answer_callback_query(call.id, "Purchase failed!")
    
    elif action.startswith("audio_"):
        if action == "audio_stt":
            msg = bot.send_message(call.message.chat.id, "Send me an audio file to transcribe")
            bot.register_next_step_handler(msg, transcribe_audio)
        elif action == "audio_tts":
            msg = bot.send_message(call.message.chat.id, "Send me text to convert to speech")
            bot.register_next_step_handler(msg, text_to_speech)
    
    elif action.startswith("image_"):
        if action == "image_face":
            msg = bot.send_message(call.message.chat.id, "Send me a photo for face analysis")
            bot.register_next_step_handler(msg, analyze_face)
        elif action == "image_art":
            msg = bot.send_message(call.message.chat.id, "Describe the art you want to generate")
            bot.register_next_step_handler(msg, generate_art)
    
    elif action.startswith("security_"):
        if action == "security_2fa":
            setup_2fa(call)
    
    bot.answer_callback_query(call.id)

def transcribe_audio(message):
    if message.audio or message.voice:
        ml = MLModelManager()
        
        # Download audio
        file_id = message.audio.file_id if message.audio else message.voice.file_id
        file_info = bot.get_file(file_id)
        downloaded = bot.download_file(file_info.file_path)
        
        audio_path = Config.TEMP_DIR / f"audio_{uuid.uuid4().hex}.ogg"
        audio_path.write_bytes(downloaded)
        
        # Transcribe
        text = ml.transcribe_audio(str(audio_path))
        
        bot.send_message(message.chat.id, f"📝 Transcription:\n\n{text}")
        
        # Cleanup
        audio_path.unlink()
    else:
        bot.reply_to(message, "Please send an audio file!")

def text_to_speech(message):
    text = message.text
    tts = gTTS(text=text, lang='en')
    
    audio_path = Config.TEMP_DIR / f"tts_{uuid.uuid4().hex}.mp3"
    tts.save(str(audio_path))
    
    with open(audio_path, 'rb') as f:
        bot.send_audio(message.chat.id, f)
    
    audio_path.unlink()

def analyze_face(message):
    if message.photo:
        ml = MLModelManager()
        
        # Download photo
        photo = message.photo[-1]
        file_info = bot.get_file(photo.file_id)
        downloaded = bot.download_file(file_info.file_path)
        
        image_path = Config.TEMP_DIR / f"face_{uuid.uuid4().hex}.jpg"
        image_path.write_bytes(downloaded)
        
        # Analyze
        result = ml.analyze_image(str(image_path))
        
        if result:
            text = f"""
🔍 <b>Face Analysis Results</b>
<b>━━━━━━━━━━━━━━━━━━━━━━</b>

🎂 <b>Age:</b> {result.get('age', 'N/A')}
⚧️ <b>Gender:</b> {result.get('gender', 'N/A')}
😊 <b>Emotion:</b> {result.get('dominant_emotion', 'N/A')}

<b>━━━━━━━━━━━━━━━━━━━━━━</b>
"""
            bot.send_message(message.chat.id, text)
        
        image_path.unlink()
    else:
        bot.reply_to(message, "Please send a photo!")

def setup_2fa(call):
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(call.from_user.username, issuer_name="Aurpon Bot")
    
    # Generate QR code
    qr = qrcode.make(provisioning_uri)
    qr_path = Config.TEMP_DIR / f"2fa_{uuid.uuid4().hex}.png"
    qr.save(qr_path)
    
    with open(qr_path, 'rb') as f:
        bot.send_photo(call.message.chat.id, f, 
                      caption="Scan this QR code with Google Authenticator")
    
    # Store secret in database
    with db.get_connection() as conn:
        c = conn.cursor()
        c.execute("UPDATE users SET two_factor_secret=?, two_factor_enabled=1 WHERE id=?", 
                 (secret, call.from_user.id))
        conn.commit()
    
    qr_path.unlink()

# ================== Admin Handlers ==================
@bot.message_handler(func=lambda message: message.text == "👑 Admin Panel" and message.from_user.id == Config.ADMIN_ID)
def admin_panel(message):
    bot.send_message(message.chat.id, "👑 Admin Panel", reply_markup=AdvancedKeyboards.admin_panel())

@bot.message_handler(func=lambda message: message.text == "📊 Full Analytics" and message.from_user.id == Config.ADMIN_ID)
def full_analytics(message):
    analytics = BotAnalytics()
    report = analytics.generate_report(30)
    
    # Generate visualization
    if report['daily_data']:
        df = pd.DataFrame(report['daily_data'])
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df['date'], y=df['total_bots'], name='Total Bots'))
        fig.add_trace(go.Scatter(x=df['date'], y=df['active_users'], name='Active Users'))
        fig.update_layout(title='Bot Analytics - 30 Days', xaxis_title='Date', yaxis_title='Count')
        
        # Save plot
        plot_path = Config.TEMP_DIR / f"analytics_{uuid.uuid4().hex}.html"
        fig.write_html(str(plot_path))
        
        with open(plot_path, 'rb') as f:
            bot.send_document(message.chat.id, f)
        
        plot_path.unlink()
    
    bot.send_message(message.chat.id, json.dumps(report['summary'], indent=2))

@bot.message_handler(func=lambda message: message.text == "💾 Backup" and message.from_user.id == Config.ADMIN_ID)
def backup_command(message):
    backup_mgr = BackupManager()
    result = backup_mgr.create_backup()
    
    if result['success']:
        with open(result['path'], 'rb') as f:
            bot.send_document(message.chat.id, f, 
                            caption=f"✅ Backup created!\nSize: {result['size'] / (1024*1024):.2f} MB")
    else:
        bot.send_message(message.chat.id, f"❌ Backup failed: {result['error']}")

# ================== Background Tasks ==================
def cleanup_processes():
    """Clean up orphaned processes"""
    with db.get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT id, pid FROM deployments WHERE status='Running'")
        running_bots = c.fetchall()
        
        for bot_id, pid in running_bots:
            if pid:
                try:
                    os.kill(pid, 0)
                except OSError:
                    c.execute("UPDATE deployments SET status='Stopped', pid=0 WHERE id=?", (bot_id,))
        conn.commit()

def update_analytics():
    """Update daily analytics"""
    with db.get_connection() as conn:
        c = conn.cursor()
        total_users = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        active_users = c.execute("SELECT COUNT(*) FROM users WHERE expiry > datetime('now')").fetchone()[0]
        total_bots = c.execute("SELECT COUNT(*) FROM deployments").fetchone()[0]
        running_bots = c.execute("SELECT COUNT(*) FROM deployments WHERE status='Running'").fetchone()[0]
        
        c.execute("""INSERT INTO analytics 
                    (date, total_users, active_users, total_bots, running_bots) 
                    VALUES (?, ?, ?, ?, ?)""",
                 (datetime.now().strftime('%Y-%m-%d'), total_users, active_users, total_bots, running_bots))
        conn.commit()

def schedule_tasks():
    """Schedule background tasks"""
    scheduler = BackgroundScheduler()
    scheduler.add_job(cleanup_processes, 'interval', minutes=5)
    scheduler.add_job(update_analytics, 'interval', hours=24)
    scheduler.add_job(lambda: BackupManager().create_backup(), 'interval', hours=24)
    scheduler.start()

# ================== Flask Web Server ==================
@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "brand": Config.BRAND_NAME,
        "version": Config.VERSION,
        "features": [
            "AI Bot Generation",
            "Blockchain Integration",
            "Social Media Management",
            "ML/AI Tools",
            "Payment Processing",
            "Advanced Analytics"
        ]
    })

@app.route('/api/stats')
def api_stats():
    stats = get_system_stats()
    with db.get_connection() as conn:
        c = conn.cursor()
        total_users = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        total_bots = c.execute("SELECT COUNT(*) FROM deployments").fetchone()[0]
        running_bots = c.execute("SELECT COUNT(*) FROM deployments WHERE status='Running'").fetchone()[0]
    
    return jsonify({
        "system": stats,
        "users": total_users,
        "bots": {"total": total_bots, "running": running_bots},
        "version": Config.VERSION
    })

@app.route('/api/metrics')
def metrics_endpoint():
    analytics = BotAnalytics()
    return generate_latest(analytics.registry)

# ================== Main Application ==================
def start_bot():
    logger.info(f"Starting bot {Config.BOT_USERNAME} v{Config.VERSION}")
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
    schedule_tasks()
    
    # Start bot in background
    threading.Thread(target=start_bot, daemon=True).start()
    
    # Start Flask server
    port = int(os.environ.get('PORT', Config.PORT))
    logger.info(f"Starting Flask server on 0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)
