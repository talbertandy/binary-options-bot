import sqlite3
import datetime
from typing import List, Dict, Optional
import logging
from config import DATABASE_PATH

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.db_path = DATABASE_PATH
        self.init_database()
    
    def init_database(self):
        """Initialize database tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Users table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        first_name TEXT,
                        last_name TEXT,
                        platform_id TEXT, -- ID на платформе
                        id_status TEXT DEFAULT 'pending', -- 'pending', 'confirmed', 'blocked'
                        subscription_type TEXT DEFAULT 'free',
                        subscription_expires TIMESTAMP,
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Signals table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS signals (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        asset TEXT NOT NULL,
                        signal_type TEXT NOT NULL,
                        expiry_time TEXT NOT NULL,
                        entry_price REAL,
                        target_price REAL,
                        stop_loss REAL,
                        accuracy REAL,
                        status TEXT DEFAULT 'pending',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP,
                        result TEXT
                    )
                ''')
                
                # Signal results table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS signal_results (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        signal_id INTEGER,
                        user_id INTEGER,
                        result TEXT,
                        profit_loss REAL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (signal_id) REFERENCES signals (id),
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                ''')
                
                # Payments table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS payments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        amount REAL,
                        currency TEXT DEFAULT 'USD',
                        payment_method TEXT,
                        status TEXT DEFAULT 'pending',
                        subscription_type TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                ''')
                
                # Statistics table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS statistics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date DATE,
                        total_signals INTEGER DEFAULT 0,
                        successful_signals INTEGER DEFAULT 0,
                        total_users INTEGER DEFAULT 0,
                        active_subscriptions INTEGER DEFAULT 0,
                        total_revenue REAL DEFAULT 0
                    )
                ''')
                
                conn.commit()
                logger.info("Database initialized successfully")
                
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
    
    def add_user(self, user_id: int, username: str = None, first_name: str = None, last_name: str = None):
        """Add new user to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR IGNORE INTO users (user_id, username, first_name, last_name)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, username, first_name, last_name))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error adding user: {e}")
            return False
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        """Get user information"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
                user = cursor.fetchone()
                if user:
                    columns = [description[0] for description in cursor.description]
                    return dict(zip(columns, user))
                return None
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None
    
    def update_user_subscription(self, user_id: int, subscription_type: str, days: int):
        """Update user subscription"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                expires_at = datetime.datetime.now() + datetime.timedelta(days=days)
                cursor.execute('''
                    UPDATE users 
                    SET subscription_type = ?, subscription_expires = ?
                    WHERE user_id = ?
                ''', (subscription_type, expires_at, user_id))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error updating subscription: {e}")
            return False
    
    def is_user_subscribed(self, user_id: int) -> bool:
        """Check if user has active subscription"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT subscription_expires FROM users 
                    WHERE user_id = ? AND subscription_expires > datetime('now')
                ''', (user_id,))
                result = cursor.fetchone()
                return result is not None
        except Exception as e:
            logger.error(f"Error checking subscription: {e}")
            return False
    
    def add_signal(self, asset: str, signal_type: str, expiry_time: str, 
                   entry_price: float = None, target_price: float = None, 
                   stop_loss: float = None, accuracy: float = None) -> int:
        """Add new signal to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                expires_at = datetime.datetime.now() + datetime.timedelta(minutes=int(expiry_time[:-1]) if expiry_time.endswith('m') else int(expiry_time[:-1]) * 60)
                cursor.execute('''
                    INSERT INTO signals (asset, signal_type, expiry_time, entry_price, target_price, stop_loss, accuracy, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (asset, signal_type, expiry_time, entry_price, target_price, stop_loss, accuracy, expires_at))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error adding signal: {e}")
            return None
    
    def get_active_signals(self) -> List[Dict]:
        """Get all active signals"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM signals 
                    WHERE status = 'pending' AND expires_at > datetime('now')
                    ORDER BY created_at DESC
                ''')
                signals = cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                return [dict(zip(columns, signal)) for signal in signals]
        except Exception as e:
            logger.error(f"Error getting active signals: {e}")
            return []
    
    def update_signal_result(self, signal_id: int, result: str):
        """Update signal result"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE signals SET status = 'completed', result = ?
                    WHERE id = ?
                ''', (result, signal_id))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error updating signal result: {e}")
            return False
    
    def get_all_users(self) -> List[int]:
        """Get all user IDs"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT user_id FROM users WHERE is_active = TRUE')
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting users: {e}")
            return []
    
    def get_subscribed_users(self) -> List[int]:
        """Get all users with active subscriptions"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT user_id FROM users 
                    WHERE subscription_expires > datetime('now') AND is_active = TRUE
                ''')
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting subscribed users: {e}")
            return []
    
    def add_payment(self, user_id: int, amount: float, subscription_type: str, 
                   payment_method: str = 'manual') -> int:
        """Add payment record"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO payments (user_id, amount, subscription_type, payment_method)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, amount, subscription_type, payment_method))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error adding payment: {e}")
            return None
    
    def update_payment_status(self, payment_id: int, status: str):
        """Update payment status"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE payments SET status = ? WHERE id = ?
                ''', (status, payment_id))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error updating payment status: {e}")
            return False
    
    def set_platform_id(self, user_id: int, platform_id: str):
        """Сохраняет ID платформы для пользователя и сбрасывает статус на 'pending'"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users SET platform_id = ?, id_status = 'pending' WHERE user_id = ?
                ''', (platform_id, user_id))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error setting platform_id: {e}")
            return False

    def confirm_user_id(self, user_id: int):
        """Подтверждает ID пользователя (доступ к сигналам)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users SET id_status = 'confirmed' WHERE user_id = ?
                ''', (user_id,))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error confirming user id: {e}")
            return False

    def block_user(self, user_id: int):
        """Блокирует пользователя"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users SET id_status = 'blocked' WHERE user_id = ?
                ''', (user_id,))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error blocking user: {e}")
            return False

    def get_user_by_platform_id(self, platform_id: str) -> Optional[Dict]:
        """Получить пользователя по platform_id"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM users WHERE platform_id = ?', (platform_id,))
                user = cursor.fetchone()
                if user:
                    columns = [description[0] for description in cursor.description]
                    return dict(zip(columns, user))
                return None
        except Exception as e:
            logger.error(f"Error getting user by platform_id: {e}")
            return None

    def get_all_users_detailed(self) -> List[Dict]:
        """Get all users with detailed information"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT user_id, username, first_name, last_name, platform_id, id_status, 
                           subscription_type, subscription_expires, created_at, last_activity
                    FROM users 
                    WHERE is_active = TRUE
                    ORDER BY created_at DESC
                ''')
                users = cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                return [dict(zip(columns, user)) for user in users]
        except Exception as e:
            logger.error(f"Error getting detailed users: {e}")
            return []

    def get_pending_users(self) -> List[Dict]:
        """Get users with pending status"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT user_id, username, first_name, last_name, platform_id, id_status, created_at
                    FROM users 
                    WHERE id_status = 'pending' AND is_active = TRUE
                    ORDER BY created_at DESC
                ''')
                users = cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                return [dict(zip(columns, user)) for user in users]
        except Exception as e:
            logger.error(f"Error getting pending users: {e}")
            return [] 