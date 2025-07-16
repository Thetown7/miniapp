import os
import sqlite3
import json
import asyncio
from datetime import datetime
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, KeyboardButton, ReplyKeyboardMarkup
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

# ================    # Invia ogni punto come messaggio separato
    for point_id, name, address, google_maps_url, apple_maps_url, photo_file_id in points:
        point_text = f"📍 PUNTO #{point_id}\n\n"
        point_text += f"🏪 Nome: {name}\n"
        point_text += f"📍 Indirizzo: {address}\n"
        
        # Link Google Maps
        if google_maps_url:
            point_text += f"🗺️ Google Maps: {google_maps_url}\n"
        else:
            point_text += f"🗺️ Google Maps: Non disponibile\n"
        
        # Link Apple Maps
        if apple_maps_url:
            point_text += f"🍎 Apple Maps: {apple_maps_url}\n"
        else:
            point_text += f"🍎 Apple Maps: Non disponibile\n"
        
        point_text += f"📸 Foto del posto: {'Disponibile' if photo_file_id else 'Non disponibile'}\n"
        point_text += "─" * 30===========================
# ⚙️ CONFIGURAZIONI PRINCIPALI
# =====================================================
DATABASE = 'users.db'
BOT_TOKEN = '7022019844:AAFoBrSCrpK2L2Ex4ptNXn96JGsbn9_BhGY'  # Token del seller bot Selena777_bot
ADMIN_ID = 1300395595
WEBAPP_URL = "https://singular-wisp-d03db1.netlify.app"  # ⚠️ URL TEMPORANEO PER TEST

# =====================================================
# 💾 INIZIALIZZAZIONE TABELLE ORDINI
# =====================================================
def init_orders_db():
    """Inizializza tabelle per gestione ordini"""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    # Tabella ordini
    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER NOT NULL,
        username TEXT,
        order_data TEXT NOT NULL,
        total_amount REAL NOT NULL,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Tabella prodotti ordine
    c.execute('''CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        product_name TEXT NOT NULL,
        product_price REAL NOT NULL,
        quantity INTEGER DEFAULT 1,
        FOREIGN KEY (order_id) REFERENCES orders (id)
    )''')
    
    # Tabella punti vendita/stand
    c.execute('''CREATE TABLE IF NOT EXISTS points (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        address TEXT NOT NULL,
        google_maps_url TEXT,
        apple_maps_url TEXT,
        photo_file_id TEXT,
        is_active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    conn.commit()
    conn.close()
    logger.info("Database ordini e punti vendita inizializzato")

# =====================================================
# 🔍 UTILITY FUNCTIONS
# =====================================================
def get_user_verification_status(telegram_id):
    """Controlla se l'utente è verificato"""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('SELECT is_verified, username, first_name FROM users WHERE telegram_id = ?', (telegram_id,))
    result = c.fetchone()
    conn.close()
    return result

def save_order(telegram_id, username, order_data, total_amount):
    """Salva ordine nel database con stato 'pending'"""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    try:
        # Inserisci ordine principale con stato 'pending'
        c.execute('''INSERT INTO orders (telegram_id, username, order_data, total_amount, status)
                     VALUES (?, ?, ?, ?, 'pending')''',
                  (telegram_id, username, json.dumps(order_data), total_amount))
        
        order_id = c.lastrowid
        
        # Inserisci prodotti dell'ordine
        if 'carrello' in order_data:
            for item in order_data['carrello']:
                c.execute('''INSERT INTO order_items (order_id, product_name, product_price, quantity)
                             VALUES (?, ?, ?, ?)''',
                          (order_id, item.get('nome', 'Prodotto'), item.get('prezzo', 0), 1))
        
        conn.commit()
        logger.info(f"Ordine {order_id} salvato per utente {telegram_id} con stato 'pending'")
        return order_id
        
    except Exception as e:
        logger.error(f"Errore salvataggio ordine: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()

def get_user_orders(telegram_id):
    """Recupera ordini di un utente"""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''SELECT id, total_amount, status, created_at 
                 FROM orders WHERE telegram_id = ? 
                 ORDER BY created_at DESC LIMIT 10''', (telegram_id,))
    result = c.fetchall()
    conn.close()
    return result

