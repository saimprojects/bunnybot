from database import get_db_connection

def get_available_items(product_id, quantity):
    """Get available items for a product"""
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
    """Mark items as sold"""
    conn = get_db_connection()
    cur = conn.cursor()
    for item_id in item_ids:
        cur.execute(
            "UPDATE product_items SET is_sold = TRUE, sold_at = NOW(), order_id = %s WHERE id = %s",
            (order_id, item_id)
        )
    conn.commit()
    cur.close()
    conn.close()

def add_product(name, duration, price, stock, warranty, description, features, category):
    """Add new product"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO products (name, duration, price, stock, warranty, description, features, category) 
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
        (name, duration, price, stock, warranty, description, features, category)
    )
    product_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return product_id

def add_product_items(product_id, items_list):
    """Add items to a product"""
    conn = get_db_connection()
    cur = conn.cursor()
    for item in items_list:
        cur.execute(
            "INSERT INTO product_items (product_id, email, password) VALUES (%s, %s, %s)",
            (product_id, item['email'], item['password'])
        )
    # Update stock count
    cur.execute("""
        UPDATE products SET stock = (
            SELECT COUNT(*) FROM product_items 
            WHERE product_id = %s AND is_sold = FALSE
        ) WHERE id = %s
    """, (product_id, product_id))
    conn.commit()
    cur.close()
    conn.close()

def update_product_stock(product_id):
    """Update product stock count"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE products SET stock = (
            SELECT COUNT(*) FROM product_items 
            WHERE product_id = %s AND is_sold = FALSE
        ) WHERE id = %s
    """, (product_id, product_id))
    conn.commit()
    cur.close()
    conn.close()