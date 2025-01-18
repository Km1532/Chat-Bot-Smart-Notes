import logging
import sqlite3
import asyncio
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from telegram.error import TimedOut, NetworkError

# Використовуємо nest_asyncio для уникнення помилок із подієвим циклом
import nest_asyncio
nest_asyncio.apply()

# Логування
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# База даних
def init_db():
    conn = sqlite3.connect("notes.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            note TEXT
        )
    """)
    conn.commit()
    conn.close()

# Команди
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.reply_text(
            "Привіт! Я - твій розумний нотатник. Ось що я вмію:\n\n"
            "/add - Додати нову нотатку\n"
            "/list - Переглянути всі нотатки\n"
            "/delete - Видалити нотатку\n"
        )
    except TimedOut:
        logger.error("Не вдалося відправити повідомлення через таймаут.")

async def add_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.reply_text("Введи текст нотатки:")
    except TimedOut:
        logger.error("Не вдалося відправити повідомлення через таймаут.")
    return "ADDING_NOTE"

async def save_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    note = update.message.text

    try:
        conn = sqlite3.connect("notes.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO notes (user_id, note) VALUES (?, ?)", (user_id, note))
        conn.commit()
        conn.close()
        await update.message.reply_text("Нотатку додано!")
    except Exception as e:
        logger.error(f"Помилка при збереженні нотатки: {e}")

async def list_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    try:
        conn = sqlite3.connect("notes.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, note FROM notes WHERE user_id = ?", (user_id,))
        notes = cursor.fetchall()
        conn.close()

        if notes:
            response = "Ваші нотатки:\n"
            for note_id, note in notes:
                response += f"{note_id}. {note}\n"
            await update.message.reply_text(response)
        else:
            await update.message.reply_text("У вас поки що немає нотаток.")
    except Exception as e:
        logger.error(f"Помилка при отриманні списку нотаток: {e}")

async def delete_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    try:
        conn = sqlite3.connect("notes.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, note FROM notes WHERE user_id = ?", (user_id,))
        notes = cursor.fetchall()
        conn.close()

        if notes:
            keyboard = [[InlineKeyboardButton(f"{note_id}: {note[:20]}", callback_data=str(note_id))] for note_id, note in notes]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("Оберіть нотатку для видалення:", reply_markup=reply_markup)
        else:
            await update.message.reply_text("У вас немає нотаток для видалення.")
    except Exception as e:
        logger.error(f"Помилка при видаленні нотатки: {e}")

async def delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    note_id = int(query.data)
    try:
        conn = sqlite3.connect("notes.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        conn.commit()
        conn.close()

        await query.edit_message_text("Нотатку видалено!")
    except Exception as e:
        logger.error(f"Помилка при обробці видалення нотатки: {e}")

# Основна функція
async def main():
    # Ініціалізуємо базу даних
    init_db()

    # Створюємо бота
    application = Application.builder().token("8123581065:AAEx_R_7duVrBcgIiSL5N7NPHWxa6pDxQ3M").connect_timeout(30).read_timeout(30).build()

    # Хендлери команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("add", add_note))
    application.add_handler(CommandHandler("list", list_notes))
    application.add_handler(CommandHandler("delete", delete_note))
    application.add_handler(CallbackQueryHandler(delete_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, save_note))

    # Запускаємо бота з обробкою мережевих помилок
    try:
        await application.run_polling()
    except NetworkError:
        logger.error("Мережа недоступна. Перевірте підключення до Інтернету.")
    except Exception as e:
        logger.error(f"Непередбачена помилка: {e}")

if __name__ == "__main__":
    asyncio.run(main())
