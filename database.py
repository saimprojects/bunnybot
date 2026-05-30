import os
import psycopg2
from urllib.parse import urlparse

def get_db_connection():
    """Get database connection"""
    url = os.environ.get('DATABASE_URL')
    if not url:
        raise ValueError("DATABASE_URL environment variable is not set")
    
    try:
        # Parse the URL
        result = urlparse(url)
        
        # Check if it's PostgreSQL
        if 'postgres' in result.scheme:
            conn = psycopg2.connect(url, sslmode='require')
        else:
            conn = psycopg2.connect(url)
        
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        raise

def init_db():
    """Initialize database tables"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Create tables
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
            name TEXT NOT NULL,
            duration TEXT,
            price FLOAT DEFAULT 0,
            stock INT DEFAULT 0,
            description TEXT,
            features TEXT,
            warranty TEXT,
            category TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW()
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS product_items (
            id SERIAL PRIMARY KEY,
            product_id INT REFERENCES products(id) ON DELETE CASCADE,
            email TEXT NOT NULL,
            password TEXT NOT NULL,
            is_sold BOOLEAN DEFAULT FALSE,
            sold_at TIMESTAMP,
            order_id TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS orders (
            id TEXT PRIMARY KEY,
            user_id BIGINT REFERENCES users(id),
            product_id INT REFERENCES products(id),
            quantity INT DEFAULT 1,
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
            status TEXT DEFAULT 'completed',
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
        try:
            cur.execute(query)
        except Exception as e:
            print(f"Error executing query: {e}")
    
    conn.commit()
    cur.close()
    conn.close()
    print("Database initialized successfully")

def get_user(user_id):
    """Get user by ID"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    return user

def create_user(user_id, username):
    """Create new user if not exists"""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO users (id, username) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING", 
            (user_id, username)
        )
        conn.commit()
    except Exception as e:
        print(f"Error creating user: {e}")
    finally:
        cur.close()
        conn.close()

def get_products():
    """Get all active products"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM products WHERE is_active = TRUE AND stock > 0 ORDER BY id")
    products = cur.fetchall()
    cur.close()
    conn.close()
    return products

def get_product(product_id):
    """Get product by ID"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM products WHERE id = %s", (product_id,))
    product = cur.fetchone()
    cur.close()
    conn.close()
    return product