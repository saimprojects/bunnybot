import logging
import json
import uuid
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Import from same directory - NO 'bot.' prefix
from config import TOKEN, ADMIN_ID, BOT_USERNAME, REFERRAL_COMMISSION, WEBAPP_URL
from database import init_db, create_user, get_user, get_db_connection
from products import get_available_items, mark_items_sold
from payment import process_wallet_payment, check_binance_payment

# Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("🛒 Open Bunny Tools", web_app=WebAppInfo(url=WEBAPP_URL))]
    ]
    return InlineKeyboardMarkup(keyboard)

def admin_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("📦 Products", callback_data="admin_products"), 
         InlineKeyboardButton("📊 Stats", callback_data="admin_stats")],
        [InlineKeyboardButton("💰 Withdrawals", callback_data="admin_withdrawals"), 
         InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    
    # Create user in DB
    try:
        create_user(user.id, user.username)
    except Exception as e:
        logger.error(f"Error creating user: {e}")
    
    # Handle referral
    if args and args[0].startswith('ref_'):
        referrer_id = int(args[0].replace('ref_', ''))
        if referrer_id != user.id:
            # Store referrer info in context or DB if needed
            pass

    await update.message.reply_text(
        f"👋 Welcome to Bunny Tools, {user.first_name}!\n\nYour one-stop shop for digital products.\n\nClick the button below to open the store:",
        reply_markup=main_menu_keyboard()
    )

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return
    
    await update.message.reply_text("🛠 **Admin Panel**", parse_mode='Markdown', reply_markup=admin_menu_keyboard())

async def web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
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
                    await update.message.reply_text("❌ Insufficient wallet balance. Please add funds to continue.")
            elif method == "binance":
                await update.message.reply_text(f"⏳ Waiting for Binance payment of {total} USDT...\n\nYou have 10 minutes to complete the payment.")
                # Start background task for payment verification
                context.application.create_task(
                    verify_binance_payment(update, context, user_id, product_id, quantity, total)
                )
    except Exception as e:
        logger.error(f"Error in web_app_data: {e}")
        await update.message.reply_text("❌ Something went wrong. Please try again.")

async def verify_binance_payment(update, context, user_id, product_id, quantity, total):
    """Background task to verify Binance payment"""
    try:
        payment_verified = await check_binance_payment(user_id, total, lambda uid, amt, method: None)
        if payment_verified:
            await complete_order(update, context, user_id, product_id, quantity, total, "Binance")
        else:
            await context.bot.send_message(
                chat_id=user_id,
                text="❌ Payment verification failed or timed out. Please contact support."
            )
    except Exception as e:
        logger.error(f"Error verifying payment: {e}")

async def complete_order(update, update_obj, user_id, product_id, quantity, total, method):
    try:
        items = get_available_items(product_id, quantity)
        if len(items) < quantity:
            await update_obj.message.reply_text("❌ Sorry, out of stock. Please try a different quantity.")
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
        conn.commit()
        cur.close()
        conn.close()
        
        mark_items_sold([i[0] for i in items], order_id)
        
        delivery_msg = "✅ **Order Confirmed!**\n\n"
        delivery_msg += f"📦 Order ID: `{order_id}`\n\n"
        delivery_msg += "**Your Items:**\n\n"
        for idx, item in enumerate(item_details, 1):
            delivery_msg += f"**Item {idx}:**\n"
            delivery_msg += f"📧 Email: `{item['email']}`\n"
            delivery_msg += f"🔑 Password: `{item['password']}`\n\n"
        
        delivery_msg += "Thank you for shopping with Bunny Tools! 🐰"
        
        await update_obj.message.reply_text(delivery_msg, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error completing order: {e}")
        await update_obj.message.reply_text("❌ Error processing your order. Please contact support.")

async def admin_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    
    text = update.message.text
    try:
        if text.startswith("/addbalance"):
            parts = text.split()
            if len(parts) == 3:
                _, uid, amt = parts
                from admin import update_user_balance
                update_user_balance(int(uid), float(amt))
                await update.message.reply_text(f"✅ Added {amt} USDT to user {uid}")
            else:
                await update.message.reply_text("❌ Usage: /addbalance <user_id> <amount>")
        elif text.startswith("/stats"):
            from admin import get_stats
            stats = get_stats()
            await update.message.reply_text(
                f"📊 **Bot Statistics**\n\n"
                f"👥 Total Users: {stats['users']}\n"
                f"📦 Total Orders: {stats['orders']}\n"
                f"💰 Total Revenue: {stats['revenue']:.2f} USDT",
                parse_mode='Markdown'
            )
        elif text.startswith("/help"):
            await update.message.reply_text(
                "**Admin Commands:**\n"
                "/addbalance <user_id> <amount> - Add balance to user\n"
                "/stats - View bot statistics\n"
                "/admin - Open admin panel",
                parse_mode='Markdown'
            )
    except Exception as e:
        logger.error(f"Error in admin_commands: {e}")
        await update.message.reply_text("❌ Error executing command")

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if update.effective_user.id != ADMIN_ID:
        await query.edit_message_text("❌ You are not authorized.")
        return
    
    data = query.data
    if data == "admin_stats":
        from admin import get_stats
        stats = get_stats()
        await query.edit_message_text(
            f"📊 **Bot Statistics**\n\n"
            f"👥 Total Users: {stats['users']}\n"
            f"📦 Total Orders: {stats['orders']}\n"
            f"💰 Total Revenue: {stats['revenue']:.2f} USDT",
            parse_mode='Markdown'
        )
    elif data == "admin_products":
        await query.edit_message_text("📦 **Products Management**\n\nComing soon...")
    elif data == "admin_withdrawals":
        await query.edit_message_text("💰 **Withdrawals**\n\nComing soon...")
    elif data == "admin_broadcast":
        await query.edit_message_text("📢 **Broadcast Message**\n\nComing soon...")

if __name__ == '__main__':
    try:
        # Initialize DB
        logger.info("Initializing database...")
        init_db()
        
        # Create bot application
        app = ApplicationBuilder().token(TOKEN).build()
        
        # Add handlers
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("admin", admin_panel))
        app.add_handler(CommandHandler("addbalance", admin_commands))
        app.add_handler(CommandHandler("stats", admin_commands))
        app.add_handler(CommandHandler("help", admin_commands))
        app.add_handler(MessageHandler(filters.WEB_APP_DATA, web_app_data))
        app.add_handler(CallbackQueryHandler(callback_handler))
        
        logger.info("Bot is starting...")
        print("🤖 Bunny Tools Bot is running...")
        
        # Start the bot
        app.run_polling()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"Error: {e}")