def get_order_details(order_id):
    """Recupera dettagli completi di un ordine"""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    # Ordine principale
    c.execute('''SELECT o.*, u.first_name, u.last_name 
                 FROM orders o 
                 LEFT JOIN users u ON o.telegram_id = u.telegram_id 
                 WHERE o.id = ?''', (order_id,))
    order = c.fetchone()
    
    # Prodotti dell'ordine
    c.execute('''SELECT product_name, product_price, quantity 
                 FROM order_items WHERE order_id = ?''', (order_id,))
    items = c.fetchall()
    
    conn.close()
    return order, items

def get_active_points():
    """Recupera tutti i punti vendita attivi"""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''SELECT id, name, address, google_maps_url, apple_maps_url, photo_file_id 
                 FROM points WHERE is_active = 1 
                 ORDER BY created_at DESC''')
    result = c.fetchall()
    conn.close()
    return result

def add_point(name, address, google_maps_url=None, apple_maps_url=None, photo_file_id=None):
    """Aggiunge un nuovo punto vendita"""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    try:
        c.execute('''INSERT INTO points (name, address, google_maps_url, apple_maps_url, photo_file_id)
                     VALUES (?, ?, ?, ?, ?)''',
                  (name, address, google_maps_url, apple_maps_url, photo_file_id))
        point_id = c.lastrowid
        conn.commit()
        logger.info(f"Punto vendita {point_id} aggiunto: {name}")
        return point_id
    except Exception as e:
        logger.error(f"Errore aggiunta punto vendita: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()

def deactivate_point(point_id):
    """Disattiva un punto vendita"""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    try:
        c.execute('UPDATE points SET is_active = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?', 
                  (point_id,))
        conn.commit()
        logger.info(f"Punto vendita {point_id} disattivato")
        return True
    except Exception as e:
        logger.error(f"Errore disattivazione punto vendita: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

# =====================================================
# 🚀 COMANDO /start
# =====================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = get_user_verification_status(user.id)
    
    if not user_data:
        await update.message.reply_text(
            "❌ NON REGISTRATO\n\n"
            "Non sei presente nel sistema di verifica.\n"
            "Contatta il supporto per registrarti."
        )
        return
    
    is_verified, username, first_name = user_data
    
    if is_verified != 1:
        await update.message.reply_text(
            "🔒 ACCESSO NEGATO\n\n"
            "❌ Non sei ancora verificato.\n"
            "Completa prima la verifica con il bot di verifica."
        )
        return
    
    # Utente verificato - mostra menu con pulsanti per apertura WebApp e per visualizzare ordini
    buttons = [
        [KeyboardButton("🛍️ Apri Negozio", web_app=WebAppInfo(url=WEBAPP_URL))],
        # Usa comando /orders per mostrare gli ordini
        [KeyboardButton("/orders")]
    ]
    reply_markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True, one_time_keyboard=True)
    name = first_name or username or "Utente"
    await update.message.reply_text(
        f"🎉 BENVENUTO {name.upper()}!\n\n"
        f"✅ Accesso autorizzato al negozio\n"
        f"Usa i pulsanti qui sotto per navigare:",
        reply_markup=reply_markup
    )

# =====================================================
# 📋 GESTIONE ORDINI UTENTE
# =====================================================
async def my_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra ordini dell'utente o admin panel se admin"""
    user_id = update.effective_user.id
    logger.info(f"🔧 COMANDO /orders ricevuto da {user_id}")
    logger.info(f"🔧 ADMIN_ID configurato: {ADMIN_ID}")
    logger.info(f"🔧 user_id == ADMIN_ID? {user_id == ADMIN_ID}")
    
    # Se è admin, mostra pannello admin
    if user_id == ADMIN_ID:
        logger.info(f"🔧 Utente {user_id} riconosciuto come ADMIN - chiamando admin_orders()")
        await admin_orders(update, context)
        return
    
    logger.info(f"🔧 Utente {user_id} NON è admin - mostrando ordini utente")
    # Altrimenti mostra ordini utente
    orders = get_user_orders(user_id)
    
    if not orders:
        await update.message.reply_text(
            "📋 NESSUN ORDINE\n\n"
            "Non hai ancora effettuato ordini.\n"
            "Usa il bottone 🛍️ per iniziare a fare shopping!"
        )
        return
    
    orders_text = "📋 I TUOI ORDINI\n\n"
    for order_id, total, status, created_at in orders:
        if status == "pending":
            status_emoji = "⏳"
            status_text = "In Attesa"
        elif status == "confirmed":
            status_emoji = "✅"
            status_text = "Confermato"
        elif status == "cancelled":
            status_emoji = "❌"
            status_text = "Annullato"
        elif status == "awaiting_photo":
            status_emoji = "📸"
            status_text = "Attende Foto"
        elif status == "awaiting_delivery_photo":
            status_emoji = "📸"
            status_text = "Attende Foto Consegna"
        else:
            status_emoji = "🔄"
            status_text = status.title()
            
        date = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S").strftime("%d/%m %H:%M")
        orders_text += f"{status_emoji} Ordine #{order_id}\n"
        orders_text += f"💰 €{total:.2f} - {date}\n"
        orders_text += f"📦 {status_text}\n\n"

    await update.message.reply_text(orders_text)

# =====================================================
# 🧾 GENERAZIONE BOLLETTINO ORDINE
# =====================================================
async def generate_order_receipt(order_id, context):
    """Genera bollettino ordine dettagliato"""
    order, items = get_order_details(order_id)
    
    if not order:
        return None
    
    # Dati ordine
    _, telegram_id, username, order_data_str, total_amount, status, created_at, _, first_name, last_name = order
    
    # Parse data ordine
    try:
        order_data = json.loads(order_data_str)
    except:
        order_data = {}
    
    # Costruisci nome cliente
    if first_name:
        customer_name = f"{first_name} {last_name or ''}".strip()
    elif username:
        customer_name = f"@{username}"
    else:
        customer_name = f"User {telegram_id}"
    
    # Data formattata - usa datetime.now() per l'orario locale attuale
    from datetime import datetime
    order_date = datetime.now().strftime("%d/%m/%Y - %H:%M")
    
    # Costruisci bollettino semplificato
    receipt = f"🧾 BOLLETTINO ORDINE #{order_id}\n"
    receipt += "=" * 35 + "\n\n"
    receipt += f"👤 Cliente: {customer_name}\n"
    receipt += f" Data: {order_date}\n\n"
    receipt += "🛒 PRODOTTI:\n"
    receipt += "-" * 35 + "\n"
    
    for product_name, product_price, quantity in items:
        line_total = product_price * quantity
        receipt += f"• {product_name}\n"
        receipt += f"  €{product_price:.2f} x {quantity} = €{line_total:.2f}\n\n"
    
    receipt += "-" * 35 + "\n"
    receipt += f"💰 TOTALE: €{total_amount:.2f}\n"
    receipt += "=" * 35
    
    return receipt

# =====================================================
# 📨 GESTIONE DATI DA MINI-APP
# =====================================================
async def handle_webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestisce dati ricevuti dalla mini-app"""
    try:
        logger.info("🔄 Ricevuti dati da WebApp")
        logger.info(f"Update completo: {update}")
        
        # Parse dati dalla mini-app
        data = json.loads(update.effective_message.web_app_data.data)
        user = update.effective_user
        
        logger.info(f"📦 Dati ricevuti da {user.id} (@{user.username}): {data}")
        
        if data.get('azione') == 'ordine_finale':
            # Elabora ordine finale
            carrello = data.get('carrello', [])
            totale = data.get('totale', 0)
            
            logger.info(f"🛒 Elaborazione ordine - Carrello: {len(carrello)} items, Totale: €{totale}")
            
            if not carrello:
                await update.effective_message.reply_text("❌ Carrello vuoto!")
                return
            
            # Salva ordine nel database
            order_id = save_order(user.id, user.username, data, totale)
            logger.info(f"💾 Ordine salvato con ID: {order_id}")
            
            if order_id:
                # Genera e invia bollettino immediatamente
                receipt = await generate_order_receipt(order_id, context)
                
                if receipt:
                    await update.effective_message.reply_text(
                        f"✅ ORDINE CONFERMATO!\n\n{receipt}"
                    )
                else:
                    await update.effective_message.reply_text(
                        f"✅ Ordine #{order_id} confermato!\n"
                        f"💰 Totale: €{totale:.2f}\n\n"
                        f"Riceverai aggiornamenti sullo stato."
                    )
                
                # Notifica admin del nuovo ordine
                await notify_admin_new_order(context, order_id)
                logger.info(f"📢 Notifica admin inviata per ordine {order_id}")
            else:
                logger.error("❌ Errore nel salvataggio dell'ordine")
                await update.effective_message.reply_text(
                    "❌ Errore nel salvataggio dell'ordine.\n"
                    "Riprova o contatta il supporto."
                )
        else:
            logger.warning(f"⚠️ Azione non riconosciuta: {data.get('azione')}")
        
    except Exception as e:
        logger.error(f"❌ Errore gestione dati webapp: {e}", exc_info=True)
        await update.effective_message.reply_text(
            "❌ Errore nell'elaborazione dell'ordine.\n"
            "Riprova più tardi."
        )

# =====================================================
# 🔔 NOTIFICHE ADMIN
# =====================================================
async def notify_admin_new_order(context, order_id):
    """Notifica admin di nuovo ordine con info cliente dettagliate"""
    try:
        # Ottieni dettagli ordine e cliente
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        
        # Query con JOIN per ottenere anche le info utente
        c.execute('''SELECT o.id, o.telegram_id, o.username, o.total_amount, o.status, o.created_at,
                            u.first_name, u.last_name, u.username as user_username
                     FROM orders o 
                     LEFT JOIN users u ON o.telegram_id = u.telegram_id
                     WHERE o.id = ?''', (order_id,))
        order_data = c.fetchone()
        conn.close()
        
        if not order_data:
            logger.error(f"Ordine {order_id} non trovato per notifica admin")
            return
        
        order_id, telegram_id, order_username, total_amount, status, created_at, first_name, last_name, user_username = order_data
        
        # Costruisci nome cliente
        client_name = ""
        if first_name or last_name:
            client_name = f"{first_name or ''} {last_name or ''}".strip()
        
        # Username (priorità a quello dal database users, fallback su order)
        username = user_username or order_username or "N/A"
        
        # Formatta data
        date = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S").strftime("%d/%m %H:%M")
        
        # Genera bollettino per la notifica
        receipt = await generate_order_receipt(order_id, context)
        
        # Messaggio notifica con info cliente dettagliate
        notification_text = f"🔔 NUOVO ORDINE #{order_id}\n\n"
        notification_text += f"👤 Cliente: {client_name if client_name else 'N/A'}\n"
        notification_text += f"📱 Username: @{username}\n"
        notification_text += f"🆔 ID: {telegram_id}\n"
        notification_text += f"📅 Data: {date}\n"
        notification_text += f"💰 Totale: €{total_amount:.2f}\n\n"
        
        if receipt:
            notification_text += f"📋 DETTAGLI:\n{receipt.split('PRODOTTI:')[1] if 'PRODOTTI:' in receipt else receipt}"
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Conferma", callback_data=f"order_confirm_{order_id}"),
                InlineKeyboardButton("❌ Annulla", callback_data=f"order_cancel_{order_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            ADMIN_ID,
            notification_text,
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Errore notifica admin: {e}")
        # Fallback - notifica semplice
        try:
            await context.bot.send_message(
                ADMIN_ID,
                f"🔔 NUOVO ORDINE #{order_id}\n\n"
                f"⚠️ Errore nel recupero dettagli.\n"
                f"Controlla manualmente con /orders"
            )
        except Exception as e2:
            logger.error(f"Errore anche nella notifica fallback: {e2}")

# =====================================================
# 🎛️ COMANDI ADMIN
# =====================================================
async def admin_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lista ordini per admin con info cliente dettagliate"""
    logger.info(f"🔧 admin_orders() chiamata da {update.effective_user.id}")
    
    if update.effective_user.id != ADMIN_ID:
        logger.warning(f"🔧 ACCESSO NEGATO - {update.effective_user.id} non è {ADMIN_ID}")
        await update.message.reply_text("❌ Accesso negato")
        return
    
    logger.info(f"🔧 ADMIN verificato - recupero ordini con info clienti dal database")
    
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    # Query con JOIN per ottenere anche le info utente
    c.execute('''SELECT o.id, o.telegram_id, o.username, o.total_amount, o.status, o.created_at,
                        u.first_name, u.last_name, u.username as user_username
                 FROM orders o 
                 LEFT JOIN users u ON o.telegram_id = u.telegram_id
                 ORDER BY o.created_at DESC LIMIT 20''')
    orders = c.fetchall()
    conn.close()
    
    logger.info(f"🔧 Trovati {len(orders)} ordini nel database")
    
    if not orders:
        await update.message.reply_text("📋 Nessun ordine presente")
        return
    
    orders_text = "🔧 GESTIONE ORDINI ADMIN\n\n"
    
    for order_id, telegram_id, order_username, total, status, created_at, first_name, last_name, user_username in orders:
        # Determina emoji stato
        if status == "pending":
            status_emoji = "⏳"
        elif status == "confirmed":
            status_emoji = "✅"
        elif status == "cancelled":
            status_emoji = "❌"
        elif status == "awaiting_photo":
            status_emoji = "📸"
        elif status == "awaiting_delivery_photo":
            status_emoji = "📸"
        else:
            status_emoji = "🔄"
        
        # Formatta data
        date = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S").strftime("%d/%m %H:%M")
        
        # Costruisci nome cliente
        client_name = ""
        if first_name or last_name:
            client_name = f"{first_name or ''} {last_name or ''}".strip()
        
        # Username (priorità a quello dal database users, fallback su order)
        username = user_username or order_username or "N/A"
        
        orders_text += f"{status_emoji} ORDINE #{order_id}\n"
        orders_text += f"👤 Cliente: {client_name if client_name else 'N/A'}\n"
        orders_text += f"📱 Username: @{username}\n"
        orders_text += f"🆔 ID: {telegram_id}\n"
        orders_text += f"💰 Totale: €{total:.2f}\n"
        orders_text += f"📅 Data: {date}\n"
        orders_text += f"📦 Stato: {status.title()}\n"
        orders_text += "─" * 30 + "\n\n"
    
    logger.info(f"🔧 Invio lista ordini admin dettagliata")
    
    # Se il messaggio è troppo lungo, dividi in più parti
    if len(orders_text) > 4000:
        # Dividi in chunks
        parts = orders_text.split("─" * 30 + "\n\n")
        current_message = "🔧 GESTIONE ORDINI ADMIN\n\n"
        
        for part in parts[1:]:  # Salta la prima parte che è solo l'header
            if len(current_message + part + "─" * 30 + "\n\n") > 4000:
                await update.message.reply_text(current_message.strip())
                current_message = part + "─" * 30 + "\n\n"
            else:
                current_message += part + "─" * 30 + "\n\n"
        
        if current_message.strip():
            await update.message.reply_text(current_message.strip())
    else:
        await update.message.reply_text(orders_text)

# =====================================================
# 📸 GESTIONE FOTO E FINALIZZAZIONE ORDINI
# =====================================================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestisce le foto inviate dagli utenti per la consegna"""
    user = update.effective_user
    
    # Verifica se l'utente ha ordini in attesa di foto consegna
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''SELECT id FROM orders 
                 WHERE telegram_id = ? AND status = 'awaiting_delivery_photo' 
                 ORDER BY created_at DESC LIMIT 1''', (user.id,))
    result = c.fetchone()
    
    if not result:
        await update.message.reply_text(
            "📸 Foto ricevuta, ma non hai ordini in attesa di foto consegna.\n"
            "La foto deve essere inviata solo dopo la conferma dell'ordine."
        )
        conn.close()
        return
    
    order_id = result[0]
    
    # Aggiorna stato ordine a 'confirmed' dopo ricezione foto
    c.execute('UPDATE orders SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', 
              ('confirmed', order_id))
    conn.commit()
    conn.close()
    
    # Conferma ricezione foto al cliente
    await update.message.reply_text(
        f"📸 Foto ricevuta per l'ordine #{order_id}!\n\n"
        f"✅ La consegna può ora essere avviata.\n"
        f"Riceverai aggiornamenti quando il rider sarà in arrivo."
    )
    
    # Inoltra la foto all'admin per verifica
    try:
        # Ottieni info cliente per la notifica admin
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute('''SELECT o.telegram_id, u.first_name, u.last_name, u.username as user_username
                     FROM orders o 
                     LEFT JOIN users u ON o.telegram_id = u.telegram_id
                     WHERE o.id = ?''', (order_id,))
        client_info = c.fetchone()
        conn.close()
        
        if client_info:
            telegram_id, first_name, last_name, username = client_info
            client_name = f"{first_name or ''} {last_name or ''}".strip() or f"@{username}" or f"User {telegram_id}"
        else:
            client_name = f"User {user.id}"
        
        # Inoltra foto all'admin
        await context.bot.forward_message(
            chat_id=ADMIN_ID,
            from_chat_id=update.effective_chat.id,
            message_id=update.message.message_id
        )
        
        # Invia info sull'ordine insieme alla foto
        await context.bot.send_message(
            ADMIN_ID,
            f"📸 FOTO POSTO CONSEGNA\n\n"
            f"🆔 Ordine: #{order_id}\n"
            f"👤 Cliente: {client_name}\n"
            f"🆔 User ID: {user.id}\n\n"
            f"✅ Foto ricevuta - Consegna può partire"
        )
        
        logger.info(f"Foto consegna ordine {order_id} inoltrata all'admin")
        
    except Exception as e:
        logger.error(f"Errore inoltrando foto all'admin: {e}")
        # Notifica admin anche se l'inoltro fallisce
        await context.bot.send_message(
            ADMIN_ID,
            f"📸 FOTO CONSEGNA RICEVUTA\n\n"
            f"🆔 Ordine: #{order_id}\n"
            f"👤 Cliente: User {user.id}\n\n"
            f"⚠️ Errore nell'inoltro foto, ma foto ricevuta."
        )

