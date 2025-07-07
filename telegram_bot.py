# telegram_bot.py
# Backend per la gestione utenti verificati tramite Telegram
# Contiene sia la logica del bot che le API Flask per la mini-app

import sqlite3
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Configurazione logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = '7897131694:AAF5IeQcYNDTGqGjEexUslVCz_LmRVIUdJs'
DATABASE = 'users.db'

# --- Database ---
def init_db():
    """Inizializza il database con la tabella users"""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        telegram_id INTEGER PRIMARY KEY,
        username TEXT,
        is_verified INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()
    logger.info("Database inizializzato")

# --- Comandi Bot Telegram ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestisce il comando /start"""
    telegram_id = update.effective_user.id
    username = update.effective_user.username or "NoUsername"
    
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    # Controlla se l'utente esiste già
    c.execute('SELECT is_verified FROM users WHERE telegram_id = ?', (telegram_id,))
    result = c.fetchone()
    
    if result:
        if result[0] == 1:
            await update.message.reply_text('👋 Bentornato! Sei già verificato.')
        else:
            await update.message.reply_text('⏳ Sei già registrato. Attendi la verifica dall\'amministratore.')
    else:
        # Inserisci nuovo utente
        c.execute('INSERT INTO users (telegram_id, username) VALUES (?, ?)', (telegram_id, username))
        conn.commit()
        await update.message.reply_text('✅ Registrazione completata! Attendi la verifica dall\'amministratore.')
        logger.info(f"Nuovo utente registrato: {username} (ID: {telegram_id})")
    
    conn.close()

async def verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestisce il comando /verify (solo per admin)"""
    # Aggiungi qui l'ID Telegram dell'admin
    ADMIN_ID = 123456789  # Sostituisci con il tuo ID Telegram
    
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text('❌ Non sei autorizzato a usare questo comando.')
        return
    
    if not context.args:
        await update.message.reply_text('Uso: /verify <telegram_id>')
        return
    
    try:
        user_id = int(context.args[0])
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        
        # Verifica l'utente
        c.execute('UPDATE users SET is_verified=1 WHERE telegram_id=?', (user_id,))
        
        if c.rowcount > 0:
            conn.commit()
            await update.message.reply_text(f'✅ Utente {user_id} verificato con successo!')
            logger.info(f"Utente {user_id} verificato")
        else:
            await update.message.reply_text(f'❌ Utente {user_id} non trovato.')
        
        conn.close()
    except ValueError:
        await update.message.reply_text('❌ ID non valido. Usa un numero.')

async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lista tutti gli utenti (solo per admin)"""
    ADMIN_ID = 1300395595  # Sostituisci con il tuo ID Telegram
    
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text('❌ Non sei autorizzato a usare questo comando.')
        return
    
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('SELECT telegram_id, username, is_verified FROM users')
    users = c.fetchall()
    conn.close()
    
    if not users:
        await update.message.reply_text('📭 Nessun utente registrato.')
        return
    
    message = "👥 *Lista Utenti:*\n\n"
    for user in users:
        status = "✅ Verificato" if user[2] else "⏳ In attesa"
        message += f"• ID: `{user[0]}`\n  Username: @{user[1]}\n  Status: {status}\n\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra i comandi disponibili"""
    help_text = """
🤖 *Comandi disponibili:*

• /start - Registrati al sistema
• /help - Mostra questo messaggio

*Per amministratori:*
• /verify <telegram_id> - Verifica un utente
• /list - Mostra tutti gli utenti registrati
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

def main():
    """Funzione principale per avviare il bot"""
    # Inizializza database
    init_db()
    
    # Crea l'applicazione
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # Aggiungi i gestori dei comandi
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("verify", verify))
    application.add_handler(CommandHandler("list", list_users))
    application.add_handler(CommandHandler("help", help_command))
    
    # Avvia il bot
    logger.info("Bot avviato...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()s