import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_ID = int(os.environ.get('ADMIN_ID', 0))
DATABASE_URL = os.environ.get('DATABASE_URL')
BOT_USERNAME = os.environ.get('BOT_USERNAME')
WEBAPP_URL = os.environ.get('WEBAPP_URL')

if not TOKEN:
    raise ValueError("BOT_TOKEN not found!")

print("✅ Config loaded successfully!")