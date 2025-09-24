# File: database.py (Dengan Tambahan Tabel Users)
import sqlite3
from datetime import datetime
import hashlib

DATABASE_FILE = "weighing_system.db"

def init_db():
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT, transaction_id TEXT NOT NULL UNIQUE, plate_number TEXT NOT NULL,
        goods_type TEXT, driver_name TEXT, vendor TEXT, customer TEXT, quantity TEXT, status TEXT NOT NULL,
        first_weigh_kg REAL NOT NULL, second_weigh_kg REAL, net_weigh_kg REAL,
        first_weigh_timestamp TEXT NOT NULL, second_weigh_timestamp TEXT,
        goods_origin TEXT, goods_destination TEXT, remake TEXT
    )""")
    
    # --- KODE BARU DITAMBAHKAN DI SINI ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL
    )""")
    
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        password_hash = hashlib.sha256('fakhriganteng24'.encode()).hexdigest()
        cursor.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)", 
                       ('admin', password_hash, 'Administrator'))
        print("Default 'admin' user created.")
    # ------------------------------------

    conn.commit()
    print("Database initialized successfully.")
    return conn

# --- FUNGSI BARU DITAMBAHKAN DI SINI ---
def verify_user(conn, username, password):
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ? AND password_hash = ?", (username, password_hash))
    return cursor.fetchone() is not None

def get_all_users(conn):
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, role FROM users")
    return cursor.fetchall()

def add_user(conn, username, password, role):
    try:
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)", (username, password_hash, role))
        conn.commit()
        return True
    except sqlite3.IntegrityError: return False

def delete_user(conn, user_id):
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    return cursor.rowcount > 0
# ------------------------------------

# ... (Sisa fungsi lainnya tidak berubah)
def generate_transaction_id(conn):
    cursor = conn.cursor(); cursor.execute("SELECT COUNT(*) FROM transactions WHERE DATE(first_weigh_timestamp) = DATE('now', 'localtime')"); count = cursor.fetchone()[0]
    today_str = datetime.now().strftime("%y%m%d"); new_id = f"W{today_str}{count + 1:04d}"; return new_id
def create_first_weigh(conn, data):
    try:
        new_id = generate_transaction_id(conn); timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S"); cursor = conn.cursor()
        query = "INSERT INTO transactions (transaction_id, plate_number, goods_type, driver_name, vendor, customer, quantity, status, first_weigh_kg, first_weigh_timestamp, goods_origin, goods_destination, remake) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        cursor.execute(query, (new_id, data['plate_number'], data['goods_type'], data['driver_name'], data['vendor'], data['customer'], data['quantity'], 'PENDING', data['weight'], timestamp, data['goods_origin'], data['goods_destination'], data['remake'])); conn.commit(); return True
    except Exception as e: print(f"Error in create_first_weigh: {e}"); return False
# Di dalam file database.py

# Di dalam file database.py

def complete_second_weigh(conn, transaction_id, second_weight, final_net_weight, remake_info):
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT first_weigh_kg FROM transactions WHERE transaction_id = ?", (transaction_id,))
        result = cursor.fetchone()
        if not result:
            return False

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Query diubah untuk mengupdate kolom 'remake' juga
        query = "UPDATE transactions SET second_weigh_kg = ?, net_weigh_kg = ?, status = 'COMPLETED', second_weigh_timestamp = ?, remake = ? WHERE transaction_id = ? AND status = 'PENDING'"
        cursor.execute(query, (second_weight, final_net_weight, timestamp, remake_info, transaction_id))
        
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"Error in complete_second_weigh: {e}")
        return False
def get_filtered_transactions(conn, start_date, end_date, goods_type=""):
    try:
        conn.row_factory = sqlite3.Row; cursor = conn.cursor()
        query = "SELECT * FROM transactions WHERE DATE(first_weigh_timestamp) BETWEEN ? AND ?"; params = [start_date, end_date]
        if goods_type: query += " AND goods_type LIKE ?"; params.append(f"%{goods_type}%")
        query += " ORDER BY first_weigh_timestamp DESC"; results = cursor.execute(query, params).fetchall(); return results
    except Exception as e: print(f"Error in get_filtered_transactions: {e}"); return []
def find_pending_by_plate_number(conn, plate_number):
    try:
        conn.row_factory = sqlite3.Row; cursor = conn.cursor(); query = "SELECT * FROM transactions WHERE plate_number = ? AND status = 'PENDING' ORDER BY first_weigh_timestamp DESC"
        result = cursor.execute(query, (plate_number,)).fetchone(); return result
    except Exception as e: print(f"Error in find_pending_by_plate_number: {e}"); return None
def get_transaction_by_id(conn, transaction_id):
    try:
        conn.row_factory = sqlite3.Row; cursor = conn.cursor(); query = "SELECT * FROM transactions WHERE transaction_id = ?"
        result = cursor.execute(query, (transaction_id,)).fetchone(); return result
    except Exception as e: print(f"Error in get_transaction_by_id: {e}"); return None
def delete_transaction_by_id(conn, transaction_id):
    try:
        cursor = conn.cursor(); query = "DELETE FROM transactions WHERE transaction_id = ?"; cursor.execute(query, (transaction_id,)); conn.commit(); return cursor.rowcount > 0
    except Exception as e: print(f"Error in delete_transaction_by_id: {e}"); return False