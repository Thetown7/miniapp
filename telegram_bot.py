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
# 💾 RESET E INIZIALIZZAZIONE DATABASE
# =====================================================
def reset_database():
    """Elimina e ricrea il database da zero"""
    logger.info("Reset completo del database...")
    
    # Backup dei dati esistenti se necessario
    backup_data = []
    if os.path.exists(DATABASE):
        try:
            conn = sqlite3.connect(DATABASE)
            c = conn.cursor()
            c.execute("SELECT telegram_id, username, is_verified FROM users WHERE is_verified = 1")
            backup_data = c.fetchall()
            conn.close()
        except:
            pass
        
        # Elimina il database esistente
        os.remove(DATABASE)
        logger.info("Database esistente eliminato")
    
    # Crea nuovo database con schema completo
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    # Crea tabella users con TUTTE le colonne necessarie
    c.execute('''CREATE TABLE users (
        telegram_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        last_name TEXT,
        is_verified INTEGER DEFAULT 0,
        status TEXT DEFAULT 'pending',
        photos_count INTEGER DEFAULT 0,
        verification_date TIMESTAMP,
        last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Crea tabella per le foto
    c.execute('''CREATE TABLE verification_photos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER,
        photo_number INTEGER,
        file_path TEXT,
        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
    )''')
    
    # Crea indici per performance
    c.execute('CREATE INDEX idx_users_status ON users(status)')
    c.execute('CREATE INDEX idx_users_verified ON users(is_verified)')
    c.execute('CREATE INDEX idx_photos_telegram_id ON verification_photos(telegram_id)')
    
    # Ripristina utenti verificati dal backup
    if backup_data:
        for user in backup_data:
            c.execute('''INSERT INTO users (telegram_id, username, is_verified, status, verification_date) 
                         VALUES (?, ?, 1, 'verified', ?)''', 
                      (user[0], user[1], datetime.now()))
        logger.info(f"Ripristinati {len(backup_data)} utenti verificati")
    
    conn.commit()
    conn.close()
    
    logger.info("Database creato con successo con schema completo")

def init_db():
    """Inizializza il database verificando lo schema"""
    if not os.path.exists(SAVE_DIR):
        os.makedirs(SAVE_DIR)
    
    # Verifica se il database esiste e ha lo schema corretto
    need_reset = False
    
    if os.path.exists(DATABASE):
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        
        try:
            # Verifica che tutte le colonne necessarie esistano
            c.execute("PRAGMA table_info(users)")
            columns = [col[1] for col in c.fetchall()]
            required_columns = ['telegram_id', 'username', 'first_name', 'last_name', 
                               'is_verified', 'status', 'photos_count', 'verification_date', 
                               'last_activity', 'created_at']
            
            for col in required_columns:
                if col not in columns:
                    logger.warning(f"Colonna mancante: {col}")
                    need_reset = True
                    break
                    
        except Exception as e:
            logger.error(f"Errore verifica schema: {e}")
            need_reset = True
        finally:
            conn.close()
    else:
        need_reset = True
    
    if need_reset:
        reset_database()
    else:
        logger.info("Database esistente con schema corretto")

# =====================================================
# 🔍 FUNZIONI DATABASE SICURE
# =====================================================
def update_user_info(user):
    """Aggiorna/inserisce informazioni utente"""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    try:
        # Verifica se l'utente esiste
        c.execute('SELECT telegram_id FROM users WHERE telegram_id = ?', (user.id,))
        exists = c.fetchone() is not None
        
        if exists:
            # Aggiorna utente esistente
            c.execute('''UPDATE users SET 
                         username = ?, 
                         first_name = ?, 
                         last_name = ?, 
                         last_activity = ?
                         WHERE telegram_id = ?''',
                      (user.username, user.first_name, user.last_name, datetime.now(), user.id))
        else:
            # Inserisci nuovo utente
            c.execute('''INSERT INTO users 
                         (telegram_id, username, first_name, last_name, last_activity, status, is_verified, photos_count) 
                         VALUES (?, ?, ?, ?, ?, 'pending', 0, 0)''',
                      (user.id, user.username, user.first_name, user.last_name, datetime.now()))
        
        conn.commit()
        logger.info(f"Utente {user.id} aggiornato")
    except Exception as e:
        logger.error(f"Errore aggiornamento utente: {e}")
        conn.rollback()
    finally:
        conn.close()

def get_user_status(telegram_id):
    """Recupera lo stato dell'utente in modo sicuro"""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    try:
        c.execute('''SELECT status, username, is_verified, photos_count, first_name, last_name
                     FROM users WHERE telegram_id = ?''', (telegram_id,))
        result = c.fetchone()
        
        if result:
            return {
                'status': result[0],
                'username': result[1],
                'is_verified': result[2],
                'photos_count': result[3],
                'first_name': result[4],
                'last_name': result[5]
            }
        return None
    except Exception as e:
        logger.error(f"Errore recupero stato utente: {e}")
        return None
    finally:
        conn.close()

# =====================================================
# 📁 GESTIONE FILE
# =====================================================
def get_user_folder_name(telegram_id, username):
    """Genera nome cartella utente"""
    if username:
        folder_name = re.sub(r'[^a-zA-Z0-9_]', '_', username.lstrip('@'))
    else:
        folder_name = f"user_{telegram_id}"
    return folder_name

def save_photo(telegram_id, username, photo, photo_number):
    """Salva foto dell'utente"""
    folder_name = get_user_folder_name(telegram_id, username)
    user_dir = os.path.join(SAVE_DIR, folder_name)
    if not os.path.exists(user_dir):
        os.makedirs(user_dir)
    
    try:
        file_id = photo[-1].file_id
        file_info = requests.get(f'https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}').json()
        
        if not file_info.get('ok'):
            logger.error(f"Errore recupero file: {file_info}")
            return False
            
        file_path_telegram = file_info['result']['file_path']
        file_url = f'https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path_telegram}'
        file_content = requests.get(file_url).content
        
        local_file_path = os.path.join(user_dir, f'photo{photo_number}.jpg')
        with open(local_file_path, 'wb') as f:
            f.write(file_content)
        
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        
        c.execute('BEGIN TRANSACTION')
        
        c.execute('''INSERT INTO verification_photos 
                     (telegram_id, photo_number, file_path) 
                     VALUES (?, ?, ?)''',
                  (telegram_id, photo_number, local_file_path))
        
        c.execute('''UPDATE users 
                     SET photos_count = photos_count + 1,
                         last_activity = ?
                     WHERE telegram_id = ?''', 
                  (datetime.now(), telegram_id))
        
        c.execute('COMMIT')
        conn.close()
        
        logger.info(f"Foto {photo_number} salvata per utente {telegram_id}")
        return True
        
    except Exception as e:
        logger.error(f"Errore salvataggio foto: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

def clear_user_photos(telegram_id):
    """Elimina foto precedenti dell'utente"""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    try:
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
    except Exception as e:
        logger.error(f"Errore pulizia foto: {e}")
        conn.rollback()
    finally:
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
        f"📸 VERIFICA CON FOTO\n\n"
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
        "✅ VERIFICA COMPLETATA!\n\n"
        f"Hai inviato {REQUIRED_PHOTOS} foto.\n"
        "Richiesta in revisione.\n\n"
        "⏳ Riceverai una notifica a breve."
    )
    
    # Notifica admin
    if user_id != ADMIN_ID:
        try:
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
            
            user_info = f"@{user_data['username']}" if user_data['username'] else f"User {user_id}"
            if user_data['first_name']:
                user_info = f"{user_data['first_name']} {user_data.get('last_name', '')}".strip()
            
            await context.bot.send_message(
                ADMIN_ID, 
                f"🔔 NUOVA VERIFICA\n\n"
                f"Utente: {user_info}\n"
                f"Username: @{user_data['username'] or 'NoUsername'}\n"
                f"ID: {user_id}\n\n"
                f"Azioni:\n"
                f"• /approve_{user_id}\n"
                f"• /reject_{user_id}"
            )
        except Exception as e:
            logger.error(f"Errore notifica admin: {e}")

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
            "❌ SOLO FOTO!\n\n"
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
                "🎉 VERIFICA APPROVATA!\n\n"
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
                "❌ VERIFICA RIFIUTATA\n\n"
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
        "🛠 PANNELLO ADMIN\n\n"
        "Gestione verifiche:\n"
        "• /list_pending - Utenti in attesa\n"
        "• /list_all - Tutti gli utenti\n"
        "• /help - Guida comandi"
    )

# =====================================================
# 📋 COMANDO /list_pending
# =====================================================
async def list_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Non autorizzato")
        return
    
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    try:
        c.execute('''SELECT telegram_id, username, first_name, last_name, photos_count
                     FROM users 
                     WHERE status = 'submitted' 
                     ORDER BY created_at DESC''')
        
        users = c.fetchall()
        
        if not users:
            await update.message.reply_text("✅ Nessun utente in attesa di verifica!")
            return
        
        message = "👥 UTENTI IN ATTESA DI VERIFICA:\n\n"
        
        for user in users:
            tid, username, first_name, last_name, photos = user
            
            # Costruisci nome
            if first_name:
                name = f"{first_name} {last_name or ''}".strip()
            elif username:
                name = f"@{username}"
            else:
                name = f"User {tid}"
            
            message += (
                f"👤 {name}\n"
                f"├ Username: @{username or 'NoUsername'}\n"
                f"├ ID: {tid}\n"
                f"├ Foto inviate: {photos}\n"
                f"└ Azioni: /approve_{tid} | /reject_{tid}\n\n"
            )
        
        await update.message.reply_text(message)
            
    except Exception as e:
        logger.error(f"Errore in list_pending: {e}")
        await update.message.reply_text("❌ Errore nel recupero degli utenti in attesa")
    finally:
        conn.close()

# =====================================================
# 📋 COMANDO /list_all
# =====================================================
async def list_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Non autorizzato")
        return
    
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    try:
        c.execute('''SELECT telegram_id, username, first_name, last_name, status, is_verified
                     FROM users 
                     ORDER BY created_at DESC
                     LIMIT 50''')
        
        users = c.fetchall()
        
        if not users:
            await update.message.reply_text("📭 Nessun utente registrato.")
            return
        
        # Statistiche
        c.execute("SELECT COUNT(*) FROM users")
        total = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM users WHERE is_verified = 1")
        verified = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM users WHERE status = 'submitted'")
        pending = c.fetchone()[0]
        
        message = (
            f"👥 RIEPILOGO UTENTI\n\n"
            f"📊 Statistiche:\n"
            f"├ Totale: {total}\n"
            f"├ Verificati: {verified} ✅\n"
            f"└ In attesa: {pending} ⏳\n\n"
            f"Ultimi 50 utenti:\n"
            f"{'─' * 25}\n\n"
        )
        
        for user in users:
            tid, username, first_name, last_name, status, verified = user
            
            # Nome
            if first_name:
                name = f"{first_name} {last_name or ''}".strip()
            elif username:
                name = f"@{username}"
            else:
                name = f"User {tid}"
            
            # Status icon
            if verified:
                status_icon = "✅"
                status_text = "Verificato"
            elif status == 'submitted':
                status_icon = "⏳"
                status_text = "In attesa"
            elif status == 'collecting':
                status_icon = "📸"
                status_text = "In raccolta"
            elif status == 'rejected':
                status_icon = "❌"
                status_text = "Rifiutato"
            else:
                status_icon = "🔄"
                status_text = status
            
            message += f"{status_icon} {name} ({tid}) - {status_text}\n"
        
        # Invia messaggio
        if len(message) > 4000:
            parts = [message[i:i+4000] for i in range(0, len(message), 4000)]
            for part in parts:
                await update.message.reply_text(part)
        else:
            await update.message.reply_text(message)
            
    except Exception as e:
        logger.error(f"Errore in list_all: {e}")
        await update.message.reply_text("❌ Errore nel recupero della lista utenti")
    finally:
        conn.close()

# =====================================================
# ❓ COMANDO /help
# =====================================================
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id == ADMIN_ID:
        help_text = (
            "🤖 GUIDA ADMIN\n\n"
            "Comandi disponibili:\n"
            "• /admin_panel - Mostra pannello admin\n"
            "• /list_pending - Lista utenti da verificare\n"
            "• /list_all - Lista tutti gli utenti (max 50)\n"
            "• /approve_ID - Approva un utente\n"
            "• /reject_ID - Rifiuta un utente\n\n"
            "Esempio:\n"
            "Per approvare l'utente 123456789:\n"
            "/approve_123456789"
        )
    else:
        help_text = (
            "🤖 COME VERIFICARSI\n\n"
            "1. /verify - Inizia la verifica\n"
            f"2. Invia {REQUIRED_PHOTOS} foto\n"
            "3. /done - Completa la verifica\n"
            "4. Attendi l'approvazione\n\n"
            "⚠️ Importante: Invia solo FOTO durante la verifica!"
        )
    
    await update.message.reply_text(help_text)

# =====================================================
# 🚀 MAIN - AVVIO BOT
# =====================================================
def main():
    """Avvia il bot con gestione errori robusta"""
    try:
        # Gestione event loop
        try:
            loop = asyncio.get_running_loop()
            logger.info("Event loop esistente rilevato")
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            logger.info("Nuovo event loop creato")
        
        # Inizializza database
        init_db()
        
        # Crea applicazione
        application = (
            Application.builder()
            .token(BOT_TOKEN)
            .concurrent_updates(True)
            .connect_timeout(30.0)
            .read_timeout(30.0)
            .write_timeout(30.0)
            .pool_timeout(30.0)
            .build()
        )
        
        # Aggiungi handler comandi base
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("verify", verify))
        application.add_handler(CommandHandler("done", done))
        application.add_handler(CommandHandler("help", help_command))
        
        # Handler comandi admin
        application.add_handler(CommandHandler("admin_panel", admin_panel))
        application.add_handler(CommandHandler("list_pending", list_pending))
        application.add_handler(CommandHandler("list_all", list_all))
        
        # Handler per approve/reject dinamici
        application.add_handler(MessageHandler(
            filters.Regex(r'^/approve_\d+$') & filters.User(user_id=ADMIN_ID), 
            approve
        ))
        application.add_handler(MessageHandler(
            filters.Regex(r'^/reject_\d+$') & filters.User(user_id=ADMIN_ID), 
            reject
        ))
        
        # Handler messaggi generici
        application.add_handler(MessageHandler(
            filters.TEXT | filters.PHOTO, 
            handle_message
        ))
        
        # Error handler
        async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
            """Gestione errori centralizzata"""
            logger.error(msg="Eccezione durante l'elaborazione:", exc_info=context.error)
            
            if update and hasattr(update, 'effective_message'):
                try:
                    await update.effective_message.reply_text(
                        "❌ Si è verificato un errore. Riprova più tardi."
                    )
                except:
                    pass
        
        application.add_error_handler(error_handler)
        
        logger.info("🚀 Bot avviato con successo!")
        logger.info(f"📍 Admin ID: {ADMIN_ID}")
        logger.info(f"📸 Foto richieste: {REQUIRED_PHOTOS}")
        logger.info(f"💾 Database: {DATABASE}")
        
        # Avvia polling
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
            close_loop=False
        )
        
    except KeyboardInterrupt:
        logger.info("⏹️ Bot fermato dall'utente")
    except Exception as e:
        logger.error(f"❌ Errore critico: {e}", exc_info=True)
    finally:
        logger.info("🛑 Bot terminato")

if __name__ == '__main__':
    main()