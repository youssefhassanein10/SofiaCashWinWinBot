from telegram import (
    Update,
    ReplyKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from config import BOT_TOKEN, ADMINS, SUPPORT_ADMIN_ID


SUPPORT_WAIT = set()


# ───── /start ─────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["💰 Пополнить", "💸 Вывести"],
        ["👤 Мой аккаунт"],
        ["📞 Поддержка"]
    ]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "👋 Добро пожаловать в Winwin Gambling\n\n"
        "Выберите действие:",
        reply_markup=markup
    )


# ───── Мой аккаунт ─────
async def account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    text = (
        "👤 *Ваш аккаунт*\n\n"
        f"Telegram ID: `{user.id}`\n"
        f"Username: @{user.username}\n"
        "Валюта: RUB\n"
        "Статус: Активен"
    )

    await update.message.reply_text(text, parse_mode="Markdown")


# ───── Поддержка ─────
async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    SUPPORT_WAIT.add(update.effective_user.id)

    await update.message.reply_text(
        "📞 Напишите сообщение для службы поддержки.\n"
        "Мы передадим его администратору."
    )


async def support_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in SUPPORT_WAIT:
        return

    text = (
        "📩 *Сообщение в поддержку*\n\n"
        f"От: {update.effective_user.full_name}\n"
        f"Telegram ID: `{user_id}`\n\n"
        f"{update.message.text}"
    )

    await context.bot.send_message(
        chat_id=SUPPORT_ADMIN_ID,
        text=text,
        parse_mode="Markdown"
    )

    SUPPORT_WAIT.remove(user_id)
    await update.message.reply_text("✅ Сообщение отправлено.")


# ───── Админ ответ ─────
async def admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        return

    if not update.message.reply_to_message:
        return

    lines = update.message.reply_to_message.text.split("\n")
    user_id = None

    for line in lines:
        if "Telegram ID:" in line:
            user_id = int(line.split("`")[1])

    if user_id:
        await context.bot.send_message(
            chat_id=user_id,
            text=f"💬 Ответ поддержки:\n\n{update.message.text}"
        )


# ───── Заглушки ─────
async def deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💰 Пополнение\n\n"
        "Скоро будет доступно."
    )


async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💸 Вывод средств\n\n"
        "Скоро будет доступен."
    )


# ───── Запуск ─────
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Text("👤 Мой аккаунт"), account))
    app.add_handler(MessageHandler(filters.Text("📞 Поддержка"), support))
    app.add_handler(MessageHandler(filters.Text("💰 Пополнить"), deposit))
    app.add_handler(MessageHandler(filters.Text("💸 Вывести"), withdraw))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, support_message))
    app.add_handler(MessageHandler(filters.REPLY & filters.TEXT, admin_reply))

    print("✅ Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
