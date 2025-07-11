import os
import sqlite3
import json
import requests
import re
import asyncio
from datetime import datetime
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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
    
    # Notifica admin con sistema organizzato
    if user_id != ADMIN_ID:
        await notifica_admin_nuova_verifica(context, user_id)

# =====================================================
# 🔔 SISTEMA NOTIFICHE ADMIN ORGANIZZATO
# =====================================================
async def notifica_admin_nuova_verifica(context, user_id):
    """Invia notifica organizzata all'admin per nuova verifica"""
    try:
        # Recupera info utente
        user_data = get_user_status(user_id)
        
        # Costruisci nome utente
        user_info = f"@{user_data['username']}" if user_data['username'] else f"User {user_id}"
        if user_data['first_name']:
            user_info = f"{user_data['first_name']} {user_data.get('last_name', '')}".strip()
        
        # Crea bottoni inline
        keyboard = [
            [
                InlineKeyboardButton("👁 Vedi Foto", callback_data=f"view_{user_id}"),
                InlineKeyboardButton("✅ Approva", callback_data=f"approve_{user_id}"),
                InlineKeyboardButton("❌ Rifiuta", callback_data=f"reject_{user_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Invia notifica compatta
        await context.bot.send_message(
            ADMIN_ID,
            f"🔔 **NUOVA VERIFICA**\n\n"
            f"👤 **Utente**: {user_info}\n"
            f"📱 **Username**: @{user_data['username'] or 'NoUsername'}\n"
            f"🆔 **ID**: `{user_id}`\n"
            f"📸 **Foto inviate**: {user_data['photos_count']}\n"
            f"⏰ **Ricevuta**: Adesso\n",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Errore notifica admin: {e}")

# =====================================================
# 🎛️ GESTIONE CALLBACK BOTTONI
# =====================================================
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestisce i click sui bottoni inline"""
    query = update.callback_query
    await query.answer()
    
    # Verifica che sia l'admin
    if query.from_user.id != ADMIN_ID:
        await query.answer("❌ Non autorizzato", show_alert=True)
        return
    
    data = query.data
    
    # View photos
    if data.startswith("view_"):
        user_id = int(data.replace("view_", ""))
        await mostra_foto_utente(query, context, user_id)
    
    # Approve
    elif data.startswith("approve_"):
        user_id = int(data.replace("approve_", ""))
        await approva_da_callback(query, context, user_id)
    
    # Reject
    elif data.startswith("reject_"):
        user_id = int(data.replace("reject_", ""))
        await rifiuta_da_callback(query, context, user_id)
    
    # Show pending dal pannello
    elif data == "show_pending":
        await mostra_pending_callback(query, context)
    
    # Show all dal pannello
    elif data == "show_all":
        await mostra_all_callback(query, context)
    
    # Show help dal pannello
    elif data == "show_help":
        await mostra_help_callback(query, context)

async def mostra_pending_callback(query, context):
    """Mostra verifiche pending da callback"""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    try:
        c.execute('''SELECT telegram_id, username, first_name, last_name, photos_count
                     FROM users 
                     WHERE status = 'submitted' 
                     ORDER BY created_at DESC''')
        
        users = c.fetchall()
        
        if not users:
            await query.edit_message_text("✅ Nessuna verifica in attesa!")
            return
        
        # Modifica il messaggio originale
        await query.edit_message_text(f"🔔 **VERIFICHE IN ATTESA ({len(users)})**", parse_mode='Markdown')
        
        # Invia un messaggio per ogni utente con bottoni
        for user in users:
            tid, username, first_name, last_name, photos = user
            
            # Costruisci nome
            if first_name:
                name = f"{first_name} {last_name or ''}".strip()
            elif username:
                name = f"@{username}"
            else:
                name = f"User {tid}"
            
            # Crea bottoni
            keyboard = [
                [
                    InlineKeyboardButton("👁 Vedi", callback_data=f"view_{tid}"),
                    InlineKeyboardButton("✅ Approva", callback_data=f"approve_{tid}"),
                    InlineKeyboardButton("❌ Rifiuta", callback_data=f"reject_{tid}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await context.bot.send_message(
                ADMIN_ID,
                f"👤 **{name}**\n"
                f"📱 @{username or 'NoUsername'}\n"
                f"🆔 `{tid}`\n"
                f"📸 {photos} foto",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
    except Exception as e:
        logger.error(f"Errore in mostra_pending_callback: {e}")
        await query.answer("❌ Errore", show_alert=True)
    finally:
        conn.close()

async def mostra_all_callback(query, context):
    """Mostra tutti gli utenti da callback"""
    # Usa la funzione list_all esistente ma adattata per callback
    await query.answer("Caricamento lista...")
    await query.message.reply_text("Usa /list_all per vedere tutti gli utenti")

async def mostra_help_callback(query, context):
    """Mostra help da callback"""
    help_text = (
        "🤖 **GUIDA ADMIN**\n\n"
        "**Comandi rapidi:**\n"
        "• /verifiche - Mostra verifiche organizzate\n"
        "• /list_pending - Lista testuale pending\n"
        "• /list_all - Lista tutti gli utenti\n\n"
        "**Bottoni:**\n"
        "• 👁 = Visualizza foto\n"
        "• ✅ = Approva utente\n"
        "• ❌ = Rifiuta utente\n\n"
        "**Gestione manuale:**\n"
        "• /approve_ID - Approva manualmente\n"
        "• /reject_ID - Rifiuta manualmente"
    )
    await query.edit_message_text(help_text, parse_mode='Markdown')

async def mostra_foto_utente(query, context, user_id):
    """Mostra le foto dell'utente quando richiesto"""
    try:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute('SELECT file_path FROM verification_photos WHERE telegram_id = ? ORDER BY photo_number', (user_id,))
        photos = c.fetchall()
        conn.close()
        
        if not photos:
            await query.answer("❌ Nessuna foto trovata", show_alert=True)
            return
        
        # Invia messaggio informativo
        await query.message.reply_text(f"📸 Foto dell'utente {user_id}:")
        
        # Invia le foto
        for i, (photo_path,) in enumerate(photos, 1):
            if os.path.exists(photo_path):
                with open(photo_path, 'rb') as f:
                    await context.bot.send_photo(
                        ADMIN_ID, 
                        f, 
                        caption=f"📸 Foto {i}/{len(photos)} - User {user_id}"
                    )
        
        # Aggiungi bottoni di azione dopo le foto
        keyboard = [
            [
                InlineKeyboardButton("✅ Approva", callback_data=f"approve_{user_id}"),
                InlineKeyboardButton("❌ Rifiuta", callback_data=f"reject_{user_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.reply_text(
            f"Cosa vuoi fare con l'utente {user_id}?",
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Errore mostra foto: {e}")
        await query.answer("❌ Errore nel mostrare le foto", show_alert=True)

async def approva_da_callback(query, context, user_id):
    """Approva utente da callback"""
    try:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute('''UPDATE users SET is_verified = 1, status = 'verified', 
                     verification_date = ? WHERE telegram_id = ?''', 
                  (datetime.now(), user_id))
        conn.commit()
        conn.close()
        
        # Notifica utente
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
        
        # Aggiorna messaggio admin
        await query.edit_message_text(
            query.message.text + "\n\n✅ **APPROVATO**",
            parse_mode='Markdown'
        )
        
        await query.answer("✅ Utente approvato!", show_alert=True)
        
    except Exception as e:
        logger.error(f"Errore approvazione: {e}")
        await query.answer("❌ Errore nell'approvazione", show_alert=True)

async def rifiuta_da_callback(query, context, user_id):
    """Rifiuta utente da callback"""
    try:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute('''UPDATE users SET status = 'rejected', photos_count = 0 
                     WHERE telegram_id = ?''', (user_id,))
        conn.commit()
        conn.close()
        
        clear_user_photos(user_id)
        
        # Notifica utente
        try:
            await context.bot.send_message(
                user_id, 
                "❌ VERIFICA RIFIUTATA\n\n"
                "Le foto non sono valide.\n\n"
                "Puoi riprovare con /verify"
            )
        except Exception as e:
            logger.error(f"Errore notifica utente: {e}")
        
        # Aggiorna messaggio admin
        await query.edit_message_text(
            query.message.text + "\n\n❌ **RIFIUTATO**",
            parse_mode='Markdown'
        )
        
        await query.answer("❌ Utente rifiutato!", show_alert=True)
        
    except Exception as e:
        logger.error(f"Errore rifiuto: {e}")
        await query.answer("❌ Errore nel rifiuto", show_alert=True)

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
# 📋 COMANDO /verifiche - MOSTRA TUTTE LE VERIFICHE PENDING
# =====================================================
async def verifiche(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra tutte le verifiche pending in modo organizzato"""
    if update.effective_user.id != ADMIN_ID:
        return
    
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    try:
        c.execute('''SELECT telegram_id, username, first_name, last_name, photos_count, created_at
                     FROM users 
                     WHERE status = 'submitted' 
                     ORDER BY created_at DESC''')
        
        users = c.fetchall()
        
        if not users:
            await update.message.reply_text("✅ Nessuna verifica in attesa!")
            return
        
        message = f"🔔 **VERIFICHE IN ATTESA ({len(users)})**\n\n"
        
        for idx, user in enumerate(users, 1):
            tid, username, first_name, last_name, photos, created = user
            
            # Costruisci nome
            if first_name:
                name = f"{first_name} {last_name or ''}".strip()
            elif username:
                name = f"@{username}"
            else:
                name = f"User {tid}"
            
            # Calcola tempo trascorso
            if created:
                try:
                    created_time = datetime.strptime(created, "%Y-%m-%d %H:%M:%S")
                    elapsed = datetime.now() - created_time
                    if elapsed.days > 0:
                        time_str = f"{elapsed.days}g fa"
                    elif elapsed.seconds > 3600:
                        time_str = f"{elapsed.seconds // 3600}h fa"
                    else:
                        time_str = f"{elapsed.seconds // 60}min fa"
                except:
                    time_str = "N/A"
            else:
                time_str = "N/A"
            
            message += f"{idx}️⃣ **{name}**\n"
            message += f"   📸 {photos} foto • ⏰ {time_str}\n\n"
            
            # Crea bottoni per ogni utente
            keyboard = [
                [
                    InlineKeyboardButton("👁", callback_data=f"view_{tid}"),
                    InlineKeyboardButton("✅", callback_data=f"approve_{tid}"),
                    InlineKeyboardButton("❌", callback_data=f"reject_{tid}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Invia messaggio separato per ogni utente con bottoni
            if idx == 1:
                await update.message.reply_text(message, parse_mode='Markdown')
                message = ""
            
            await update.message.reply_text(
                f"**{name}** (`{tid}`)\n"
                f"📸 {photos} foto • ⏰ {time_str}",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
    except Exception as e:
        logger.error(f"Errore in verifiche: {e}")
        await update.message.reply_text("❌ Errore nel recupero delle verifiche")
    finally:
        conn.close()

# =====================================================
# 📊 COMANDO /admin_panel AGGIORNATO
# =====================================================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    
    # Crea bottoni inline per il pannello admin
    keyboard = [
        [InlineKeyboardButton("🔔 Verifiche Pending", callback_data="show_pending")],
        [InlineKeyboardButton("📋 Lista Tutti", callback_data="show_all")],
        [InlineKeyboardButton("❓ Aiuto", callback_data="show_help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🛠 **PANNELLO ADMIN**\n\n"
        "Seleziona un'opzione:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
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
            "Sistema Verifiche Organizzato:\n"
            "• /admin_panel - Pannello con bottoni\n"
            "• /verifiche - Mostra verifiche con bottoni interattivi\n\n"
            "Comandi classici:\n"
            "• /list_pending - Lista testuale pending\n"
            "• /list_all - Lista tutti gli utenti\n"
            "• /approve_ID - Approva manualmente\n"
            "• /reject_ID - Rifiuta manualmente\n\n"
            "Nuovo sistema:\n"
            "- Le foto vengono mostrate solo cliccando 👁\n"
            "- Puoi approvare/rifiutare con un click\n"
            "- Notifiche più ordinate e compatte"
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
        
        # Handler per callback query (bottoni)
        application.add_handler(CallbackQueryHandler(handle_callback_query))
        
        # Handler per il comando verifiche
        application.add_handler(CommandHandler("verifiche", verifiche))
        
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