from bot.database import get_db_connection
from bot.products import add_product, add_product_items

def get_stats():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    total_users = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM orders")
    total_orders = cur.fetchone()[0]
    cur.execute("SELECT SUM(total_amount) FROM orders")
    total_revenue = cur.fetchone()[0] or 0
    cur.close()
    conn.close()
    return {
        "users": total_users,
        "orders": total_orders,
        "revenue": total_revenue
    }

def update_user_balance(user_id, amount):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET balance = balance + %s WHERE id = %s", (amount, user_id))
    cur.execute("INSERT INTO transactions (user_id, type, amount) VALUES (%s, 'admin_add', %s)", (user_id, amount))
    conn.commit()
    cur.close()
    conn.close()

def approve_withdrawal(withdrawal_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE withdrawals SET status = 'Approved' WHERE id = %s", (withdrawal_id,))
    conn.commit()
    cur.close()
    conn.close()