async def done_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando di supporto - non più necessario nel nuovo flusso"""
    await update.message.reply_text(
        "ℹ️ COMANDO NON NECESSARIO\n\n"
        "Il comando /done non è più necessario.\n\n"
        "Nuovo flusso:\n"
        "1. Effettua ordine dalla mini-app\n"
        "2. Ricevi subito il bollettino\n"
        "3. Attendi conferma dell'admin\n"
        "4. Invia foto posto consegna quando richiesto\n"
        "5. La consegna partirà automaticamente"
    )

# =====================================================
# 📍 GESTIONE PUNTI VENDITA
# =====================================================
async def points_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra punti vendita attivi - solo per admin"""
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ Comando riservato agli amministratori")
        return
    
    logger.info(f"🔧 COMANDO /point ricevuto da admin {user_id}")
    
    # Recupera punti vendita attivi
    points = get_active_points()
    
    if not points:
        await update.message.reply_text(
            "📍 NESSUN PUNTO ATTIVO\n\n"
            "Non ci sono punti vendita attivi al momento.\n"
            "Per aggiungere nuovi punti, contatta lo sviluppatore."
        )
        return
    
    await update.message.reply_text(f"📍 PUNTI VENDITA ATTIVI ({len(points)})\n\n")
    
    # Invia ogni punto come messaggio separato
    for point_id, name, address, maps_url, photo_file_id in points:
        point_text = f"📍 PUNTO #{point_id}\n\n"
        point_text += f"🏪 Nome: {name}\n"
        point_text += f"📍 Indirizzo: {address}\n"
        
        if maps_url:
            point_text += f"�️ Mappe: {maps_url}\n"
        
        point_text += "─" * 30
        
        try:
            if photo_file_id:
                # Invia foto con descrizione
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=photo_file_id,
                    caption=point_text
                )
            else:
                # Invia solo testo
                await update.message.reply_text(point_text)
                
        except Exception as e:
            logger.error(f"Errore invio punto {point_id}: {e}")
            # Fallback senza foto
            await update.message.reply_text(
                f"{point_text}\n\n⚠️ Foto non disponibile"
            )

