from bot.database import get_db_connection
import json

def get_available_items(product_id, quantity):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, email, password FROM product_items WHERE product_id = %s AND is_sold = FALSE LIMIT %s",
        (product_id, quantity)
    )
    items = cur.fetchall()
    cur.close()
    conn.close()
    return items

def mark_items_sold(item_ids, order_id):
    conn = get_db_connection()
    cur = conn.cursor()
    for item_id in item_ids:
        cur.execute(
            "UPDATE product_items SET is_sold = TRUE, sold_at = NOW() WHERE id = %s",
            (item_id,)
        )
    conn.commit()
    cur.close()
    conn.close()

def add_product(name, duration, price, stock, warranty, desc, features, category):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO products (name, duration, price, stock, warranty, description, features, category) 
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
        (name, duration, price, stock, warranty, desc, features, category)
    )
    product_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return product_id

def add_product_items(product_id, items_json):
    conn = get_db_connection()
    cur = conn.cursor()
    items = json.loads(items_json)
    for item in items:
        cur.execute(
            "INSERT INTO product_items (product_id, email, password) VALUES (%s, %s, %s)",
            (product_id, item['email'], item['password'])
        )
    # Update stock
    cur.execute("UPDATE products SET stock = (SELECT COUNT(*) FROM product_items WHERE product_id = %s AND is_sold = FALSE) WHERE id = %s", (product_id, product_id))
    conn.commit()
    cur.close()
    conn.close()
