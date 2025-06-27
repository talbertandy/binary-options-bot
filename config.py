import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_USER_ID = int(os.getenv('ADMIN_USER_ID', 0))

# Database Configuration
DATABASE_PATH = 'bot_database.db'

# Subscription Plans (in days)
SUBSCRIPTION_PLANS = {
    'basic': 30,
    'premium': 90,
    'vip': 180
}

# Signal Configuration
SIGNAL_TYPES = ['CALL', 'PUT']
ASSETS = ['EUR/USD', 'GBP/USD', 'USD/JPY', 'USD/CHF', 'AUD/USD', 'USD/CAD']
EXPIRY_TIMES = ['1m', '5m', '15m', '30m', '1h']

# Payment Configuration
PAYMENT_TOKEN = os.getenv('PAYMENT_TOKEN')  # For payment processing
PAYMENT_PROVIDER = 'stripe'  # or 'yookassa', 'qiwi', etc.

# Logging Configuration
LOG_LEVEL = 'INFO'
LOG_FILE = 'bot.log'

# Signal Generation Settings
MIN_SIGNAL_INTERVAL = 30  # minutes
MAX_SIGNALS_PER_DAY = 20
SIGNAL_ACCURACY_THRESHOLD = 0.7  # 70% accuracy required 