# =====================================================
# ❓ COMANDO /help
# =====================================================
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ADMIN_ID:
        help_text = (
            "🔧 COMANDI ADMIN SELLER BOT\n\n"
            "📋 GESTIONE:\n"
            "• /start - Menu principale\n"
            "• /orders - Gestione ordini\n"
            "• /help - Questa guida\n\n"
            "📍 PUNTI VENDITA:\n"
            "• /point - Visualizza punti attivi\n"
            "• /add_point - Aggiungi nuovo punto\n"
            "• /edit_point - Modifica punto esistente\n"
            "• /toggle_point - Attiva/disattiva punto\n\n"
            "Il bot riceve automaticamente gli ordini dalla mini-app\n"
            "e genera bollettini dettagliati.\n\n"
            "🆕 FORMATO PUNTI:\n"
            "Nome, Indirizzo, Indirizzo Maps, Foto del posto"
        )
    else:
        help_text = (
            "🛍️ GUIDA SHOPPING\n\n"
            "• /start - Apri il negozio\n"
            "• /orders - I tuoi ordini\n"
            "• /help - Questa guida\n\n"
            "🔄 NUOVO FLUSSO ORDINI:\n"
            "1. Clicca 'Apri Negozio' per fare shopping\n"
            "2. Aggiungi prodotti al carrello\n"
            "3. Completa l'ordine nella mini-app\n"
            "4. Ricevi subito il bollettino\n"
            "5. Attendi conferma dell'admin\n"
            "6. Invia foto posto consegna quando richiesto\n"
            "7. La consegna partirà automaticamente"
        )
    
    await update.message.reply_text(help_text)

