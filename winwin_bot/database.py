import sqlite3
import datetime
from config import Config

class Database:
    def __init__(self, db_name='winwin_bot.db'):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.create_tables()
    
    def create_tables(self):
        cursor = self.conn.cursor()
        
        # Таблица депозитов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS deposits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                amount REAL NOT NULL,
                status TEXT DEFAULT 'PENDING',
                payment_details TEXT,
                receipt_file_id TEXT,
                admin_message_id TEXT,
                user_message_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP,
                admin_id INTEGER
            )
        ''')
        
        # Таблица пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                balance REAL DEFAULT 0,
                deposits_count INTEGER DEFAULT 0,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица административных сообщений
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_messages (
                message_id INTEGER PRIMARY KEY,
                deposit_id INTEGER,
                admin_id INTEGER,
                FOREIGN KEY (deposit_id) REFERENCES deposits (id)
            )
        ''')
        
        self.conn.commit()
    
    def add_deposit(self, user_id, username, amount):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO deposits (user_id, username, amount, status)
            VALUES (?, ?, ?, 'PENDING')
        ''', (user_id, username, amount))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_deposit(self, deposit_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM deposits WHERE id = ?', (deposit_id,))
        return cursor.fetchone()
    
    def update_deposit_status(self, deposit_id, status, admin_id=None, payment_details=None):
        cursor = self.conn.cursor()
        
        if status == 'COMPLETED':
            cursor.execute('''
                UPDATE deposits 
                SET status = ?, processed_at = CURRENT_TIMESTAMP, admin_id = ?
                WHERE id = ?
            ''', (status, admin_id, deposit_id))
        elif payment_details:
            cursor.execute('''
                UPDATE deposits 
                SET status = ?, payment_details = ?, admin_id = ?
                WHERE id = ?
            ''', (status, payment_details, admin_id, deposit_id))
        else:
            cursor.execute('''
                UPDATE deposits 
                SET status = ?, admin_id = ?
                WHERE id = ?
            ''', (status, admin_id, deposit_id))
        
        self.conn.commit()
    
    def add_receipt(self, deposit_id, file_id):
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE deposits 
            SET receipt_file_id = ?, status = 'PROCESSING'
            WHERE id = ?
        ''', (file_id, deposit_id))
        self.conn.commit()
    
    def get_pending_deposits(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM deposits WHERE status = "PENDING"')
        return cursor.fetchall()
    
    def get_processing_deposits(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM deposits WHERE status = "PROCESSING"')
        return cursor.fetchall()
    
    def get_user_deposits(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM deposits 
            WHERE user_id = ? 
            ORDER BY created_at DESC
        ''', (user_id,))
        return cursor.fetchall()
    
    def add_or_update_user(self, user_id, username, full_name):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO users (user_id, username, full_name)
            VALUES (?, ?, ?)
        ''', (user_id, username, full_name))
        
        cursor.execute('''
            UPDATE users 
            SET username = ?, full_name = ?, last_activity = CURRENT_TIMESTAMP
            WHERE user_id = ?
        ''', (username, full_name, user_id))
        
        self.conn.commit()
    
    def get_user(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        return cursor.fetchone()
    
    def update_user_balance(self, user_id, amount):
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE users 
            SET balance = balance + ?, deposits_count = deposits_count + 1
            WHERE user_id = ?
        ''', (amount, user_id))
        self.conn.commit()
