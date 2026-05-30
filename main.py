import logging
import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# Import from local files
from config import TOKEN, ADMIN_ID, BOT_USERNAME, WEBAPP_URL
from database import init_db, create_user, get_user, get_db_connection
from products import get_available_items, mark_items_sold
from payment import process_wallet_payment
from admin import get_stats, update_user_balance

# Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def main_menu():
    keyboard = [
        [InlineKeyboardButton("🛒 Open Store", web_app=WebAppInfo(url=WEBAPP_URL))],
        [InlineKeyboardButton("👤 Profile", callback_data="profile"),
         InlineKeyboardButton("💰 Wallet", callback_data="wallet")],
        [InlineKeyboardButton("📦 My Orders", callback_data="orders")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    try:
        create_user(user.id, user.username)
        logger.info(f"User {user.id} started")
    except Exception as e:
        logger.error(f"Error: {e}")
    
    await update.message.reply_text(
        f"🐰 Welcome to Bunny Tools, {user.first_name}!\n\nClick below to start shopping!",
        reply_markup=main_menu()
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    if query.data == "profile":
        user = get_user(user_id)
        if user:
            msg = f"👤 Profile\n\nID: {user[0]}\nBalance: {user[3]} USDT\nOrders: {user[4]}"
            await query.edit_message_text(msg)
        else:
            await query.edit_message_text("User not found!")
    
    elif query.data == "wallet":
        user = get_user(user_id)
        if user:
            msg = f"💰 Wallet\n\nBalance: {user[3]} USDT"
            await query.edit_message_text(msg)
        else:
            await query.edit_message_text("User not found!")
    
    elif query.data == "orders":
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, total_amount FROM orders WHERE user_id = %s ORDER BY created_at DESC LIMIT 5", (user_id,))
        orders = cur.fetchall()
        cur.close()
        conn.close()
        
        if orders:
            msg = "📦 Your Orders:\n\n"
            for o in orders:
                msg += f"Order: {o[0]} - {o[1]} USDT\n"
            await query.edit_message_text(msg)
        else:
            await query.edit_message_text("No orders yet!")

async def webapp_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        data = json.loads(update.effective_message.web_app_data.data)
        user_id = update.effective_user.id
        
        if data.get("action") == "order":
            product_id = data.get("product_id")
            quantity = data.get("quantity")
            total = data.get("total")
            method = data.get("method")
            
            if method == "wallet":
                if process_wallet_payment(user_id, total):
                    await update.message.reply_text(f"✅ Payment successful! Amount: {total} USDT")
                else:
                    await update.message.reply_text("❌ Insufficient balance!")
            else:
                await update.message.reply_text(f"⏳ Processing {method} payment of {total} USDT...")
                
    except Exception as e:
        logger.error(f"Webapp error: {e}")
        await update.message.reply_text("❌ Something went wrong!")

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Unauthorized!")
        return
    
    await update.message.reply_text("🛠 Admin Panel - Coming Soon!")

def create_tables():
    """Create database tables if not exist"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Users table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id BIGINT PRIMARY KEY,
            username TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            balance FLOAT DEFAULT 0,
            total_orders INT DEFAULT 0,
            referrals INT DEFAULT 0,
            referral_earnings FLOAT DEFAULT 0
        )
    """)
    
    # Products table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            price FLOAT DEFAULT 0,
            stock INT DEFAULT 0,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    
    # Orders table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id TEXT PRIMARY KEY,
            user_id BIGINT REFERENCES users(id),
            product_id INT,
            quantity INT DEFAULT 1,
            total_amount FLOAT,
            payment_method TEXT,
            status TEXT DEFAULT 'Completed',
            created_at TIMESTAMP DEFAULT NOW(),
            delivery_details TEXT
        )
    """)
    
    # Transactions table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id SERIAL PRIMARY KEY,
            user_id BIGINT REFERENCES users(id),
            type TEXT,
            amount FLOAT,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    
    conn.commit()
    cur.close()
    conn.close()
    print("✅ Database tables ready")

def main():
    try:
        print("=" * 50)
        print("🐰 Bunny Tools Bot Starting...")
        print("=" * 50)
        
        # Create tables
        create_tables()
        
        # Create Application
        application = Application.builder().token(TOKEN).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("admin", admin_panel))
        application.add_handler(CallbackQueryHandler(handle_callback))
        # FIXED: Use filters.StatusUpdate.WEB_APP_DATA instead of filters.WEB_APP_DATA
        application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, webapp_handler))
        
        print(f"✅ Bot is running! Username: @{BOT_USERNAME}")
        print("=" * 50)
        
        # Start polling
        application.run_polling()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        logger.error(f"Fatal error: {e}")

if __name__ == '__main__':
    main()