# =====================================================
# 🎛️ GESTIONE CALLBACK QUERY
# =====================================================
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestisce i callback dei bottoni inline"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "my_orders":
        await my_orders_callback(query, context)
    elif query.data.startswith("order_confirm_"):
        await handle_admin_order_action(query, context, "confirm")
    elif query.data.startswith("order_cancel_"):
        await handle_admin_order_action(query, context, "cancel")

async def handle_admin_order_action(query, context, action):
    """Gestisce le azioni admin sui bottoni ordine"""
    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("❌ Non autorizzato")
        return
    
    # Estrai order_id dal callback_data
    order_id = int(query.data.split("_")[-1])
    
    # Aggiorna stato ordine nel database
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    if action == "confirm":
        new_status = "awaiting_delivery_photo"
        status_text = "✅ CONFERMATO - ATTENDE FOTO"
        c.execute('UPDATE orders SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', 
                  (new_status, order_id))
    else:  # cancel
        new_status = "cancelled"
        status_text = "❌ ANNULLATO"
        c.execute('UPDATE orders SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', 
                  (new_status, order_id))
    
    conn.commit()
    conn.close()
    
    # Aggiorna il messaggio rimuovendo i pulsanti
    await query.edit_message_text(
        f"{query.message.text}\n\n🔄 STATO AGGIORNATO: {status_text}",
        reply_markup=None
    )
    
    # Notifica il cliente
    order, items = get_order_details(order_id)
    if order:
        telegram_id = order[1]
        try:
            if action == "confirm":
                await context.bot.send_message(
                    telegram_id,
                    f"✅ Ordine #{order_id} CONFERMATO!\n\n"
                    f"Il tuo ordine è stato confermato e verrà preparato a breve.\n"
                    f"Tempo stimato: 30-45 minuti.\n\n"
                    f"📸 FOTO RICHIESTA\n"
                    f"Per procedere con la consegna, invia una foto del posto dove ti trovi.\n"
                    f"Questo aiuterà il nostro team a localizzarti facilmente."
                )
            else:
                await context.bot.send_message(
                    telegram_id,
                    f"❌ Ordine #{order_id} ANNULLATO\n\n"
                    f"Il tuo ordine è stato annullato.\n"
                    f"Per informazioni contatta il supporto."
                )
        except Exception as e:
            logger.error(f"Errore notifica cliente: {e}")

