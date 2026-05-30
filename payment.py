import random
import asyncio
from database import get_db_connection

# Binance client (optional)
try:
    from binance.spot import Spot
    from config import BINANCE_API_KEY, BINANCE_SECRET_KEY
    if BINANCE_API_KEY and BINANCE_SECRET_KEY:
        client = Spot(api_key=BINANCE_API_KEY, api_secret=BINANCE_SECRET_KEY)
    else:
        client = None
except ImportError:
    client = None

async def check_binance_payment(user_id, expected_amount, order_callback):
    """Check Binance payment (simplified version)"""
    # For now, return True for demo
    # In production, implement actual Binance API check
    await asyncio.sleep(5)  # Simulate checking
    return True

def generate_unique_amount(base_price):
    """Generate unique amount for payment"""
    return base_price + random.uniform(0.01, 0.99)

def process_wallet_payment(user_id, amount):
    """Process wallet payment"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Check balance
        cur.execute("SELECT balance FROM users WHERE id = %s", (user_id,))
        result = cur.fetchone()
        
        if not result:
            cur.close()
            conn.close()
            return False
            
        balance = result[0]
        
        if balance >= amount:
            # Deduct balance
            cur.execute("UPDATE users SET balance = balance - %s WHERE id = %s", (amount, user_id))
            # Record transaction
            cur.execute(
                "INSERT INTO transactions (user_id, type, amount, status) VALUES (%s, 'purchase', %s, 'completed')", 
                (user_id, -amount)
            )
            conn.commit()
            return True
        
        return False
    except Exception as e:
        print(f"Error processing wallet payment: {e}")
        return False
    finally:
        cur.close()
        conn.close()