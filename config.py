import os
from dotenv import load_dotenv

load_dotenv()

TOKEN                  = os.environ.get('BOT_TOKEN')
ADMIN_ID               = int(os.environ.get('ADMIN_ID', 0))
DATABASE_URL           = os.environ.get('DATABASE_URL')
BINANCE_API_KEY        = os.environ.get('BINANCE_API_KEY')
BINANCE_SECRET_KEY     = os.environ.get('BINANCE_SECRET_KEY')
BINANCE_WALLET_ADDRESS = os.environ.get('BINANCE_WALLET_ADDRESS')
BINANCE_NETWORK        = os.environ.get('BINANCE_NETWORK', 'BSC')
WEBAPP_URL             = os.environ.get('WEBAPP_URL')
BOT_USERNAME           = os.environ.get('BOT_USERNAME')
REFERRAL_COMMISSION    = float(os.environ.get('REFERRAL_COMMISSION', '0.10'))
PAYMENT_TIMEOUT        = int(os.environ.get('PAYMENT_TIMEOUT', '600'))
WITHDRAW_MIN           = float(os.environ.get('WITHDRAW_MIN', '20.0'))
WITHDRAW_FEE           = float(os.environ.get('WITHDRAW_FEE', '1.0'))
DEPOSIT_MIN            = float(os.environ.get('DEPOSIT_MIN', '10.0'))
