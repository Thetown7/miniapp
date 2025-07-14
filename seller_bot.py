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

# =====================================================
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
    
    conn.commit()
    conn.close()
    logger.info("Database ordini inizializzato")

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
    """Salva ordine nel database"""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    try:
        # Inserisci ordine principale
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
        logger.info(f"Ordine {order_id} salvato per utente {telegram_id}")
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
    """Mostra ordini dell'utente"""
    user_id = update.effective_user.id
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
        status_emoji = "⏳" if status == "pending" else "✅" if status == "completed" else "🔄"
        date = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S").strftime("%d/%m %H:%M")
        orders_text += f"{status_emoji} Ordine #{order_id}\n"
        orders_text += f"💰 €{total:.2f} - {date}\n"
        orders_text += f"📦 {status.title()}\n\n"
    
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
                # Genera bollettino per il cliente
                receipt = await generate_order_receipt(order_id, context)
                
                if receipt:
                    await update.effective_message.reply_text(
                        f"✅ ORDINE CONFERMATO!\n\n{receipt}"
                    )
                    
                    # Notifica admin del nuovo ordine
                    await notify_admin_new_order(context, order_id)
                    logger.info(f"📢 Notifica admin inviata per ordine {order_id}")
                else:
                    await update.effective_message.reply_text(
                        f"✅ Ordine #{order_id} confermato!\n"
                        f"💰 Totale: €{totale:.2f}\n\n"
                        f"Riceverai aggiornamenti sullo stato."
                    )
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
    """Notifica admin di nuovo ordine"""
    try:
        receipt = await generate_order_receipt(order_id, context)
        
        if receipt:
            keyboard = [
                [
                    InlineKeyboardButton("✅ Conferma", callback_data=f"order_confirm_{order_id}"),
                    InlineKeyboardButton("❌ Annulla", callback_data=f"order_cancel_{order_id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await context.bot.send_message(
                ADMIN_ID,
                f"🔔 NUOVO ORDINE!\n\n{receipt}",
                reply_markup=reply_markup
            )
    except Exception as e:
        logger.error(f"Errore notifica admin: {e}")

# =====================================================
# 🎛️ COMANDI ADMIN
# =====================================================
async def admin_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lista ordini per admin"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Accesso negato")
        return
    
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''SELECT id, telegram_id, total_amount, status, created_at 
                 FROM orders ORDER BY created_at DESC LIMIT 20''')
    orders = c.fetchall()
    conn.close()
    
    if not orders:
        await update.message.reply_text("📋 Nessun ordine presente")
        return
    
    orders_text = "🔧 GESTIONE ORDINI ADMIN\n\n"
    for order_id, user_id, total, status, created_at in orders:
        status_emoji = "⏳" if status == "pending" else "✅" if status == "completed" else "🔄"
        date = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S").strftime("%d/%m %H:%M")
        orders_text += f"{status_emoji} #{order_id} - User {user_id}\n"
        orders_text += f"💰 €{total:.2f} - {date}\n\n"
    
    await update.message.reply_text(orders_text)

# =====================================================
# ❓ COMANDO /help
# =====================================================
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ADMIN_ID:
        help_text = (
            "🔧 COMANDI ADMIN SELLER BOT\n\n"
            "• /start - Menu principale\n"
            "• /orders - Gestione ordini\n"
            "• /help - Questa guida\n\n"
            "Il bot riceve automaticamente gli ordini dalla mini-app\n"
            "e genera bollettini dettagliati."
        )
    else:
        help_text = (
            "🛍️ GUIDA SHOPPING\n\n"
            "• /start - Apri il negozio\n"
            "• /orders - I tuoi ordini\n"
            "• /help - Questa guida\n\n"
            "1. Clicca 'Apri Negozio' per fare shopping\n"
            "2. Aggiungi prodotti al carrello\n"
            "3. Completa l'ordine nella mini-app\n"
            "4. Ricevi il bollettino qui"
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
        new_status = "confirmed"
        status_text = "✅ CONFERMATO"
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
                    f"Tempo stimato: 30-45 minuti."
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
        status_emoji = "⏳" if status == "pending" else "✅" if status == "completed" else "🔄"
        date = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S").strftime("%d/%m %H:%M")
        orders_text += f"{status_emoji} Ordine #{order_id}\n"
        orders_text += f"💰 €{total:.2f} - {date}\n"
        orders_text += f"📦 {status.title()}\n\n"
    
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
        application.add_handler(CommandHandler("help", help_command))
        
        # Handler callback query
        application.add_handler(CallbackQueryHandler(handle_callback_query))
        
        # Handler admin
        application.add_handler(CommandHandler("admin_orders", admin_orders))
        
        # Handler dati da mini-app CON SUPER LOGGING
        async def webapp_data_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
            logger.info("🔥🔥🔥 RICEVUTO QUALCOSA DA WEBAPP! 🔥🔥🔥")
            logger.info(f"Update completo: {update}")
            logger.info(f"Message: {update.message}")
            logger.info(f"Effective message: {update.effective_message}")
            await handle_webapp_data(update, context)
        
        application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, webapp_data_handler))
        
        # Handler SUPER SEMPLICE per TUTTI i messaggi
        async def debug_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
            logger.info(f"�🔥🔥 MESSAGGIO RICEVUTO DA {update.effective_user.id if update.effective_user else 'UNKNOWN'}")
            logger.info(f"📝 Tipo messaggio: {type(update.message) if update.message else 'NO MESSAGE'}")
            
            # Se è un messaggio con web_app_data
            if update.message and hasattr(update.message, 'web_app_data') and update.message.web_app_data:
                logger.info(f"🌐 WEB APP DATA RICEVUTO: {update.message.web_app_data.data}")
                
                # Elabora ordine in modo super semplice
                try:
                    data = json.loads(update.message.web_app_data.data)
                    user = update.effective_user
                    
                    # Salva ordine nel database
                    conn = sqlite3.connect(DATABASE)
                    c = conn.cursor()
                    c.execute('''INSERT INTO orders (telegram_id, username, order_data, total_amount)
                                 VALUES (?, ?, ?, ?)''',
                              (user.id, user.username or 'unknown', json.dumps(data), data.get('totale', 0)))
                    order_id = c.lastrowid
                    conn.commit()
                    conn.close()
                    
                    # Invia bollettino al cliente
                    await update.message.reply_text(
                        f"✅ ORDINE #{order_id} CONFERMATO!\n\n"
                        f"💰 Totale: €{data.get('totale', 0):.2f}\n"
                        f"📦 Prodotti: {len(data.get('carrello', []))}\n\n"
                        f"Grazie per il tuo ordine!"
                    )
                    
                    # Notifica admin
                    await context.bot.send_message(
                        chat_id=ADMIN_ID,
                        text=f"🔔 NUOVO ORDINE #{order_id}\n\n"
                             f"👤 Cliente: {user.first_name or ''} {user.last_name or ''}\n"
                             f"📱 Username: @{user.username or 'N/A'}\n"
                             f"🆔 ID: {user.id}\n"
                             f"💰 Totale: €{data.get('totale', 0):.2f}\n"
                             f"📦 Prodotti: {len(data.get('carrello', []))}"
                    )
                    
                    logger.info(f"✅ Ordine {order_id} processato con successo!")
                    
                except Exception as e:
                    logger.error(f"❌ Errore elaborazione ordine: {e}")
                    await update.message.reply_text("❌ Errore nell'elaborazione dell'ordine")
        
        application.add_handler(MessageHandler(filters.ALL, debug_all_messages))
        
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

# =====================================================
# � MAIN - AVVIO BOT
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
        application.add_handler(CommandHandler("help", help_command))
        
        # Handler callback query
        application.add_handler(CallbackQueryHandler(handle_callback_query))
        
        # Handler admin
        application.add_handler(CommandHandler("admin_orders", admin_orders))
        
        # Handler dati da mini-app CON SUPER LOGGING
        async def webapp_data_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
            logger.info("🔥🔥🔥 RICEVUTO QUALCOSA DA WEBAPP! 🔥🔥🔥")
            logger.info(f"Update completo: {update}")
            logger.info(f"Message: {update.message}")
            logger.info(f"Effective message: {update.effective_message}")
            await handle_webapp_data(update, context)
        
        application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, webapp_data_handler))
        
        # Handler SUPER SEMPLICE per TUTTI i messaggi
        async def debug_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
            logger.info(f"�🔥🔥 MESSAGGIO RICEVUTO DA {update.effective_user.id if update.effective_user else 'UNKNOWN'}")
            logger.info(f"📝 Tipo messaggio: {type(update.message) if update.message else 'NO MESSAGE'}")
            
            # Se è un messaggio con web_app_data
            if update.message and hasattr(update.message, 'web_app_data') and update.message.web_app_data:
                logger.info(f"🌐 WEB APP DATA RICEVUTO: {update.message.web_app_data.data}")
                
                # Elabora ordine in modo super semplice
                try:
                    data = json.loads(update.message.web_app_data.data)
                    user = update.effective_user
                    
                    # Salva ordine nel database
                    conn = sqlite3.connect(DATABASE)
                    c = conn.cursor()
                    c.execute('''INSERT INTO orders (telegram_id, username, order_data, total_amount)
                                 VALUES (?, ?, ?, ?)''',
                              (user.id, user.username or 'unknown', json.dumps(data), data.get('totale', 0)))
                    order_id = c.lastrowid
                    conn.commit()
                    conn.close()
                    
                    # Invia bollettino al cliente
                    await update.message.reply_text(
                        f"✅ ORDINE #{order_id} CONFERMATO!\n\n"
                        f"💰 Totale: €{data.get('totale', 0):.2f}\n"
                        f"📦 Prodotti: {len(data.get('carrello', []))}\n\n"
                        f"Grazie per il tuo ordine!"
                    )
                    
                    # Notifica admin
                    await context.bot.send_message(
                        chat_id=ADMIN_ID,
                        text=f"🔔 NUOVO ORDINE #{order_id}\n\n"
                             f"👤 Cliente: {user.first_name or ''} {user.last_name or ''}\n"
                             f"📱 Username: @{user.username or 'N/A'}\n"
                             f"🆔 ID: {user.id}\n"
                             f"💰 Totale: €{data.get('totale', 0):.2f}\n"
                             f"📦 Prodotti: {len(data.get('carrello', []))}"
                    )
                    
                    logger.info(f"✅ Ordine {order_id} processato con successo!")
                    
                except Exception as e:
                    logger.error(f"❌ Errore elaborazione ordine: {e}")
                    await update.message.reply_text("❌ Errore nell'elaborazione dell'ordine")
        
        application.add_handler(MessageHandler(filters.ALL, debug_all_messages))
        
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
