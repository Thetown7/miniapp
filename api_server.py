# api_server.py
# Server Flask per fornire API alla mini-app Telegram

from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import hmac
import hashlib
import json
from urllib.parse import unquote

app = Flask(__name__)
CORS(app)  # Abilita CORS per permettere richieste dalla mini-app

DATABASE = 'users.db'
BOT_TOKEN = '7897131694:AAFDIUob9YoBJFGEWFHSP_HqeuOHQbfJONQ'

def verify_telegram_data(init_data):
    """Verifica l'autenticità dei dati Telegram"""
    try:
        # Parse init data
        parsed_data = {}
        for param in init_data.split('&'):
            key, value = param.split('=')
            parsed_data[key] = unquote(value)
        
        # Estrai hash
        received_hash = parsed_data.pop('hash', None)
        if not received_hash:
            return False
        
        # Prepara la stringa per la verifica
        data_check_string = '\n'.join([f"{k}={v}" for k, v in sorted(parsed_data.items())])
        
        # Calcola hash
        secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        
        return calculated_hash == received_hash
    except Exception as e:
        print(f"Errore verifica: {e}")
        return False

@app.route('/api/check-user', methods=['POST'])
def check_user():
    """Verifica se un utente è autorizzato"""
    try:
        data = request.get_json()
        init_data = data.get('initData', '')
        
        # Verifica autenticità
        if not verify_telegram_data(init_data):
            return jsonify({'authorized': False, 'error': 'Invalid data'}), 401
        
        # Estrai user data
        parsed = {}
        for param in init_data.split('&'):
            key, value = param.split('=')
            parsed[key] = unquote(value)
        
        user_data = json.loads(parsed.get('user', '{}'))
        telegram_id = user_data.get('id')
        
        if not telegram_id:
            return jsonify({'authorized': False, 'error': 'No user ID'}), 400
        
        # Controlla nel database
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute('SELECT is_verified FROM users WHERE telegram_id = ?', (telegram_id,))
        result = c.fetchone()
        conn.close()
        
        if result and result[0] == 1:
            return jsonify({'authorized': True, 'user': user_data})
        else:
            return jsonify({'authorized': False, 'message': 'User not verified'})
            
    except Exception as e:
        print(f"Errore: {e}")
        return jsonify({'authorized': False, 'error': str(e)}), 500

@app.route('/api/users', methods=['GET'])
def get_users():
    """Ottieni lista utenti (solo per debug)"""
    try:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute('SELECT telegram_id, username, is_verified FROM users')
        users = c.fetchall()
        conn.close()
        
        return jsonify({
            'users': [
                {
                    'telegram_id': u[0],
                    'username': u[1],
                    'is_verified': bool(u[2])
                } for u in users
            ]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    app.run(debug=True, port=5000)