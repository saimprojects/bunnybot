from database import get_db_connection
import random
import asyncio

def process_wallet_payment(user_id, amount):
    """Process wallet payment"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Check balance
        cur.execute("SELECT balance FROM users WHERE id = %s", (user_id,))
        result = cur.fetchone()
        
        if not result:
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
        print(f"❌ Error processing wallet payment: {e}")
        return False
    finally:
        cur.close()
        conn.close()

async def verify_binance_payment(user_id, expected_amount, timeout=600):
    """Verify Binance payment (simulated)"""
    # In production, implement actual Binance API check here
    await asyncio.sleep(5)  # Simulate API call
    return True

def generate_unique_amount(base_price):
    """Generate unique amount for payment tracking"""
    return base_price + random.uniform(0.01, 0.99)

def add_wallet_balance(user_id, amount):
    """Add balance to user wallet"""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE users SET balance = balance + %s WHERE id = %s", (amount, user_id))
        cur.execute(
            "INSERT INTO transactions (user_id, type, amount, status) VALUES (%s, 'deposit', %s, 'completed')", 
            (user_id, amount)
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ Error adding balance: {e}")
        return False
    finally:
        cur.close()
        conn.close()

def withdraw_balance(user_id, amount, address):
    """Process withdrawal request"""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Check balance
        cur.execute("SELECT balance FROM users WHERE id = %s", (user_id,))
        result = cur.fetchone()
        
        if not result or result[0] < amount:
            return False, "Insufficient balance"
        
        # Deduct balance
        cur.execute("UPDATE users SET balance = balance - %s WHERE id = %s", (amount, user_id))
        
        # Create withdrawal request
        cur.execute(
            "INSERT INTO withdrawals (user_id, amount, address, status) VALUES (%s, %s, %s, 'Pending')",
            (user_id, amount, address)
        )
        
        # Record transaction
        cur.execute(
            "INSERT INTO transactions (user_id, type, amount, status) VALUES (%s, 'withdrawal', %s, 'pending')", 
            (user_id, -amount)
        )
        
        conn.commit()
        return True, "Withdrawal request submitted"
    except Exception as e:
        print(f"❌ Error processing withdrawal: {e}")
        return False, str(e)
    finally:
        cur.close()
        conn.close()