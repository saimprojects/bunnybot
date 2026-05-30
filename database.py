import psycopg2
import os
from urllib.parse import urlparse

def get_db_connection():
    url = os.environ.get('DATABASE_URL')
    if not url:
        raise ValueError("DATABASE_URL environment variable is not set")
    
    # Handle both local (SQLite/Postgres) and Railway (Postgres)
    # For local testing, we might want to support SQLite or a local Postgres
    # But user specifically asked for Postgres on Railway
    
    conn = psycopg2.connect(url, sslmode='require' if 'railway.app' in url else 'prefer')
    return conn

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Create tables based on user requirements
    queries = [
        """
        CREATE TABLE IF NOT EXISTS users (
            id BIGINT PRIMARY KEY,
            username TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            balance FLOAT DEFAULT 0,
            total_orders INT DEFAULT 0,
            referrals INT DEFAULT 0,
            referral_earnings FLOAT DEFAULT 0
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS products (
            id SERIAL PRIMARY KEY,
            name TEXT,
            duration TEXT,
            price FLOAT,
            stock INT DEFAULT 0,
            description TEXT,
            features TEXT,
            warranty TEXT,
            category TEXT,
            is_active BOOLEAN DEFAULT TRUE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS product_items (
            id SERIAL PRIMARY KEY,
            product_id INT REFERENCES products(id),
            email TEXT,
            password TEXT,
            is_sold BOOLEAN DEFAULT FALSE,
            sold_at TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS orders (
            id TEXT PRIMARY KEY,
            user_id BIGINT REFERENCES users(id),
            product_id INT REFERENCES products(id),
            quantity INT,
            total_amount FLOAT,
            payment_method TEXT,
            status TEXT DEFAULT 'Confirmed',
            created_at TIMESTAMP DEFAULT NOW(),
            delivery_details JSONB
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS transactions (
            id SERIAL PRIMARY KEY,
            user_id BIGINT REFERENCES users(id),
            type TEXT,
            amount FLOAT,
            created_at TIMESTAMP DEFAULT NOW()
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS withdrawals (
            id SERIAL PRIMARY KEY,
            user_id BIGINT REFERENCES users(id),
            amount FLOAT,
            address TEXT,
            status TEXT DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT NOW()
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS pending_payments (
            id SERIAL PRIMARY KEY,
            user_id BIGINT,
            product_id INT,
            quantity INT,
            expected_amount FLOAT,
            created_at TIMESTAMP DEFAULT NOW(),
            expires_at TIMESTAMP,
            status TEXT DEFAULT 'pending'
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS support_messages (
            id SERIAL PRIMARY KEY,
            user_id BIGINT,
            message TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        )
        """
    ]
    
    for query in queries:
        cur.execute(query)
    
    conn.commit()
    cur.close()
    conn.close()

# Shared helper functions for bot and webapp
def get_user(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    return user

def create_user(user_id, username):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO users (id, username) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING", (user_id, username))
    conn.commit()
    cur.close()
    conn.close()

def get_products():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM products WHERE is_active = TRUE AND stock > 0")
    products = cur.fetchall()
    cur.close()
    conn.close()
    return products

def get_product(product_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM products WHERE id = %s", (product_id,))
    product = cur.fetchone()
    cur.close()
    conn.close()
    return product
