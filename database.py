import sqlite3
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: str = "bot_database.db"):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        """Get database connection with proper settings"""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        return conn
    
    def init_database(self):
        """Initialize database tables"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Users table - simplified
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        first_name TEXT,
                        last_name TEXT,
                        platform_id TEXT UNIQUE,
                        id_status TEXT DEFAULT 'pending',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Signals table - simplified
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS signals (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        asset TEXT NOT NULL,
                        signal_type TEXT NOT NULL,
                        expiry_time TEXT NOT NULL,
                        entry_price TEXT NOT NULL,
                        target_price TEXT NOT NULL,
                        accuracy INTEGER NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                conn.commit()
                logger.info("Database initialized successfully")
                
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
    
    def add_user(self, user_id: int, username: str = None, first_name: str = None, last_name: str = None) -> bool:
        """Add new user to database"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR IGNORE INTO users (user_id, username, first_name, last_name)
                    VALUES (?, ?, ?, ?)
                """, (user_id, username, first_name, last_name))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error adding user {user_id}: {e}")
            return False
    
    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            return None
    
    def get_user_by_platform_id(self, platform_id: str) -> Optional[Dict[str, Any]]:
        """Get user by platform ID"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE platform_id = ?", (platform_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting user by platform_id {platform_id}: {e}")
            return None
    
    def set_platform_id(self, user_id: int, platform_id: str) -> bool:
        """Set platform ID for user"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE users 
                    SET platform_id = ?, id_status = 'pending', last_activity = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                """, (platform_id, user_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error setting platform_id for user {user_id}: {e}")
            return False
    
    def confirm_user_id(self, user_id: int) -> bool:
        """Confirm user access"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE users 
                    SET id_status = 'confirmed', last_activity = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                """, (user_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error confirming user {user_id}: {e}")
            return False
    
    def block_user(self, user_id: int) -> bool:
        """Block user"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE users 
                    SET id_status = 'blocked', last_activity = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                """, (user_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error blocking user {user_id}: {e}")
            return False
    
    def get_all_users_detailed(self) -> List[Dict[str, Any]]:
        """Get all users with details"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT user_id, username, first_name, last_name, platform_id, id_status, created_at, last_activity
                    FROM users
                    ORDER BY created_at DESC
                """)
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            return []
    
    def get_pending_users(self) -> List[Dict[str, Any]]:
        """Get users waiting for confirmation"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT user_id, username, first_name, last_name, platform_id
                    FROM users
                    WHERE id_status = 'pending' AND platform_id IS NOT NULL
                    ORDER BY created_at ASC
                """)
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting pending users: {e}")
            return []
    
    def get_confirmed_users(self) -> List[int]:
        """Get list of confirmed user IDs"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT user_id FROM users WHERE id_status = 'confirmed'")
                rows = cursor.fetchall()
                return [row['user_id'] for row in rows]
        except Exception as e:
            logger.error(f"Error getting confirmed users: {e}")
            return []
    
    def add_signal(self, asset: str, signal_type: str, expiry_time: str, 
                   entry_price: str, target_price: str, accuracy: int) -> int:
        """Add new signal to database"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO signals (asset, signal_type, expiry_time, entry_price, target_price, accuracy)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (asset, signal_type, expiry_time, entry_price, target_price, accuracy))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error adding signal: {e}")
            return 0
    
    def get_active_signals(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent active signals"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM signals
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (limit,))
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting active signals: {e}")
            return []
    
    def get_user_count(self) -> int:
        """Get total user count"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) as count FROM users")
                row = cursor.fetchone()
                return row['count'] if row else 0
        except Exception as e:
            logger.error(f"Error getting user count: {e}")
            return 0
    
    def get_confirmed_user_count(self) -> int:
        """Get confirmed user count"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) as count FROM users WHERE id_status = 'confirmed'")
                row = cursor.fetchone()
                return row['count'] if row else 0
        except Exception as e:
            logger.error(f"Error getting confirmed user count: {e}")
            return 0
    
    def update_user_activity(self, user_id: int) -> bool:
        """Update user's last activity"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE users 
                    SET last_activity = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                """, (user_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating user activity {user_id}: {e}")
            return False
    
    def cleanup_old_signals(self, days: int = 7) -> int:
        """Clean up old signals"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM signals 
                    WHERE created_at < datetime('now', '-{} days')
                """.format(days))
                conn.commit()
                return cursor.rowcount
        except Exception as e:
            logger.error(f"Error cleaning up old signals: {e}")
            return 0 