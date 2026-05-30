from database import get_db_connection
from products import add_product, add_product_items

def get_stats():
    """Get bot statistics"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("SELECT COUNT(*) FROM users")
        total_users = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM orders")
        total_orders = cur.fetchone()[0]
        
        cur.execute("SELECT COALESCE(SUM(total_amount), 0) FROM orders")
        total_revenue = cur.fetchone()[0]
        
        return {
            "users": total_users,
            "orders": total_orders,
            "revenue": total_revenue
        }
    except Exception as e:
        print(f"Error getting stats: {e}")
        return {"users": 0, "orders": 0, "revenue": 0}
    finally:
        cur.close()
        conn.close()

def update_user_balance(user_id, amount):
    """Update user balance"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("UPDATE users SET balance = balance + %s WHERE id = %s", (amount, user_id))
        cur.execute(
            "INSERT INTO transactions (user_id, type, amount) VALUES (%s, 'admin_add', %s)", 
            (user_id, amount)
        )
        conn.commit()
    except Exception as e:
        print(f"Error updating balance: {e}")
    finally:
        cur.close()
        conn.close()

def approve_withdrawal(withdrawal_id):
    """Approve withdrawal request"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("UPDATE withdrawals SET status = 'Approved' WHERE id = %s", (withdrawal_id,))
        conn.commit()
    except Exception as e:
        print(f"Error approving withdrawal: {e}")
    finally:
        cur.close()
        conn.close()