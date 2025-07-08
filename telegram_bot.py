import os
import sqlite3
import json
import requests
import re
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram import Update
from telegram.ext import ContextTypes
import logging

# =====================================================
# 🔧 CONFIGURAZIONE LOGGING
# =====================================================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# =====================================================
# ⚙️ CONFIGURAZIONI PRINCIPALI
# =====================================================
DATABASE = 'users.db'  # Nome del file database
BOT_TOKEN = '7897131694:AAF5IeQcYNDTGqGjEexUslVCz_LmRVIUdJs'  # Token del bot
ADMIN_ID = 1300395595  # IL TUO ID TELEGRAM (lascia come numero, non stringa)
SAVE_DIR = 'verifiche'  # Cartella dove salvare i file di verifica

# =====================================================
# 💾 INIZIALIZZAZIONE DATABASE
# =====================================================
def init_db():
    """Crea il database e la struttura delle tabelle se non esistono"""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    # Crea la tabella users con tutti i campi necessari
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        telegram_id INTEGER PRIMARY KEY,
        username TEXT,
        is_verified INTEGER DEFAULT 0,
        status TEXT DEFAULT 'pending',
        verification_messages TEXT DEFAULT '[]',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    conn.commit()
    conn.close()
    
    # Crea la cartella per i file di verifica se non esiste
    if not os.path.exists(SAVE_DIR):
        os.makedirs(SAVE_DIR)
    
    logger.info("Database inizializzato")

# =====================================================
# 📁 GESTIONE CARTELLE UTENTE
# =====================================================
def get_user_folder_name(telegram_id, username):
    """Genera il nome della cartella per salvare i file dell'utente"""
    if username:
        # Rimuovi caratteri non validi per i nomi delle cartelle
        folder_name = re.sub(r'[^a-zA-Z0-9_]', '_', username.lstrip('@'))
    else:
        folder_name = str(telegram_id)
    return folder_name

# =====================================================
# 💾 SALVATAGGIO MESSAGGI
# =====================================================
def save_message_to_folder(telegram_id, username, message):
    """Salva i messaggi di verifica (testo o foto) nella cartella dell'utente"""
    # Crea la cartella dell'utente
    folder_name = get_user_folder_name(telegram_id, username)
    user_dir = os.path.join(SAVE_DIR, folder_name)
    if not os.path.exists(user_dir):
        os.makedirs(user_dir)
    
    # Recupera i messaggi già salvati dal database
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('SELECT verification_messages FROM users WHERE telegram_id = ?', (telegram_id,))
    messages_json = c.fetchone()[0]
    messages = json.loads(messages_json)
    msg_count = len(messages) + 1
    
    # Se è un messaggio di testo
    if message.text:
        file_path = os.path.join(user_dir, f'message{msg_count}.txt')
        with open(file_path, 'w') as f:
            f.write(message.text)
            
    # Se è una foto
    elif message.photo:
        file_id = message.photo[-1].file_id  # Prendi la foto in qualità più alta
        # Scarica la foto da Telegram
        file_info = requests.get(f'https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}').json()
        if not file_info.get('ok'):
            logger.error(f"Errore nel recupero del file: {file_info}")
            return
        file_path_telegram = file_info['result']['file_path']
        file_url = f'https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path_telegram}'
        file_content = requests.get(file_url).content
        local_file_path = os.path.join(user_dir, f'photo{msg_count}.jpg')
        with open(local_file_path, 'wb') as f:
            f.write(file_content)
    
    # Aggiorna la lista dei messaggi nel database
    messages.append(message.message_id)
    c.execute('UPDATE users SET verification_messages = ? WHERE telegram_id = ?', (json.dumps(messages), telegram_id))
    conn.commit()
    conn.close()

# =====================================================
# 🔍 VERIFICA STATO UTENTE
# =====================================================
def get_user_status(telegram_id):
    """Recupera lo stato corrente dell'utente dal database"""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('SELECT status, username FROM users WHERE telegram_id = ?', (telegram_id,))
    result = c.fetchone()
    conn.close()
    if result:
        return result[0], result[1]
    return 'pending', None

