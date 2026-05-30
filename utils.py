from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from bot.config import WEBAPP_URL

def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("🛒 Open Bunny Tools", web_app=WebAppInfo(url=WEBAPP_URL))]
    ]
    return InlineKeyboardMarkup(keyboard)

def admin_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("📦 All Products", callback_data="admin_products"), 
         InlineKeyboardButton("📋 All Orders", callback_data="admin_orders")],
        [InlineKeyboardButton("💸 Withdrawals", callback_data="admin_withdrawals"), 
         InlineKeyboardButton("📊 Statistics", callback_data="admin_stats")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")]
    ]
    return InlineKeyboardMarkup(keyboard)

def format_currency(amount):
    return f"${amount:.2f} USDT"
