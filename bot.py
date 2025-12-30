# =========================
# Telegram Bot Configuration
# =========================

# 🔐 Токен Telegram-бота (из @BotFather)
BOT_TOKEN = "7479880371:AAHemgaC1OO2Ni-8ClbH9aYG4c8_FXoIQik"

# 👮 Администраторы (Telegram ID)
ADMINS = [7940060404]  # Это твой ID

# =========================
# Основной код бота
# =========================

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import logging

# Включаем логирование, чтобы видеть ошибки
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

# Функция для команды /start
def start(update, context):
    user = update.effective_user
    update.message.reply_text(
        f'Привет, {user.first_name}! 👋\n'
        f'Я твой телеграм-бот!\n'
        f'Твой ID: {user.id}'
    )

# Функция для команды /help
def help_command(update, context):
    update.message.reply_text(
        'Доступные команды:\n'
        '/start - Начать работу\n'
        '/help - Помощь\n'
        '/admin - Для администраторов'
    )

# Функция для команды /admin
def admin_command(update, context):
    user_id = update.effective_user.id
    
    if user_id in ADMINS:
        update.message.reply_text(
            f'Привет, администратор! 👑\n'
            f'Твой ID: {user_id}\n'
            f'Ты можешь управлять ботом.'
        )
    else:
        update.message.reply_text('У вас нет прав администратора!')

# Функция для обработки текстовых сообщений
def echo(update, context):
    text = update.message.text
    update.message.reply_text(f'Вы написали: {text}')

# Функция для обработки ошибок
def error(update, context):
    logger.warning(f'Update {update} вызвал ошибку {context.error}')

# Основная функция
def main():
    # Создаем Updater и передаем ему токен бота
    updater = Updater(BOT_TOKEN, use_context=True)
    
    # Получаем dispatcher для регистрации обработчиков
    dp = updater.dispatcher
    
    # Регистрируем обработчики команд
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(CommandHandler("admin", admin_command))
    
    # Регистрируем обработчик для текстовых сообщений
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))
    
    # Регистрируем обработчик ошибок
    dp.add_error_handler(error)
    
    # Запускаем бота
    updater.start_polling()
    
    # Останавливаем бота при нажатии Ctrl+C
    updater.idle()

if __name__ == '__main__':
    main()