# =====================================================
# 🚀 COMANDO /start
# =====================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestisce il comando /start - primo comando che l'utente invia"""
    user_id = update.effective_user.id
    username = update.effective_user.username or None
    
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    # Inserisce l'utente nel database se non esiste già
    c.execute('INSERT OR IGNORE INTO users (telegram_id, username, status) VALUES (?, ?, ?)', 
              (user_id, username, 'pending'))
    
    # Controlla lo stato attuale dell'utente
    c.execute('SELECT is_verified, status FROM users WHERE telegram_id = ?', (user_id,))
    result = c.fetchone()
    conn.commit()
    conn.close()
    
    # ========== MESSAGGI DI RISPOSTA /start ==========
    if result[0] == 1:
        # MESSAGGIO: Utente già verificato
        await update.message.reply_text("✅ Sei già verificato! Puoi accedere all'app.")
    elif result[1] in ['collecting', 'submitted']:
        # MESSAGGIO: Verifica già in corso
        await update.message.reply_text("⏳ Hai già un processo di verifica in corso. Completa con /done o attendi la revisione.")
    else:
        # MESSAGGIO: Nuovo utente - benvenuto
        await update.message.reply_text(
            "👋 Benvenuto! Sono il bot di verifica.\n\n"
            "Per accedere all'app devi essere verificato.\n"
            "Usa /verify per iniziare il processo di verifica."
        )

# =====================================================
# ✅ COMANDO /verify
# =====================================================
async def verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inizia il processo di verifica per l'utente"""
    user_id = update.effective_user.id
    status, _ = get_user_status(user_id)
    
    # ========== MESSAGGI DI RISPOSTA /verify ==========
    if status == 'verified':
        # MESSAGGIO: Già verificato
        await update.message.reply_text("✅ Sei già verificato! Non serve ripetere il processo.")
    elif status in ['pending', 'rejected']:
        # Inizia la raccolta dei messaggi di verifica
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute('UPDATE users SET status = ?, verification_messages = ? WHERE telegram_id = ?', 
                  ('collecting', '[]', user_id))
        conn.commit()
        conn.close()
        
        # MESSAGGIO: Istruzioni per la verifica
        await update.message.reply_text(
            "📝 **PROCESSO DI VERIFICA INIZIATO**\n\n"
            "Ora puoi inviarmi:\n"
            "• Messaggi di testo\n"
            "• Foto\n\n"
            "Invia tutto ciò che serve per la verifica.\n"
            "Quando hai finito, usa /done per completare."
        )
    else:
        # MESSAGGIO: Verifica già in corso
        await update.message.reply_text("⚠️ Hai già un processo di verifica in corso. Completa con /done o attendi la revisione.")

# =====================================================
# ✔️ COMANDO /done
# =====================================================
async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Completa il processo di verifica e notifica l'admin"""
    user_id = update.effective_user.id
    status, username = get_user_status(user_id)
    
    if status == 'collecting':
        # Aggiorna lo stato a 'submitted'
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute('UPDATE users SET status = ? WHERE telegram_id = ?', ('submitted', user_id))
        conn.commit()
        conn.close()
        
        # MESSAGGIO: Conferma invio per revisione (all'utente)
        await update.message.reply_text(
            "✅ **VERIFICA INVIATA!**\n\n"
            "Le tue informazioni sono state inviate per la revisione.\n"
            "Riceverai una notifica quando l'admin avrà verificato il tuo account.\n\n"
            "⏳ Attendi pazientemente..."
        )
        
        # MESSAGGIO: Notifica all'admin
        await context.bot.send_message(
            ADMIN_ID, 
            f"🔔 **NUOVA VERIFICA DA REVISIONARE**\n\n"
            f"Utente: @{username or 'NoUsername'}\n"
            f"ID: `{user_id}`\n\n"
            f"Usa /review {user_id} per vedere i messaggi"
        )
    else:
        # MESSAGGIO: Errore - deve prima iniziare la verifica
        await update.message.reply_text("❌ Devi prima iniziare la verifica con /verify.")

# =====================================================
# 💬 GESTIONE MESSAGGI (testo e foto)
# =====================================================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestisce tutti i messaggi inviati dall'utente durante la verifica"""
    user_id = update.effective_user.id
    username = update.effective_user.username or None
    status, _ = get_user_status(user_id)
    
    if status == 'collecting':
        # Salva il messaggio
        save_message_to_folder(user_id, username, update.message)
        
        # MESSAGGIO: Conferma salvataggio
        if update.message.text:
            await update.message.reply_text("✅ Messaggio salvato! Continua o usa /done per terminare.")
        elif update.message.photo:
            await update.message.reply_text("📸 Foto salvata! Continua o usa /done per terminare.")
    else:
        # MESSAGGIO: Non in fase di raccolta
        await update.message.reply_text("⚠️ Non stai inviando una verifica. Usa /verify per iniziare.")

