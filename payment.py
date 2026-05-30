import random
import asyncio
from binance.spot import Spot
from bot.config import BINANCE_API_KEY, BINANCE_SECRET_KEY, PAYMENT_TIMEOUT
from bot.database import get_db_connection

client = Spot(api_key=BINANCE_API_KEY, api_secret=BINANCE_SECRET_KEY)

async def check_binance_payment(user_id, expected_amount, order_callback):
    """
    Poll Binance for deposits matching the expected amount.
    """
    start_time = asyncio.get_event_loop().time()
    while asyncio.get_event_loop().time() - start_time < PAYMENT_TIMEOUT:
        try:
            # Call Binance API
            deposits = client.deposit_history(coin='USDT', limit=20)
            
            for deposit in deposits:
                # Match logic: amount within 0.001 and status is success (1)
                if abs(float(deposit['amount']) - expected_amount) < 0.001 and deposit['status'] == 1:
                    # Additional check for time could be added here
                    await order_callback(user_id, expected_amount, "Binance")
                    return True
        except Exception as e:
            print(f"Error checking Binance payment: {e}")
            
        await asyncio.sleep(15)
    return False

def generate_unique_amount(base_price):
    return base_price + random.uniform(0.01, 0.99)

def process_wallet_payment(user_id, amount):
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Check balance
    cur.execute("SELECT balance FROM users WHERE id = %s", (user_id,))
    balance = cur.fetchone()[0]
    
    if balance >= amount:
        # Deduct balance
        cur.execute("UPDATE users SET balance = balance - %s WHERE id = %s", (amount, user_id))
        # Record transaction
        cur.execute("INSERT INTO transactions (user_id, type, amount) VALUES (%s, 'purchase', %s)", (user_id, -amount))
        conn.commit()
        cur.close()
        conn.close()
        return True
    
    cur.close()
    conn.close()
    return False
