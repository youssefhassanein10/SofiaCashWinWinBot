import os
import logging
import asyncio
from datetime import datetime, timedelta
from telegram import Update, Message, Chat
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)
from telegram.constants import ParseMode, ChatAction

from config import Config
from database import Database
from api_client import SofiaCashAPI
from keyboards import (
    get_main_keyboard, get_admin_keyboard, get_deposit_keyboard,
    get_user_deposit_keyboard, get_payment_methods_keyboard,
    get_broadcast_keyboard, get_support_keyboard
)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
DEPOSIT_AMOUNT, PAYMENT_METHOD, PAYMENT_DETAILS = range(3)
BROADCAST_MESSAGE = range(3, 4)

class WinWinBot:
    def __init__(self):
        self.config = Config
        self.db = Database()
        self.api = SofiaCashAPI()
        self.pending_deposits = {}  # Временное хранение депозитов
        
    def is_admin(self, user_id):
        """Проверка, является ли пользователь администратором"""
        return user_id in self.config.ADMINS
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user = update.effective_user
        self.db.add_or_update_user(user.id, user.username, user.full_name)
        
        if self.is_admin(user.id):
            welcome_text = f"""
👋 Добро пожаловать, Администратор {user.first_name}!

🤖 **WinWin Bot - SofiaCash System**
💼 Касса: SofiaCash
🔗 Интеграция: WinWin Gaming Platform

📊 **Панель администратора:**
- Управление депозитами
- Обработка выплат
- Рассылка сообщений
- Мониторинг баланса

Используйте меню ниже для управления.
            """
            await update.message.reply_text(
                welcome_text, 
                reply_markup=get_admin_keyboard(),
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            welcome_text = f"""
🎰 Добро пожаловать в WinWin, {user.first_name}!

💰 **Быстрые депозиты и выплаты**
⚡ Мгновенные операции
🛡 Безопасные транзакции
🆘 Круглосуточная поддержка

💵 **Минимальный депозит:** 100 ₽
💳 **Методы оплаты:** Карты, ЮMoney, Qiwi, Crypto

Выберите действие ниже ⤵️
            """
            await update.message.reply_text(
                welcome_text,
                reply_markup=get_main_keyboard(),
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстовых сообщений"""
        user = update.effective_user
        text = update.message.text
        
        if self.is_admin(user.id):
            # Обработка сообщений администратора
            if text == "📊 Статистика":
                await self.admin_stats(update, context)
            elif text == "⏳ Ожидающие депозиты":
                await self.show_pending_deposits(update, context)
            elif text == "🔄 В обработке":
                await self.show_processing_deposits(update, context)
            elif text == "📢 Рассылка":
                await update.message.reply_text(
                    "📢 Введите сообщение для рассылки:",
                    reply_markup=ReplyKeyboardMarkup([["❌ Отменить рассылку"]], resize_keyboard=True)
                )
                return BROADCAST_MESSAGE
            elif text == "💼 Баланс кассы":
                await self.show_cashier_balance(update, context)
            elif text == "👥 Поиск игрока":
                await update.message.reply_text("🔍 Введите ID игрока для поиска:")
                context.user_data['action'] = 'search_user'
        else:
            # Обработка сообщений пользователя
            if text == "💰 Пополнить счет":
                await self.start_deposit(update, context)
            elif text == "💸 Вывести средства":
                await self.start_withdrawal(update, context)
            elif text == "📊 Мой баланс":
                await self.show_user_balance(update, context)
            elif text == "📋 Мои депозиты":
                await self.show_user_deposits(update, context)
            elif text == "🆘 Поддержка":
                await self.show_support(update, context)
            elif text == "📞 Связаться с поддержкой":
                await self.contact_support(update, context)

    async def start_deposit(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начало процесса депозита"""
        await update.message.reply_text(
            "💵 **Пополнение счета**\n\n"
            "Введите сумму пополнения в рублях:\n"
            "Минимальная сумма: 100 ₽",
            parse_mode=ParseMode.MARKDOWN
        )
        return DEPOSIT_AMOUNT
    
    async def process_deposit_amount(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка суммы депозита"""
        try:
            amount = float(update.message.text)
            if amount < 100:
                await update.message.reply_text("❌ Минимальная сумма депозита: 100 ₽\nПопробуйте еще раз:")
                return DEPOSIT_AMOUNT
            
            context.user_data['deposit_amount'] = amount
            
            # Показываем методы оплаты
            await update.message.reply_text(
                f"💰 Сумма: {amount:.2f} ₽\n\n"
                "Выберите метод оплаты:",
                reply_markup=get_payment_methods_keyboard(),
                parse_mode=ParseMode.MARKDOWN
            )
            return PAYMENT_METHOD
            
        except ValueError:
            await update.message.reply_text("❌ Пожалуйста, введите корректную сумму (например: 500)")
            return DEPOSIT_AMOUNT
    
    async def process_payment_method(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора метода оплаты"""
        query = update.callback_query
        await query.answer()
        
        method = query.data.replace("method_", "")
        context.user_data['payment_method'] = method
        
        methods_text = {
            'card': '💳 Банковская карта',
            'yoomoney': '📱 ЮMoney',
            'qiwi': '🎯 QIWI Кошелек',
            'crypto': '🔗 Криптовалюта'
        }
        
        await query.edit_message_text(
            f"✅ Выбран метод: {methods_text.get(method, method)}\n"
            f"💰 Сумма: {context.user_data['deposit_amount']:.2f} ₽\n\n"
            "⏳ Создаем заявку на депозит...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Создаем депозит в базе данных
        user = update.effective_user
        deposit_id = self.db.add_deposit(
            user.id,
            user.username,
            context.user_data['deposit_amount']
        )
        
        # Сохраняем информацию о депозите
        context.user_data['deposit_id'] = deposit_id
        
        # Уведомляем администраторов
        await self.notify_admins_about_deposit(
            context, 
            deposit_id, 
            user, 
            context.user_data['deposit_amount'],
            method
        )
        
        # Отправляем сообщение пользователю
        user_message = await query.message.reply_text(
            f"📋 **Заявка на депозит #{deposit_id} создана**\n\n"
            f"👤 Игрок: {user.full_name}\n"
            f"💵 Сумма: {context.user_data['deposit_amount']:.2f} ₽\n"
            f"💳 Метод: {methods_text.get(method, method)}\n\n"
            "⏳ Ожидайте реквизиты для оплаты от администратора...",
            reply_markup=get_user_deposit_keyboard(deposit_id),
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Сохраняем ID сообщения пользователя
        self.db.conn.execute(
            "UPDATE deposits SET user_message_id = ? WHERE id = ?",
            (user_message.message_id, deposit_id)
        )
        self.db.conn.commit()
        
        return ConversationHandler.END
    
    async def notify_admins_about_deposit(self, context, deposit_id, user, amount, method):
        """Уведомление администраторов о новом депозите"""
        admin_message = (
            f"🆕 **Новый депозит #{deposit_id}**\n\n"
            f"👤 Игрок: {user.full_name}\n"
            f"🆔 TG ID: {user.id}\n"
            f"👤 Username: @{user.username or 'нет'}\n"
            f"💰 Сумма: {amount:.2f} ₽\n"
            f"💳 Метод: {method}\n"
            f"⏰ Время: {datetime.now().strftime('%H:%M:%S')}\n\n"
            "👇 Для обработки нажмите кнопку ниже:"
        )
        
        for admin_id in self.config.ADMINS:
            try:
                message = await context.bot.send_message(
                    chat_id=admin_id,
                    text=admin_message,
                    reply_markup=get_deposit_keyboard(deposit_id),
                    parse_mode=ParseMode.MARKDOWN
                )
                
                # Сохраняем ID сообщения администратора
                self.db.conn.execute(
                    "UPDATE deposits SET admin_message_id = ? WHERE id = ?",
                    (message.message_id, deposit_id)
                )
                self.db.conn.commit()
                
            except Exception as e:
                logger.error(f"Не удалось отправить уведомление администратору {admin_id}: {e}")
    
    async def handle_deposit_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка callback от администратора по депозиту"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        deposit_id = int(data.split('_')[1])
        
        if data.startswith('accept_'):
            await self.accept_deposit(query, deposit_id, context)
        elif data.startswith('reject_'):
            await self.reject_deposit(query, deposit_id, context)
        elif data.startswith('contact_'):
            await self.contact_user(query, deposit_id, context)
        elif data.startswith('view_'):
            await self.view_deposit(query, deposit_id, context)
    
    async def accept_deposit(self, query, deposit_id, context):
        """Администратор принимает депозит"""
        deposit = self.db.get_deposit(deposit_id)
        if not deposit:
            await query.edit_message_text("❌ Депозит не найден")
            return
        
        # Запрашиваем реквизиты оплаты
        await query.edit_message_text(
            f"✅ Вы принимаете депозит #{deposit_id}\n\n"
            "Введите реквизиты для оплаты:\n"
            "(например: номер карты, кошелька и т.д.)",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Сохраняем контекст для следующего шага
        context.user_data['action'] = 'add_payment_details'
        context.user_data['deposit_id'] = deposit_id
    
    async def process_payment_details(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка реквизитов оплаты от администратора"""
        if context.user_data.get('action') == 'add_payment_details':
            deposit_id = context.user_data['deposit_id']
            payment_details = update.message.text
            
            # Обновляем депозит
            self.db.update_deposit_status(
                deposit_id, 
                'PAID', 
                update.effective_user.id,
                payment_details
            )
            
            # Получаем информацию о депозите
            deposit = self.db.get_deposit(deposit_id)
            
            # Отправляем реквизиты пользователю
            try:
                await context.bot.send_message(
                    chat_id=deposit[1],  # user_id
                    text=f"💳 **Реквизиты для оплаты**\n\n"
                         f"📋 Депозит #{deposit_id}\n"
                         f"💰 Сумма: {deposit[3]:.2f} ₽\n\n"
                         f"🔗 Реквизиты:\n"
                         f"{payment_details}\n\n"
                         f"⏳ Время на оплату: 10 минут\n"
                         f"После оплаты нажмите кнопку 'Я оплатил'",
                    parse_mode=ParseMode.MARKDOWN
                )
                
                await update.message.reply_text(
                    f"✅ Реквизиты отправлены игроку\n"
                    f"Депозит #{deposit_id}\n"
                    f"⏰ Таймер: 10 минут",
                    reply_markup=get_admin_keyboard()
                )
                
                # Запускаем таймер на 10 минут
                asyncio.create_task(
                    self.deposit_timeout_check(deposit_id, context)
                )
                
            except Exception as e:
                await update.message.reply_text(
                    f"❌ Не удалось отправить сообщение игроку: {e}",
                    reply_markup=get_admin_keyboard()
                )
            
            # Очищаем контекст
            context.user_data.clear()
    
    async def deposit_timeout_check(self, deposit_id, context):
        """Проверка таймаута депозита (10 минут)"""
        await asyncio.sleep(600)  # 10 минут
        
        deposit = self.db.get_deposit(deposit_id)
        if deposit and deposit[4] == 'PAID':  # status == 'PAID'
            # Депозит не оплачен вовремя
            self.db.update_deposit_status(deposit_id, 'CANCELLED')
            
            # Уведомляем пользователя
            try:
                await context.bot.send_message(
                    chat_id=deposit[1],
                    text=f"❌ Депозит #{deposit_id} отменен\n"
                         f"Причина: истекло время оплаты"
                )
            except:
                pass
    
    async def handle_user_paid(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Пользователь нажал 'Я оплатил'"""
        query = update.callback_query
        await query.answer()
        
        deposit_id = int(query.data.split('_')[1])
        
        await query.edit_message_text(
            f"✅ Вы подтвердили оплату депозита #{deposit_id}\n\n"
            "📎 Пожалуйста, загрузите чек (PDF, фото или скриншот):",
            parse_mode=ParseMode.MARKDOWN
        )
        
        context.user_data['waiting_for_receipt'] = deposit_id
    
    async def handle_receipt(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка загруженного чека"""
        if 'waiting_for_receipt' in context.user_data:
            deposit_id = context.user_data['waiting_for_receipt']
            file_id = None
            
            if update.message.document:
                if update.message.document.mime_type == 'application/pdf':
                    file_id = update.message.document.file_id
            elif update.message.photo:
                file_id = update.message.photo[-1].file_id
            
            if file_id:
                # Сохраняем файл
                self.db.add_receipt(deposit_id, file_id)
                
                # Уведомляем администраторов
                deposit = self.db.get_deposit(deposit_id)
                
                for admin_id in self.config.ADMINS:
                    try:
                        # Отправляем сообщение с чеком
                        if update.message.document:
                            await context.bot.send_document(
                                chat_id=admin_id,
                                document=file_id,
                                caption=f"📎 Чек для депозита #{deposit_id}\n"
                                        f"👤 Игрок: {deposit[2]}\n"
                                        f"💰 Сумма: {deposit[3]:.2f} ₽",
                                reply_markup=get_deposit_keyboard(deposit_id)
                            )
                        else:
                            await context.bot.send_photo(
                                chat_id=admin_id,
                                photo=file_id,
                                caption=f"📎 Чек для депозита #{deposit_id}\n"
                                        f"👤 Игрок: {deposit[2]}\n"
                                        f"💰 Сумма: {deposit[3]:.2f} ₽",
                                reply_markup=get_deposit_keyboard(deposit_id)
                            )
                    except Exception as e:
                        logger.error(f"Не удалось отправить чек администратору {admin_id}: {e}")
                
                await update.message.reply_text(
                    f"✅ Чек получен и отправлен администратору\n"
                    f"Ожидайте подтверждения платежа",
                    reply_markup=get_main_keyboard()
                )
                
                # Очищаем контекст
                del context.user_data['waiting_for_receipt']
            else:
                await update.message.reply_text(
                    "❌ Пожалуйста, загрузите PDF-файл или фото"
                )
    
    async def reject_deposit(self, query, deposit_id, context):
        """Администратор отклоняет депозит"""
        self.db.update_deposit_status(
            deposit_id, 
            'CANCELLED', 
            query.from_user.id
        )
        
        deposit = self.db.get_deposit(deposit_id)
        
        # Уведомляем пользователя
        try:
            await context.bot.send_message(
                chat_id=deposit[1],
                text=f"❌ Депозит #{deposit_id} отклонен\n"
                     f"💰 Сумма: {deposit[3]:.2f} ₽\n\n"
                     f"Если у вас есть вопросы, обратитесь в поддержку"
            )
        except:
            pass
        
        await query.edit_message_text(
            f"❌ Депозит #{deposit_id} отклонен\n"
            f"Игрок уведомлен"
        )
    
    async def complete_deposit(self, deposit_id, admin_id, context):
        """Завершение депозита (пополнение через API)"""
        deposit = self.db.get_deposit(deposit_id)
        
        # Пополняем счет через API SofiaCash
        result = self.api.deposit_to_user(deposit[1], deposit[3])
        
        if result['success']:
            # Обновляем статус депозита
            self.db.update_deposit_status(deposit_id, 'COMPLETED', admin_id)
            
            # Обновляем баланс пользователя
            self.db.update_user_balance(deposit[1], deposit[3])
            
            # Уведомляем пользователя
            try:
                await context.bot.send_message(
                    chat_id=deposit[1],
                    text=f"✅ **Депозит успешно зачислен!**\n\n"
                         f"📋 Номер: #{deposit_id}\n"
                         f"💵 Сумма: {deposit[3]:.2f} ₽\n"
                         f"💰 Ваш счет пополнен\n"
                         f"🎰 Удачной игры в WinWin!",
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                pass
            
            return True
        else:
            # Ошибка API
            try:
                await context.bot.send_message(
                    chat_id=deposit[1],
                    text=f"⚠️ **Ошибка зачисления депозита**\n\n"
                         f"📋 Номер: #{deposit_id}\n"
                         f"💵 Сумма: {deposit[3]:.2f} ₽\n"
                         f"❌ Ошибка: {result.get('error', 'Неизвестная ошибка')}\n"
                         f"📞 Свяжитесь с поддержкой",
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                pass
            
            return False
    
    async def show_support(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать информацию о поддержке"""
        support_text = f"""
🆘 **Служба поддержки WinWin**

📞 **Связаться с поддержкой:**
Нажмите кнопку ниже, чтобы написать напрямую

🕒 **Часы работы:**
Круглосуточно, 24/7

📋 **Что предоставить при обращении:**
1. Ваш ID в боте
2. Номер операции (если есть)
3. Описание проблемы

👇 **Выберите действие:**
        """
        
        await update.message.reply_text(
            support_text,
            reply_markup=get_support_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def contact_support(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Связаться с поддержкой"""
        user = update.effective_user
        support_link = f"https://t.me/{self.config.SUPPORT_USERNAME[1:]}?start=user{user.id}"
        
        await update.message.reply_text(
            f"📞 **Связь с поддержкой**\n\n"
            f"👤 Ваш ID: `{user.id}`\n"
            f"📛 Имя: {user.full_name}\n\n"
            f"Нажмите кнопку ниже, чтобы написать в поддержку:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("💬 Написать в поддержку", url=support_link)
            ]]),
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def broadcast_message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик рассылки"""
        if update.message.text == "❌ Отменить рассылку":
            await update.message.reply_text(
                "❌ Рассылка отменена",
                reply_markup=get_admin_keyboard()
            )
            return ConversationHandler.END
        
        context.user_data['broadcast_message'] = update.message.text_markdown_v2
        
        await update.message.reply_text(
            f"📢 **Предпросмотр рассылки:**\n\n"
            f"{update.message.text}\n\n"
            f"✅ Отправить это сообщение всем пользователям?",
            reply_markup=get_broadcast_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
        
        return ConversationHandler.END
    
    async def broadcast_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Подтверждение рассылки"""
        query = update.callback_query
        await query.answer()
        
        if query.data == 'broadcast_confirm':
            await query.edit_message_text("⏳ Отправка рассылки...")
            
            # Получаем всех пользователей
            cursor = self.db.conn.cursor()
            cursor.execute("SELECT user_id FROM users")
            users = cursor.fetchall()
            
            success_count = 0
            fail_count = 0
            
            for user in users:
                try:
                    await context.bot.send_message(
                        chat_id=user[0],
                        text=context.user_data['broadcast_message'].replace('\\', ''),
                        parse_mode=ParseMode.MARKDOWN_V2
                    )
                    success_count += 1
                    await asyncio.sleep(0.1)  # Задержка чтобы не превысить лимиты
                except Exception as e:
                    fail_count += 1
                    logger.error(f"Не удалось отправить рассылку пользователю {user[0]}: {e}")
            
            await query.edit_message_text(
                f"✅ Рассылка завершена!\n\n"
                f"✅ Успешно: {success_count}\n"
                f"❌ Не удалось: {fail_count}\n"
                f"👥 Всего: {len(users)}"
            )
        else:
            await query.edit_message_text("❌ Рассылка отменена")
        
        context.user_data.clear()
        await query.message.reply_text(
            "Главное меню:",
            reply_markup=get_admin_keyboard()
        )
    
    async def show_cashier_balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать баланс кассы через API"""
        await update.message.reply_text("⏳ Запрашиваю баланс кассы...")
        
        balance_data = self.api.get_balance()
        
        if balance_data and 'Balance' in balance_data:
            response = (
                f"💰 **Баланс кассы SofiaCash**\n\n"
                f"💵 Доступно: {balance_data['Balance']:.2f} ₽\n"
                f"📊 Лимит: {balance_data.get('Limit', 0):.2f} ₽\n"
                f"📈 Свободно: {balance_data.get('Limit', 0) - balance_data['Balance']:.2f} ₽\n\n"
                f"🔄 Последнее обновление: {datetime.now().strftime('%H:%M:%S')}"
            )
        else:
            response = "❌ Не удалось получить баланс кассы"
        
        await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Глобальный обработчик ошибок"""
        logger.error(f"Ошибка: {context.error}")
        
        if update and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "⚠️ Произошла ошибка. Пожалуйста, попробуйте позже."
                )
            except:
                pass

def main():
    """Запуск бота"""
    # Проверка конфигурации
    if not Config.BOT_TOKEN:
        raise ValueError("BOT_TOKEN не установлен!")
    
    # Создаем бота
    bot = WinWinBot()
    
    # Создаем приложение
    application = Application.builder().token(Config.BOT_TOKEN).build()
    
    # ConversationHandler для депозитов
    deposit_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Text(["💰 Пополнить счет"]), bot.start_deposit)],
        states={
            DEPOSIT_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, bot.process_deposit_amount)
            ],
            PAYMENT_METHOD: [
                CallbackQueryHandler(bot.process_payment_method, pattern="^method_")
            ]
        },
        fallbacks=[CommandHandler("cancel", bot.cancel)],
        allow_reentry=True
    )
    
    # ConversationHandler для рассылки
    broadcast_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Text(["📢 Рассылка"]), bot.handle_message)],
        states={
            BROADCAST_MESSAGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, bot.broadcast_message_handler)
            ]
        },
        fallbacks=[],
        allow_reentry=True
    )
    
    # Добавляем обработчики
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(deposit_conv_handler)
    application.add_handler(broadcast_conv_handler)
    
    # Обработчики callback
    application.add_handler(CallbackQueryHandler(bot.handle_deposit_callback, pattern="^(accept|reject|contact|view)_"))
    application.add_handler(CallbackQueryHandler(bot.handle_user_paid, pattern="^paid_"))
    application.add_handler(CallbackQueryHandler(bot.broadcast_confirmation, pattern="^broadcast_"))
    
    # Обработчики сообщений
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, 
        bot.handle_message
    ))
    
    # Обработчик документов (чеки)
    application.add_handler(MessageHandler(
        filters.Document.ALL | filters.PHOTO,
        bot.handle_receipt
    ))
    
    # Обработчик для платежных реквизитов от администратора
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        bot.process_payment_details
    ))
    
    # Обработчик ошибок
    application.add_error_handler(bot.error_handler)
    
    # Запуск бота
    print("🤖 Бот WinWin запущен...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
