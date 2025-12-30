import os
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import logging

# Включаем логирование
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# 🔐 Токен бота
BOT_TOKEN = "7479880371:AAHemgaC1OO2Ni-8ClbH9aYG4c8_FXoIQik"
ADMINS = [7940060404]

# Функция для /start
def start(update, context):
    user = update.effective_user
    update.message.reply_text(f'Привет {user.first_name}! 🤖\nЯ твой бот!')

# Функция для /help
def help_command(update, context):
    update.message.reply_text('Я умею:\n/start - начать\n/help - помощь\n/admin - админка')

# Функция для /admin
def admin_command(update, context):
    user_id = update.effective_user.id
    if user_id in ADMINS:
        update.message.reply_text('👑 Привет, администратор!')
    else:
        update.message.reply_text('❌ Вы не администратор')

# Ответ на любое сообщение
def echo(update, context):
    update.message.reply_text(f'Вы написали: {update.message.text}')

# Основная функция
def main():
    # Создаем бота
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    
    # Регистрируем команды
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(CommandHandler("admin", admin_command))
    
    # Регистрируем обработчик текста
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))
    
    # Запускаем бота
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
