import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Токен бота
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    
    # Данные API SofiaCash
    API_HASH = os.getenv('API_HASH')
    API_CASHIERPASS = os.getenv('API_CASHIERPASS')
    API_CASHDESKID = os.getenv('API_CASHDESKID')
    API_LOGIN = os.getenv('API_LOGIN')
    API_BASE_URL = "https://partners.servcul.com/CashdeskBotAPI/"
    
    # Админы (через запятую)
    ADMINS = [int(admin_id) for admin_id in os.getenv('ADMINS', '').split(',') if admin_id]
    
    # Канал для уведомлений
    NOTIFICATION_CHANNEL = os.getenv('NOTIFICATION_CHANNEL', '')
    
    # Ссылка на поддержку
    SUPPORT_USERNAME = os.getenv('SUPPORT_USERNAME', '@WinWinSupport')
    
    # Настройки времени
    DEPOSIT_TIMEOUT = 600  # 10 минут в секундах
    
    # Статусы депозитов
    DEPOSIT_STATUS = {
        'PENDING': 'ожидает оплаты',
        'PAID': 'оплачен',
        'PROCESSING': 'в обработке',
        'COMPLETED': 'завершен',
        'CANCELLED': 'отменен'
    }
