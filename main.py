import logging
import json
import uuid
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# Import from local files
from config import TOKEN, ADMIN_ID, BOT_USERNAME, REFERRAL_COMMISSION, WEBAPP_URL
from database import init_db, create_user, get_user, get_db_connection
from products import get_available_items, mark_items_sold
from payment import process_wallet_payment
from admin import get_stats, update_user_balance

# Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def main_menu_keyboard():
    """Main menu keyboard for users"""
    keyboard = [
        [InlineKeyboardButton("🛒 Open Bunny Tools Store", web_app=WebAppInfo(url=WEBAPP_URL))],
        [InlineKeyboardButton("👤 My Profile", callback_data="profile"),
         InlineKeyboardButton("💰 Wallet", callback_data="wallet")],
        [InlineKeyboardButton("📦 My Orders", callback_data="orders"),
         InlineKeyboardButton("🎁 Refer & Earn", callback_data="refer")]
    ]
    return InlineKeyboardMarkup(keyboard)

def admin_menu_keyboard():
    """Admin menu keyboard"""
    keyboard = [
        [InlineKeyboardButton("📊 Statistics", callback_data="admin_stats"), 
         InlineKeyboardButton("📦 Products", callback_data="admin_products")],
        [InlineKeyboardButton("💰 Withdrawals", callback_data="admin_withdrawals"), 
         InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
        [InlineKeyboardButton("👥 Users", callback_data="admin_users"),
         InlineKeyboardButton("📋 Orders", callback_data="admin_orders")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler"""
    user = update.effective_user
    args = context.args
    
    # Create user in DB
    try:
        create_user(user.id, user.username)
        logger.info(f"User {user.id} ({user.username}) started the bot")
    except Exception as e:
        logger.error(f"Error creating user: {e}")
    
    # Handle referral
    if args and args[0].startswith('ref_'):
        try:
            referrer_id = int(args[0].replace('ref_', ''))
            if referrer_id != user.id:
                # Add referral commission logic here
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("UPDATE users SET referrals = referrals + 1, referral_earnings = referral_earnings + 5 WHERE id = %s", (referrer_id,))
                cur.execute("UPDATE users SET balance = balance + 5 WHERE id = %s", (referrer_id,))
                conn.commit()
                cur.close()
                conn.close()
                logger.info(f"Referral: {referrer_id} referred {user.id}")
        except Exception as e:
            logger.error(f"Error processing referral: {e}")

    welcome_msg = f"""🐰 **Welcome to Bunny Tools, {user.first_name}!** 🐰

Your one-stop shop for premium digital products.

✨ **Features:**
• Instant delivery after payment
• Secure wallet system
• 24/7 automated support
• Best prices guaranteed

Click the button below to start shopping! 🛒"""

    await update.message.reply_text(
        welcome_msg,
        parse_mode='Markdown',
        reply_markup=main_menu_keyboard()
    )

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin panel command"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return
    
    await update.message.reply_text(
        "🛠 **Admin Control Panel**\n\nWelcome back, Admin! Use the buttons below to manage your bot.",
        parse_mode='Markdown',
        reply_markup=admin_menu_keyboard()
    )

async def web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle web app data"""
    try:
        data = json.loads(update.effective_message.web_app_data.data)
        action = data.get("action")
        user_id = update.effective_user.id
        
        if action == "order":
            product_id = data.get("product_id")
            product_name = data.get("product_name")
            quantity = data.get("quantity")
            method = data.get("method")
            total = data.get("total")
            
            if method == "wallet":
                if process_wallet_payment(user_id, total):
                    await complete_order(update, context, user_id, product_id, product_name, quantity, total, "Wallet")
                else:
                    await update.message.reply_text(
                        "❌ **Insufficient Wallet Balance!**\n\n"
                        f"Required: {total} USDT\n"
                        f"Your balance: {get_user_balance(user_id)} USDT\n\n"
                        "Please add funds to continue.",
                        parse_mode='Markdown'
                    )
            elif method == "binance":
                await update.message.reply_text(
                    f"⏳ **Payment Initiated**\n\n"
                    f"Amount: {total} USDT\n"
                    f"Product: {product_name}\n"
                    f"Quantity: {quantity}\n\n"
                    "Please complete the payment within 10 minutes.\n"
                    "We will notify you once payment is confirmed.",
                    parse_mode='Markdown'
                )
                # Start payment verification
                context.application.create_task(
                    verify_binance_payment(update, context, user_id, product_id, product_name, quantity, total)
                )
                
    except Exception as e:
        logger.error(f"Error in web_app_data: {e}")
        await update.message.reply_text("❌ Something went wrong. Please try again.")

def get_user_balance(user_id):
    """Get user balance"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT balance FROM users WHERE id = %s", (user_id,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result[0] if result else 0

async def verify_binance_payment(update, context, user_id, product_id, product_name, quantity, total):
    """Background task to verify Binance payment"""
    import asyncio
    await asyncio.sleep(5)  # Simulate payment check
    # In production, implement actual Binance API check
    await complete_order(update, context, user_id, product_id, product_name, quantity, total, "Binance")

async def complete_order(update, context, user_id, product_id, product_name, quantity, total, method):
    """Complete order and deliver items"""
    try:
        items = get_available_items(product_id, quantity)
        if len(items) < quantity:
            await update.message.reply_text(
                f"❌ **Out of Stock!**\n\n"
                f"Sorry, {product_name} is currently out of stock.\n"
                f"Available: {len(items)} units\n"
                f"Requested: {quantity} units\n\n"
                "Please try a smaller quantity or contact support.",
                parse_mode='Markdown'
            )
            return

        order_id = str(uuid.uuid4())[:8].upper()
        item_details = [{"email": i[1], "password": i[2]} for i in items]
        
        # Save order to DB
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO orders (id, user_id, product_id, quantity, total_amount, payment_method, delivery_details, status) 
               VALUES (%s, %s, %s, %s, %s, %s, %s, 'Completed')""",
            (order_id, user_id, product_id, quantity, total, method, json.dumps(item_details))
        )
        cur.execute("UPDATE users SET total_orders = total_orders + 1 WHERE id = %s", (user_id,))
        conn.commit()
        cur.close()
        conn.close()
        
        # Mark items as sold
        mark_items_sold([i[0] for i in items], order_id)
        
        # Delivery message
        delivery_msg = f"✅ **ORDER CONFIRMED!** ✅\n\n"
        delivery_msg += f"📦 **Order ID:** `{order_id}`\n"
        delivery_msg += f"🛍️ **Product:** {product_name}\n"
        delivery_msg += f"🔢 **Quantity:** {quantity}\n"
        delivery_msg += f"💵 **Amount:** {total} USDT\n"
        delivery_msg += f"💳 **Method:** {method}\n\n"
        delivery_msg += "━━━━━━━━━━━━━━━━━━━━━━\n"
        delivery_msg += "**📧 YOUR LOGIN DETAILS:**\n\n"
        
        for idx, item in enumerate(item_details, 1):
            delivery_msg += f"**Account {idx}:**\n"
            delivery_msg += f"└ 📧 Email: `{item['email']}`\n"
            delivery_msg += f"└ 🔑 Password: `{item['password']}`\n\n"
        
        delivery_msg += "━━━━━━━━━━━━━━━━━━━━━━\n"
        delivery_msg += "🐰 **Thank you for shopping with Bunny Tools!**\n"
        delivery_msg += "Need help? Use /support to contact us."
        
        await update.message.reply_text(delivery_msg, parse_mode='Markdown')
        logger.info(f"Order completed: {order_id} for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error completing order: {e}")
        await update.message.reply_text(
            "❌ **Error Processing Order**\n\n"
            "Something went wrong. Please contact support with your order details.\n"
            "Use /support to reach us.",
            parse_mode='Markdown'
        )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    if data == "profile":
        user = get_user(user_id)
        if user:
            profile_msg = f"""👤 **Your Profile**

📝 **Username:** @{user[1] or 'N/A'}
🆔 **User ID:** `{user[0]}`
📅 **Joined:** {user[2].strftime('%Y-%m-%d') if user[2] else 'N/A'}
🛍️ **Orders:** {user[4]}
👥 **Referrals:** {user[5]}
💰 **Referral Earnings:** {user[6]} USDT

Use /start to go back to main menu."""
            await query.edit_message_text(profile_msg, parse_mode='Markdown')
        else:
            await query.edit_message_text("❌ User not found!")
            
    elif data == "wallet":
        user = get_user(user_id)
        if user:
            wallet_msg = f"""💰 **Your Wallet**

💵 **Balance:** {user[3]} USDT
🛍️ **Total Spent:** {get_user_total_spent(user_id)} USDT

**Quick Actions:**
• Add funds via Binance
• Withdraw to Binance (min 20 USDT)

Use /start to go back."""
            await query.edit_message_text(wallet_msg, parse_mode='Markdown')
        else:
            await query.edit_message_text("❌ User not found!")
            
    elif data == "orders":
        orders = get_user_orders(user_id)
        if orders:
            msg = "📦 **Your Orders**\n\n"
            for order in orders[:5]:  # Last 5 orders
                msg += f"🆔 `{order[0]}` - {order[1]} USDT\n"
                msg += f"   Status: {order[2]}\n\n"
            await query.edit_message_text(msg, parse_mode='Markdown')
        else:
            await query.edit_message_text("📦 You haven't placed any orders yet!\n\nUse the store button to start shopping.")
            
    elif data == "refer":
        user = get_user(user_id)
        bot_username = BOT_USERNAME
        ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
        msg = f"""🎁 **Refer & Earn!**

Invite friends and earn 5 USDT for each referral!

**Your Referral Link:**
`{ref_link}`

**Stats:**
• Referrals: {user[5] if user else 0}
• Earnings: {user[6] if user else 0} USDT

Share the link and start earning!"""
        await query.edit_message_text(msg, parse_mode='Markdown')
        
    elif data.startswith("admin_"):
        if user_id != ADMIN_ID:
            await query.edit_message_text("❌ You are not authorized!")
            return
            
        if data == "admin_stats":
            stats = get_stats()
            msg = f"""📊 **Bot Statistics**

👥 **Total Users:** {stats['users']}
📦 **Total Orders:** {stats['orders']}
💰 **Total Revenue:** {stats['revenue']:.2f} USDT
💵 **Pending Withdrawals:** {stats.get('pending_withdrawals', 0)}

Last updated: Just now"""
            await query.edit_message_text(msg, parse_mode='Markdown')
        else:
            await query.edit_message_text(f"🛠 {data} - Coming soon!")

def get_user_total_spent(user_id):
    """Get total amount spent by user"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COALESCE(SUM(total_amount), 0) FROM orders WHERE user_id = %s", (user_id,))
    result = cur.fetchone()[0]
    cur.close()
    conn.close()
    return result

def get_user_orders(user_id):
    """Get user orders"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, total_amount, status FROM orders WHERE user_id = %s ORDER BY created_at DESC LIMIT 10", (user_id,))
    orders = cur.fetchall()
    cur.close()
    conn.close()
    return orders

async def support_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Support command"""
    msg = """📞 **Customer Support**

Need help? Here's how to reach us:

• **Email:** support@bunnytools.com
• **Telegram:** @BunnyToolsSupport
• **Response Time:** Usually within 24 hours

**Common Issues:**
• Not receiving login details? Check your spam folder
• Payment issues? Contact support with your order ID
• Technical problems? Describe the issue in detail

We're here to help! 🐰"""
    await update.message.reply_text(msg, parse_mode='Markdown')

if __name__ == '__main__':
    try:
        # Initialize database
        logger.info("Initializing database...")
        init_db()
        
        # Create bot application
        app = ApplicationBuilder().token(TOKEN).build()
        
        # Add command handlers
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("admin", admin_panel))
        app.add_handler(CommandHandler("support", support_command))
        
        # Add message handlers
        app.add_handler(MessageHandler(filters.WEB_APP_DATA, web_app_data))
        
        # Add callback handler
        app.add_handler(CallbackQueryHandler(handle_callback))
        
        logger.info("🤖 Bunny Tools Bot is starting...")
        print("=" * 50)
        print("🐰 Bunny Tools Bot is Running!")
        print(f"📊 Bot Username: @{BOT_USERNAME}")
        print(f"👑 Admin ID: {ADMIN_ID}")
        print("=" * 50)
        
        # Start the bot
        app.run_polling()
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"❌ Error: {e}")