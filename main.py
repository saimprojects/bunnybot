import logging
import json
import uuid
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

from bot.config import TOKEN, ADMIN_ID, BOT_USERNAME, REFERRAL_COMMISSION
from bot.database import init_db, create_user, get_user, get_db_connection
from bot.utils import main_menu_keyboard, admin_menu_keyboard
from bot.products import get_available_items, mark_items_sold
from bot.payment import process_wallet_payment, check_binance_payment
from bot.admin import get_stats, update_user_balance

# Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    
    # Create user in DB
    create_user(user.id, user.username)
    
    # Handle referral
    if args and args[0].startswith('ref_'):
        referrer_id = int(args[0].replace('ref_', ''))
        if referrer_id != user.id:
            # Store referrer info in context or DB if needed
            # For simplicity, we just log it or you could add a 'referred_by' column to users table
            pass

    await update.message.reply_text(
        f"👋 Welcome to Bunny Tools, {user.first_name}!\n\nYour one-stop shop for digital products.",
        reply_markup=main_menu_keyboard()
    )

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    
    await update.message.reply_text("🛠 Admin Panel", reply_markup=admin_menu_keyboard())

async def web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = json.loads(update.effective_message.web_app_data.data)
    action = data.get("action")
    user_id = update.effective_user.id
    
    if action == "order":
        product_id = data.get("product_id")
        quantity = data.get("quantity")
        method = data.get("method")
        total = data.get("total")
        
        if method == "wallet":
            if process_wallet_payment(user_id, total):
                await complete_order(update, context, user_id, product_id, quantity, total, "Wallet")
            else:
                await update.message.reply_text("❌ Insufficient wallet balance.")
        elif method == "binance":
            await update.message.reply_text(f"⏳ Waiting for Binance payment of {total} USDT...")
            # In a real app, you'd start the background task here
            # For this demo, we'll assume the polling logic is handled
            pass

async def complete_order(update, context, user_id, product_id, quantity, total, method):
    items = get_available_items(product_id, quantity)
    if len(items) < quantity:
        await update.message.reply_text("❌ Sorry, out of stock.")
        return

    order_id = str(uuid.uuid4())[:8].upper()
    item_details = [{"email": i[1], "password": i[2]} for i in items]
    
    # Save order to DB
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO orders (id, user_id, product_id, quantity, total_amount, payment_method, delivery_details) VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (order_id, user_id, product_id, quantity, total, method, json.dumps(item_details))
    )
    # Update user stats
    cur.execute("UPDATE users SET total_orders = total_orders + 1 WHERE id = %s", (user_id,))
    
    # Handle referral commission (simple version)
    # cur.execute("UPDATE users SET balance = balance + %s WHERE id = (SELECT referred_by FROM users WHERE id = %s)", (total * REFERRAL_COMMISSION, user_id))
    
    conn.commit()
    cur.close()
    conn.close()
    
    mark_items_sold([i[0] for i in items], order_id)
    
    delivery_msg = "✅ Order Confirmed!\n\n"
    for item in item_details:
        delivery_msg += f"📧 Email: `{item['email']}`\n🔑 Password: `{item['password']}`\n\n"
    
    await update.message.reply_text(delivery_msg, parse_mode='Markdown')

async def admin_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    
    text = update.message.text
    if text.startswith("/addbalance"):
        _, uid, amt = text.split()
        update_user_balance(int(uid), float(amt))
        await update.message.reply_text(f"✅ Added {amt} to user {uid}")
    # Add other admin commands as per requirement...

if __name__ == '__main__':
    # Initialize DB
    init_db()
    
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(MessageHandler(filters.WEB_APP_DATA, web_app_data))
    app.add_handler(MessageHandler(filters.COMMAND, admin_commands))
    
    print("Bot is running...")
    app.run_polling()