async def my_orders_callback(query, context):
    """Mostra ordini dell'utente da callback"""
    user_id = query.from_user.id
    orders = get_user_orders(user_id)
    
    if not orders:
        # Mostra bottone per aprire la mini-app invece del link testuale
        keyboard = [
            [InlineKeyboardButton("🛍️ Apri Negozio", web_app=WebAppInfo(url=WEBAPP_URL))]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "📋 NESSUN ORDINE\n\n"
            "Non hai ancora effettuato ordini.\n"
            "👇 Clicca per aprire il negozio:",
            reply_markup=reply_markup
        )
        return
    
    orders_text = "📋 I TUOI ORDINI\n\n"
    for order_id, total, status, created_at in orders:
        if status == "pending":
            status_emoji = "⏳"
            status_text = "In Attesa"
        elif status == "confirmed":
            status_emoji = "✅"
            status_text = "Confermato"
        elif status == "cancelled":
            status_emoji = "❌"
            status_text = "Annullato"
        elif status == "awaiting_photo":
            status_emoji = "📸"
            status_text = "Attende Foto"
        elif status == "awaiting_delivery_photo":
            status_emoji = "📸"
            status_text = "Attende Foto Consegna"
        else:
            status_emoji = "🔄"
            status_text = status.title()
            
        date = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S").strftime("%d/%m %H:%M")
        orders_text += f"{status_emoji} Ordine #{order_id}\n"
        orders_text += f"💰 €{total:.2f} - {date}\n"
        orders_text += f"📦 {status_text}\n\n"

    await query.edit_message_text(orders_text)

