# telegram_bot.py
# Backend per la gestione utenti verificati tramite Telegram
# Contiene sia la logica del bot che le API Flask per la mini-app

import sqlite3
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TELEGRAM_TOKEN = '7897131694:AAFDIUob9YoBJFGEWFHSP_HqeuOHQbfJONQ'
DATABASE = 'users.db'

# --- Database ---
def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        telegram_id INTEGER PRIMARY KEY,
        username TEXT,
        is_verified INTEGER DEFAULT 0
    )''')
    conn.commit()
    conn.close()

# --- Bot Telegram ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    username = update.effective_user.username
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO users (telegram_id, username) VALUES (?, ?)', (telegram_id, username))
    conn.commit()
    conn.close()
    await update.message.reply_text('Ciao! Sei stato registrato. Attendi la verifica.')

async def verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('UPDATE users SET is_verified=1 WHERE telegram_id=?', (telegram_id,))
    conn.commit()
    conn.close()
    await update.message.reply_text('Utente verificato!')

async def run_bot():
    bot_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    bot_app.add_handler(CommandHandler('start', start))
    bot_app.add_handler(CommandHandler('verify', verify))
    await bot_app.run_polling()

if __name__ == '__main__':
    init_db()
    import asyncio
    asyncio.run(run_bot())
