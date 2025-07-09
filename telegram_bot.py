import os
import sqlite3
import json
import requests
import re
import asyncio
from datetime import datetime
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram import Update
from telegram.ext import ContextTypes
import logging
import sys

# =====================================================
# 🔧 CONFIGURAZIONE LOGGING
# =====================================================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# =====================================================
# ⚙️ CONFIGURAZIONI PRINCIPALI
# =====================================================
DATABASE = 'users.db'  
BOT_TOKEN = '7897131694:AAF5IeQcYNDTGqGjEexUslVCz_LmRVIUdJs'  
ADMIN_ID = 1300395595
SAVE_DIR = 'verifiche'  
REQUIRED_PHOTOS = 2

# =====================================================
# 💾 INIZIALIZZAZIONE DATABASE ROBUSTA
# =====================================================
def init_db():
    """Crea il database con migrazione completa dello schema"""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    # Tabella per tracciare la versione dello schema
    c.execute('''CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY)''')
    c.execute('SELECT version FROM schema_version')
    result = c.fetchone()
    current_version = result[0] if result else 0
    
    # Schema versione 1 (base)
    if current_version < 1:
        logger.info("Applica migrazione schema a versione 1")
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            username TEXT,
            is_verified INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS verification_photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER,
            photo_number INTEGER,
            file_path TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
        )''')
        
        c.execute('INSERT OR REPLACE INTO schema_version (version) VALUES (1)')
        current_version = 1
    
    # Schema versione 2 (aggiunge colonne mancanti)
    if current_version < 2:
        logger.info("Applica migrazione schema a versione 2")
        # Aggiungi tutte le colonne mancanti
        columns_to_add = [
            ('photos_count', 'INTEGER DEFAULT 0'),
            ('verification_date', 'TIMESTAMP'),
            ('last_activity', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),
            ('first_name', 'TEXT'),
            ('last_name', 'TEXT')
        ]
        
        for col_name, col_type in columns_to_add:
            try:
                c.execute(f'ALTER TABLE users ADD COLUMN {col_name} {col_type}')
                logger.info(f"Aggiunta colonna: {col_name}")
            except sqlite3.OperationalError:
                logger.warning(f"Colonna {col_name} già presente")
        
        c.execute('UPDATE schema_version SET version = 2')
        current_version = 2
    
    conn.commit()
    conn.close()
    
    if not os.path.exists(SAVE_DIR):
        os.makedirs(SAVE_DIR)
    
    logger.info(f"Database inizializzato con schema versione {current_version}")

# =====================================================
# 🔍 FUNZIONI DATABASE
# =====================================================
def update_user_info(user):
    """Aggiorna/inserisce informazioni complete dell'utente"""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    # Query dinamica basata sulle colonne disponibili
    c.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in c.fetchall()]
    
    if 'first_name' in columns and 'last_name' in columns:
        c.execute('''INSERT OR REPLACE INTO users 
                     (telegram_id, username, first_name, last_name, last_activity) 
                     VALUES (?, ?, ?, ?, ?)''',
                  (user.id, user.username, user.first_name, user.last_name, datetime.now()))
    else:
        c.execute('''INSERT OR REPLACE INTO users 
                     (telegram_id, username, last_activity) 
                     VALUES (?, ?, ?)''',
                  (user.id, user.username, datetime.now()))
    
    conn.commit()
    conn.close()

def get_user_status(telegram_id):
    """Recupera lo stato completo dell'utente"""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    # Query sicura che funziona con qualsiasi schema
    c.execute('''SELECT status, username, is_verified, 
                 COALESCE(photos_count, 0) AS photos_count 
                 FROM users WHERE telegram_id = ?''', (telegram_id,))
    result = c.fetchone()
    conn.close()
    
    if result:
        return {
            'status': result[0],
            'username': result[1],
            'is_verified': result[2],
            'photos_count': result[3]
        }
    return None

# =====================================================
# 📁 GESTIONE CARTELLE E FILE
# =====================================================
def get_user_folder_name(telegram_id, username):
    """Genera il nome della cartella per l'utente"""
    if username:
        folder_name = re.sub(r'[^a-zA-Z0-9_]', '_', username.lstrip('@'))
    else:
        folder_name = f"user_{telegram_id}"
    return folder_name

def save_photo(telegram_id, username, photo, photo_number):
    """Salva solo le foto (non i messaggi di testo)"""
    folder_name = get_user_folder_name(telegram_id, username)
    user_dir = os.path.join(SAVE_DIR, folder_name)
    if not os.path.exists(user_dir):
        os.makedirs(user_dir)
    
    try:
        file_id = photo[-1].file_id
        file_info = requests.get(f'https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}').json()
        
        if not file_info.get('ok'):
            logger.error(f"Errore nel recupero del file: {file_info}")
            return False
            
        file_path_telegram = file_info['result']['file_path']
        file_url = f'https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path_telegram}'
        file_content = requests.get(file_url).content
        
        local_file_path = os.path.join(user_dir, f'photo{photo_number}.jpg')
        with open(local_file_path, 'wb') as f:
            f.write(file_content)
        
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute('''INSERT INTO verification_photos 
                     (telegram_id, photo_number, file_path) 
                     VALUES (?, ?, ?)''',
                  (telegram_id, photo_number, local_file_path))
        
        # Aggiornamento sicuro di photos_count
        c.execute('''UPDATE users 
                     SET photos_count = COALESCE(photos_count, 0) + 1 
                     WHERE telegram_id = ?''', 
                  (telegram_id,))
        
        conn.commit()
        conn.close()
        
        return True
        
    except Exception as e:
        logger.error(f"Errore nel salvare la foto: {e}")
        return False

def clear_user_photos(telegram_id):
    """Pulisce le foto precedenti dell'utente per nuovo tentativo"""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    c.execute('SELECT file_path FROM verification_photos WHERE telegram_id = ?', (telegram_id,))
    photos = c.fetchall()
    
    for photo in photos:
        try:
            if os.path.exists(photo[0]):
                os.remove(photo[0])
        except Exception as e:
            logger.error(f"Errore eliminazione file: {e}")
    
    c.execute('DELETE FROM verification_photos WHERE telegram_id = ?', (telegram_id,))
    c.execute('UPDATE users SET photos_count = 0 WHERE telegram_id = ?', (telegram_id,))
    
    conn.commit()
    conn.close()

# =====================================================
# 🚀 COMANDO /start
# =====================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    update_user_info(user)
    
    user_data = get_user_status(user.id)
    
    if user.id == ADMIN_ID:
        await update.message.reply_text(
            "👋 Ciao Admin!\n\n"
            "Comandi disponibili:\n"
            "• /admin_panel - Pannello di controllo\n"
            "• /help - Guida"
        )
        return
    
    if user_data and user_data['is_verified'] == 1:
        await update.message.reply_text("✅ Sei già verificato! Puoi accedere all'app.")
    elif user_data and user_data['status'] in ['collecting', 'submitted']:
        await update.message.reply_text(
            f"⏳ Verifica in corso\n"
            f"Foto inviate: {user_data['photos_count']}/{REQUIRED_PHOTOS}\n\n"
            f"Continua a inviare foto o attendi"
        )
    else:
        await update.message.reply_text(
            "👋 Benvenuto nel sistema di verifica!\n\n"
            "Per accedere all'app devi essere verificato.\n"
            "Usa /verify per iniziare."
        )

# =====================================================
# ✅ COMANDO /verify
# =====================================================
async def verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user_status(user_id)
    
    if not user_data:
        update_user_info(update.effective_user)
        user_data = get_user_status(user_id)
    
    if user_data['is_verified'] == 1:
        await update.message.reply_text("✅ Sei già verificato!")
        return
    
    if user_data['status'] == 'submitted':
        await update.message.reply_text("⏳ La tua verifica è in revisione. Attendi.")
        return
    
    if user_data['status'] == 'collecting' and user_data['photos_count'] >= REQUIRED_PHOTOS:
        await update.message.reply_text(
            f"✅ Hai già inviato {REQUIRED_PHOTOS} foto.\n"
            f"Usa /done per completare."
        )
        return
    
    if user_data['status'] != 'collecting':
        clear_user_photos(user_id)
        
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute('UPDATE users SET status = ?, photos_count = 0 WHERE telegram_id = ?', 
                  ('collecting', user_id))
        conn.commit()
        conn.close()
    
    photos_remaining = REQUIRED_PHOTOS - user_data.get('photos_count', 0)
    
    await update.message.reply_text(
        f"📸 **VERIFICA CON FOTO**\n\n"
        f"Devi inviare {REQUIRED_PHOTOS} foto\n"
        f"Foto già inviate: {user_data.get('photos_count', 0)}/{REQUIRED_PHOTOS}\n\n"
        f"⚠️ Invia SOLO foto!\n\n"
        f"Usa /done quando hai finito"
    )

# =====================================================
# ✔️ COMANDO /done
# =====================================================
async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user_status(user_id)
    
    if not user_data or user_data['status'] != 'collecting':
        await update.message.reply_text("❌ Non hai iniziato la verifica. Usa /verify")
        return
    
    if user_data['photos_count'] < REQUIRED_PHOTOS:
        await update.message.reply_text(
            f"❌ Foto insufficienti!\n\n"
            f"Richieste: {REQUIRED_PHOTOS}\n"
            f"Inviate: {user_data['photos_count']}\n\n"
            f"Mancano {REQUIRED_PHOTOS - user_data['photos_count']} foto."
        )
        return
    
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('UPDATE users SET status = ? WHERE telegram_id = ?', ('submitted', user_id))
    conn.commit()
    conn.close()
    
    await update.message.reply_text(
        "✅ **VERIFICA COMPLETATA!**\n\n"
        f"Hai inviato {REQUIRED_PHOTOS} foto.\n"
        "Richiesta in revisione.\n\n"
        "⏳ Riceverai una notifica a breve."
    )
    
    if user_id != ADMIN_ID:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute('SELECT file_path FROM verification_photos WHERE telegram_id = ? ORDER BY photo_number', (user_id,))
        photos = c.fetchall()
        conn.close()
        
        for i, (photo_path,) in enumerate(photos, 1):
            if os.path.exists(photo_path):
                with open(photo_path, 'rb') as f:
                    await context.bot.send_photo(
                        ADMIN_ID, 
                        f, 
                        caption=f"📸 Foto {i}/{len(photos)} - User {user_id}"
                    )
        
        await context.bot.send_message(
            ADMIN_ID, 
            f"🔔 **NUOVA VERIFICA**\n\n"
            f"Utente: {user_data['username'] or 'NoUsername'}\n"
            f"ID: `{user_id}`\n\n"
            f"Azioni:\n"
            f"• /approve_{user_id}\n"
            f"• /reject_{user_id}"
        )

# =====================================================
# 💬 GESTIONE MESSAGGI
# =====================================================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user_status(user_id)
    
    if not user_data or user_data['status'] != 'collecting':
        return
    
    if update.message.text:
        await update.message.reply_text(
            "❌ **SOLO FOTO!**\n\n"
            "Invia solo foto durante la verifica 📸"
        )
        return
    
    if update.message.photo:
        current_photos = user_data['photos_count']
        
        if current_photos >= REQUIRED_PHOTOS:
            await update.message.reply_text(
                f"⚠️ Hai già inviato {REQUIRED_PHOTOS} foto!\n"
                f"Usa /done per completare."
            )
            return
        
        photo_number = current_photos + 1
        success = save_photo(user_id, user_data['username'], update.message.photo, photo_number)
        
        if success:
            photos_remaining = REQUIRED_PHOTOS - photo_number
            
            if photos_remaining > 0:
                await update.message.reply_text(
                    f"✅ Foto {photo_number}/{REQUIRED_PHOTOS} salvata!\n\n"
                    f"Mancano {photos_remaining} foto."
                )
            else:
                await update.message.reply_text(
                    f"🎉 Foto complete!\n\n"
                    f"Usa /done per completare."
                )

# =====================================================
# ✅ COMANDO /approve
# =====================================================
async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    
    try:
        # Estrai l'ID utente dal comando
        command = update.message.text.split('_')
        if len(command) < 2:
            await update.message.reply_text("❌ Formato: /approve_123456789")
            return
            
        user_id = int(command[1])
        
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute('''UPDATE users SET is_verified = 1, status = 'verified', 
                     verification_date = ? WHERE telegram_id = ?''', 
                  (datetime.now(), user_id))
        conn.commit()
        conn.close()
        
        try:
            await context.bot.send_message(
                user_id, 
                "🎉 **VERIFICA APPROVATA!**\n\n"
                "✅ Sei stato verificato con successo!\n"
                "Ora puoi accedere all'app.\n\n"
                "Benvenuto! 🚀"
            )
        except Exception as e:
            logger.error(f"Errore notifica utente: {e}")
        
        await update.message.reply_text(f"✅ Utente {user_id} approvato!")

    except Exception as e:
        logger.error(f"Errore approvazione: {e}")
        await update.message.reply_text("❌ Errore: /approve_123456789")

# =====================================================
# ❌ COMANDO /reject
# =====================================================
async def reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    
    try:
        command = update.message.text.split('_')
        if len(command) < 2:
            await update.message.reply_text("❌ Formato: /reject_123456789")
            return
            
        user_id = int(command[1])
        
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute('''UPDATE users SET status = 'rejected', photos_count = 0 
                     WHERE telegram_id = ?''', (user_id,))
        conn.commit()
        conn.close()
        
        clear_user_photos(user_id)
        
        try:
            await context.bot.send_message(
                user_id, 
                "❌ **VERIFICA RIFIUTATA**\n\n"
                "Le foto non sono valide.\n\n"
                "Puoi riprovare con /verify"
            )
        except Exception as e:
            logger.error(f"Errore notifica utente: {e}")
        
        await update.message.reply_text(f"❌ Utente {user_id} rifiutato.")

    except Exception as e:
        logger.error(f"Errore rifiuto: {e}")
        await update.message.reply_text("❌ Errore: /reject_123456789")

# =====================================================
# 📊 COMANDO /admin_panel
# =====================================================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    
    await update.message.reply_text(
        "🛠 **PANNELLO ADMIN**\n\n"
        "**Gestione verifiche:**\n"
        "• /list_pending - Utenti in attesa\n"
        "• /list_all - Tutti gli utenti\n\n"
        "**Statistiche:**\n"
        "• /stats - Statistiche generali"
    )

# =====================================================
# 📋 COMANDO /list_pending
# =====================================================
async def list_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    # Query robusta che funziona con qualsiasi schema
    c.execute('''SELECT telegram_id, username, 
                 COALESCE(first_name, '') || ' ' || COALESCE(last_name, '') AS full_name,
                 COALESCE(photos_count, 0) AS photos_count 
                 FROM users WHERE status = 'submitted' 
                 ORDER BY COALESCE(last_activity, created_at) DESC''')
    
    users = c.fetchall()
    conn.close()
    
    if not users:
        await update.message.reply_text("✅ Nessun utente in attesa!")
        return
    
    message = "👥 **UTENTI IN ATTESA:**\n\n"
    for user in users:
        tid, username, full_name, photos = user
        name = full_name.strip() if full_name.strip() else (username or f"User {tid}")
        
        message += (
            f"👤 {name}\n"
            f"📱 @{username or 'NoUsername'}\n"
            f"🆔 ID: `{tid}`\n"
            f"📸 Foto: {photos}\n"
            f"🔍 /approve_{tid} | /reject_{tid}\n\n"
        )
    
    await update.message.reply_text(message, parse_mode='Markdown')

# =====================================================
# 📋 COMANDO /list_all
# =====================================================
async def list_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    # Query robusta che funziona con qualsiasi schema
    c.execute('''SELECT telegram_id, username, 
                 COALESCE(first_name, '') || ' ' || COALESCE(last_name, '') AS full_name,
                 status, is_verified 
                 FROM users 
                 ORDER BY COALESCE(last_activity, created_at) DESC''')
    
    users = c.fetchall()
    conn.close()
    
    if not users:
        await update.message.reply_text("📭 Nessun utente registrato.")
        return
    
    message = "👥 **TUTTI GLI UTENTI:**\n\n"
    for user in users:
        tid, username, full_name, status, verified = user
        name = full_name.strip() if full_name.strip() else (username or f"User {tid}")
        status_icon = "✅" if verified else "⏳" if status == 'submitted' else "🔄" if status == 'collecting' else "❌"
        message += (
            f"{status_icon} {name}\n"
            f"📱 @{username or 'NoUsername'}\n"
            f"🆔 ID: `{tid}`\n"
            f"📊 Stato: {status}\n\n"
        )
    
    await update.message.reply_text(message, parse_mode='Markdown')

# =====================================================
# 📊 COMANDO /stats
# =====================================================
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM users")
    total = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM users WHERE is_verified = 1")
    verified = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM users WHERE status = 'submitted'")
    pending = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM users WHERE status = 'collecting'")
    collecting = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM users WHERE status = 'rejected'")
    rejected = c.fetchone()[0]
    
    conn.close()
    
    await update.message.reply_text(
        f"📊 **STATISTICHE**\n\n"
        f"👥 Totale: {total}\n"
        f"✅ Verificati: {verified}\n"
        f"⏳ In attesa: {pending}\n"
        f"📸 In invio: {collecting}\n"
        f"❌ Rifiutati: {rejected}"
    )

# =====================================================
# ❓ COMANDO /help
# =====================================================
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id == ADMIN_ID:
        await update.message.reply_text(
            "🤖 **AIUTO ADMIN**\n\n"
            "Usa /admin_panel per i comandi"
        )
    else:
        await update.message.reply_text(
            "🤖 **COME VERIFICARSI**\n\n"
            "1. /verify - Inizia\n"
            f"2. Invia {REQUIRED_PHOTOS} foto\n"
            "3. /done - Completa\n"
            "4. Attendi approvazione\n\n"
            "⚠️ Invia solo FOTO!"
        )

# =====================================================
# 🚀 CONFIGURAZIONE E AVVIO
# =====================================================
def main():
    """Avvia il bot in modo sicuro"""
    # Risolvi eventuali problemi con l'event loop
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            logger.warning("Event loop già in esecuzione, ne creo uno nuovo")
            loop.stop()
            loop.close()
    except:
        pass
    
    # Crea un nuovo event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Inizializza il database con migrazione completa
    init_db()
    
    # Crea l'applicazione
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Aggiungi handler
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("verify", verify))
    application.add_handler(CommandHandler("done", done))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("admin_panel", admin_panel))
    application.add_handler(CommandHandler("list_pending", list_pending))
    application.add_handler(CommandHandler("list_all", list_all))
    application.add_handler(CommandHandler("stats", stats))
    
    # Handler per comandi approve/reject dinamici
    application.add_handler(MessageHandler(
        filters.Regex(r'^/approve_\d+$') & filters.Chat(chat_id=ADMIN_ID), 
        approve
    ))
    application.add_handler(MessageHandler(
        filters.Regex(r'^/reject_\d+$') & filters.Chat(chat_id=ADMIN_ID), 
        reject
    ))
    
    # Handler per messaggi generici
    application.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_message))
    
    logger.info("🚀 Bot in avvio...")
    
    try:
        # Avvia il polling
        application.run_polling()
    except Exception as e:
        logger.error(f"Errore grave: {e}")
    finally:
        # Pulisci l'event loop
        loop.close()

if __name__ == '__main__':
    main()