# =====================================================
# 🚀 MAIN - AVVIO BOT
# =====================================================
def main():
    """Avvia il seller bot"""
    
    # Verifica configurazione
    if BOT_TOKEN == 'TUO_SELLER_BOT_TOKEN_QUI':
        logger.error("❌ ERRORE: Configura il BOT_TOKEN nel codice!")
        return
    
    if WEBAPP_URL == "http://192.168.1.2:3000":
        logger.warning("⚠️ Ricorda di configurare WEBAPP_URL con il tuo IP!")
    
    try:
        # Inizializza database
        init_orders_db()
        
        # Crea application
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Handler comandi
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("orders", my_orders))
        application.add_handler(CommandHandler("point", points_command))
        application.add_handler(CommandHandler("done", done_command))
        application.add_handler(CommandHandler("help", help_command))
        
        # Handler callback query
        application.add_handler(CallbackQueryHandler(handle_callback_query))
        
        # Handler admin
        application.add_handler(CommandHandler("admin_orders", admin_orders))
        
        # Handler foto
        application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
        
        # Handler dati da mini-app CON SUPER LOGGING
        async def webapp_data_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
            logger.info("🔥🔥🔥 RICEVUTO QUALCOSA DA WEBAPP! 🔥🔥🔥")
            logger.info(f"Update completo: {update}")
            logger.info(f"Message: {update.message}")
            logger.info(f"Effective message: {update.effective_message}")
            await handle_webapp_data(update, context)
        
        application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, webapp_data_handler))
        
        # Error handler
        async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
            logger.error(msg="Eccezione:", exc_info=context.error)
        
        application.add_error_handler(error_handler)
        
        logger.info("🛍️ Seller Bot avviato con successo!")
        logger.info(f"📍 Admin ID: {ADMIN_ID}")
        logger.info(f"🌐 WebApp URL: {WEBAPP_URL}")
        
        # Avvia polling
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )
        
    except KeyboardInterrupt:
        logger.info("⏹️ Seller Bot fermato dall'utente")
    except Exception as e:
        logger.error(f"❌ Errore critico: {e}", exc_info=True)
    finally:
        logger.info("🛑 Seller Bot terminato")

if __name__ == '__main__':
    main()
