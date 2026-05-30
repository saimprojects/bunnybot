from database import get_db_connection

def get_stats():
    """Get bot statistics"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Total users
        cur.execute("SELECT COUNT(*) FROM users")
        total_users = cur.fetchone()[0]
        
        # Total orders
        cur.execute("SELECT COUNT(*) FROM orders")
        total_orders = cur.fetchone()[0]
        
        # Total revenue
        cur.execute("SELECT COALESCE(SUM(total_amount), 0) FROM orders WHERE status = 'Completed'")
        total_revenue = cur.fetchone()[0]
        
        # Pending withdrawals
        cur.execute("SELECT COUNT(*) FROM withdrawals WHERE status = 'Pending'")
        pending_withdrawals = cur.fetchone()[0]
        
        # Today's orders
        cur.execute("SELECT COUNT(*) FROM orders WHERE DATE(created_at) = CURRENT_DATE")
        today_orders = cur.fetchone()[0]
        
        # Today's revenue
        cur.execute("SELECT COALESCE(SUM(total_amount), 0) FROM orders WHERE DATE(created_at) = CURRENT_DATE AND status = 'Completed'")
        today_revenue = cur.fetchone()[0]
        
        return {
            "users": total_users,
            "orders": total_orders,
            "revenue": total_revenue,
            "pending_withdrawals": pending_withdrawals,
            "today_orders": today_orders,
            "today_revenue": today_revenue
        }
    except Exception as e:
        print(f"❌ Error getting stats: {e}")
        return {
            "users": 0,
            "orders": 0,
            "revenue": 0,
            "pending_withdrawals": 0,
            "today_orders": 0,
            "today_revenue": 0
        }
    finally:
        cur.close()
        conn.close()

def update_user_balance(user_id, amount):
    """Update user balance (admin)"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("UPDATE users SET balance = balance + %s WHERE id = %s", (amount, user_id))
        cur.execute(
            "INSERT INTO transactions (user_id, type, amount, status) VALUES (%s, 'admin_add', %s, 'completed')", 
            (user_id, amount)
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ Error updating balance: {e}")
        return False
    finally:
        cur.close()
        conn.close()

def get_all_users(limit=100):
    """Get all users"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, username, created_at, balance, total_orders FROM users ORDER BY created_at DESC LIMIT %s", (limit,))
    users = cur.fetchall()
    cur.close()
    conn.close()
    return users

def get_pending_withdrawals():
    """Get all pending withdrawals"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM withdrawals WHERE status = 'Pending' ORDER BY created_at ASC")
    withdrawals = cur.fetchall()
    cur.close()
    conn.close()
    return withdrawals

def approve_withdrawal(withdrawal_id):
    """Approve withdrawal request"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("UPDATE withdrawals SET status = 'Approved' WHERE id = %s", (withdrawal_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ Error approving withdrawal: {e}")
        return False
    finally:
        cur.close()
        conn.close()

def reject_withdrawal(withdrawal_id):
    """Reject withdrawal request and refund"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Get withdrawal amount and user
        cur.execute("SELECT user_id, amount FROM withdrawals WHERE id = %s", (withdrawal_id,))
        result = cur.fetchone()
        
        if result:
            user_id, amount = result
            # Refund user
            cur.execute("UPDATE users SET balance = balance + %s WHERE id = %s", (amount, user_id))
            # Update withdrawal status
            cur.execute("UPDATE withdrawals SET status = 'Rejected' WHERE id = %s", (withdrawal_id,))
            conn.commit()
            return True
        return False
    except Exception as e:
        print(f"❌ Error rejecting withdrawal: {e}")
        return False
    finally:
        cur.close()
        conn.close()

def broadcast_message(message):
    """Get all user IDs for broadcast"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users")
    users = cur.fetchall()
    cur.close()
    conn.close()
    return [user[0] for user in users]