# =====================================================
# 👁️ COMANDO /review (SOLO ADMIN)
# =====================================================
async def review(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Permette all'admin di vedere i messaggi di verifica di un utente"""
    # Controlla se è l'admin
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Non sei autorizzato a usare questo comando!")
        return
    
    try:
        user_id = int(context.args[0])
        
        # Recupera i dati dell'utente
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute('SELECT username, verification_messages FROM users WHERE telegram_id = ?', (user_id,))
        result = c.fetchone()
        conn.close()
        
        if not result:
            # MESSAGGIO ADMIN: Utente non trovato
            await update.message.reply_text("❌ Utente non trovato nel database.")
            return
            
        username, messages_json = result
        messages = json.loads(messages_json)
        
        # MESSAGGIO ADMIN: Inizio review
        await update.message.reply_text(
            f"📋 **REVIEW UTENTE**\n\n"
            f"Username: @{username or 'NoUsername'}\n"
            f"ID: `{user_id}`\n"
            f"Messaggi salvati: {len(messages)}\n\n"
            f"Invio i messaggi..."
        )
        
        # Inoltra i messaggi salvati
        for msg_id in messages:
            try:
                await context.bot.forward_message(ADMIN_ID, user_id, msg_id)
            except Exception as e:
                logger.error(f"Errore nell'inoltro del messaggio {msg_id}: {e}")
        
        # Invia anche i file dalla cartella
        folder_name = get_user_folder_name(user_id, username)
        user_dir = os.path.join(SAVE_DIR, folder_name)
        if os.path.exists(user_dir):
            for file_name in os.listdir(user_dir):
                file_path = os.path.join(user_dir, file_name)
                if file_name.endswith('.txt'):
                    with open(file_path, 'r') as f:
                        await context.bot.send_message(ADMIN_ID, f"📝 Testo salvato:\n\n{f.read()}")
                elif file_name.endswith('.jpg'):
                    with open(file_path, 'rb') as f:
                        await context.bot.send_photo(ADMIN_ID, f, caption="📸 Foto salvata")
        
        # MESSAGGIO ADMIN: Istruzioni finali
        await update.message.reply_text(
            f"✅ Messaggi inviati!\n\n"
            f"Ora puoi:\n"
            f"• /approve {user_id} - per approvare\n"
            f"• /reject {user_id} - per rifiutare"
        )
        
    except (IndexError, ValueError):
        # MESSAGGIO ADMIN: Errore uso comando
        await update.message.reply_text("❌ Uso corretto: /review <user_id>")

# =====================================================
# ✅ COMANDO /approve (SOLO ADMIN)
# =====================================================
async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Approva la verifica di un utente"""
    # Controlla se è l'admin
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Non sei autorizzato!")
        return
    
    try:
        user_id = int(context.args[0])
        
        # Aggiorna il database
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute('UPDATE users SET is_verified = 1, status = ? WHERE telegram_id = ?', ('verified', user_id))
        conn.commit()
        conn.close()
        
        # MESSAGGIO: Notifica all'utente approvato
        await context.bot.send_message(
            user_id, 
            "🎉 **CONGRATULAZIONI!**\n\n"
            "✅ La tua verifica è stata APPROVATA!\n"
            "Ora puoi accedere all'app.\n\n"
            "Grazie per la pazienza! 🚀"
        )
        
        # MESSAGGIO ADMIN: Conferma approvazione
        await update.message.reply_text(f"✅ Utente {user_id} verificato con successo!")
        
    except (IndexError, ValueError):
        # MESSAGGIO ADMIN: Errore uso comando
        await update.message.reply_text("❌ Uso corretto: /approve <user_id>")

# =====================================================
# ❌ COMANDO /reject (SOLO ADMIN)
# =====================================================
async def reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Rifiuta la verifica di un utente"""
    # Controlla se è l'admin
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Non sei autorizzato!")
        return
    
    try:
        user_id = int(context.args[0])
        
        # Aggiorna il database
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute('UPDATE users SET status = ? WHERE telegram_id = ?', ('rejected', user_id))
        conn.commit()
        conn.close()
        
        # MESSAGGIO: Notifica all'utente rifiutato
        await context.bot.send_message(
            user_id, 
            "❌ **VERIFICA RIFIUTATA**\n\n"
            "Purtroppo la tua verifica non è stata approvata.\n\n"
            "Puoi riprovare inviando nuovamente /verify\n"
            "Assicurati di fornire tutte le informazioni richieste."
        )
        
        # MESSAGGIO ADMIN: Conferma rifiuto
        await update.message.reply_text(f"❌ Utente {user_id} rifiutato.")
        
    except (IndexError, ValueError):
        # MESSAGGIO ADMIN: Errore uso comando
        await update.message.reply_text("❌ Uso corretto: /reject <user_id>")

# =====================================================
# 📋 COMANDO /list_pending (SOLO ADMIN)
# =====================================================
async def list_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra la lista degli utenti in attesa di verifica"""
    # Controlla se è l'admin
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Non sei autorizzato!")
        return
    
    # Recupera utenti in attesa
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('SELECT telegram_id, username FROM users WHERE status = ?', ('submitted',))
    users = c.fetchall()
    conn.close()
    
    if not users:
        # MESSAGGIO ADMIN: Nessun utente in attesa
        await update.message.reply_text("✅ Nessun utente in attesa di verifica!")
        return
    
    # MESSAGGIO ADMIN: Lista utenti in attesa
    message = "👥 **UTENTI IN ATTESA DI VERIFICA:**\n\n"
    for user in users:
        message += f"• ID: `{user[0]}`\n  Username: @{user[1] or 'NoUsername'}\n  Comando: /review {user[0]}\n\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

# =====================================================
# 👥 COMANDO /list_users (SOLO ADMIN)
# =====================================================
async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra tutti gli utenti registrati"""
    # Controlla se è l'admin
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Non sei autorizzato!")
        return
    
    # Recupera tutti gli utenti
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('SELECT telegram_id, username, is_verified, status FROM users')
    users = c.fetchall()
    conn.close()
    
    if not users:
        # MESSAGGIO ADMIN: Nessun utente
        await update.message.reply_text("📭 Nessun utente registrato.")
        return
    
    # MESSAGGIO ADMIN: Lista completa utenti
    message = "👥 **LISTA COMPLETA UTENTI:**\n\n"
    verified_count = 0
    pending_count = 0
    
    for user in users:
        if user[2] == 1:
            status_emoji = "✅"
            status_text = "Verificato"
            verified_count += 1
        else:
            status_emoji = "⏳"
            status_text = user[3].capitalize()
            pending_count += 1
            
        message += f"{status_emoji} ID: `{user[0]}`\n   @{user[1] or 'NoUsername'}\n   Status: {status_text}\n\n"
    
    # Aggiungi statistiche
    message += f"\n📊 **STATISTICHE:**\n"
    message += f"✅ Verificati: {verified_count}\n"
    message += f"⏳ In attesa/Non verificati: {pending_count}\n"
    message += f"📋 Totale: {len(users)}"
    
    await update.message.reply_text(message, parse_mode='Markdown')

# =====================================================
# ❓ COMANDO /help
# =====================================================
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra i comandi disponibili in base al tipo di utente"""
    user_id = update.effective_user.id
    
    # Se è l'admin mostra tutti i comandi
    if user_id == ADMIN_ID:
        # MESSAGGIO: Help per admin
        help_text = """
🤖 **COMANDI BOT - ADMIN**

**Comandi Utente:**
• /start - Registrazione iniziale
• /verify - Inizia processo di verifica
• /done - Completa invio documenti
• /help - Mostra questo messaggio

**Comandi Admin:**
• /review <id> - Vedi messaggi di un utente
• /approve <id> - Approva verifica
• /reject <id> - Rifiuta verifica  
• /list_pending - Utenti in attesa
• /list_users - Tutti gli utenti

**Come funziona:**
1. L'utente usa /verify
2. Invia messaggi/foto
3. Usa /done per completare
4. Tu ricevi notifica
5. Usi /review per vedere
6. Approvi o rifiuti
        """
    else:
        # MESSAGGIO: Help per utenti normali
        help_text = """
🤖 **COME VERIFICARSI**

**Passaggi:**
1️⃣ Usa /verify per iniziare
2️⃣ Invia i tuoi messaggi o foto
3️⃣ Usa /done quando hai finito
4️⃣ Attendi l'approvazione

**Comandi disponibili:**
• /start - Inizio
• /verify - Avvia verifica
• /done - Completa verifica
• /help - Aiuto

Per assistenza contatta l'admin.
        """
    
    await update.message.reply_text(help_text)

# =====================================================
# 🚀 FUNZIONE PRINCIPALE
# =====================================================
def main():
    """Avvia il bot e registra tutti i gestori di comandi"""
    # Inizializza il database
    init_db()
    
    # Crea l'applicazione del bot
    application = Application.builder().token(BOT_TOKEN).build()
    
    # ========== REGISTRA TUTTI I COMANDI ==========
    # Comandi per tutti gli utenti
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("verify", verify))
    application.add_handler(CommandHandler("done", done))
    application.add_handler(CommandHandler("help", help_command))
    
    # Comandi solo per admin
    application.add_handler(CommandHandler("review", review))
    application.add_handler(CommandHandler("approve", approve))
    application.add_handler(CommandHandler("reject", reject))
    application.add_handler(CommandHandler("list_pending", list_pending))
    application.add_handler(CommandHandler("list_users", list_users))
    
    # Gestore per tutti i messaggi (testo e foto)
    application.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_message))
    
    # Avvia il bot
    logger.info("🚀 Bot avviato e pronto!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

# =====================================================
# 🏁 PUNTO DI INGRESSO
# =====================================================
if __name__ == '__main__':
    main()