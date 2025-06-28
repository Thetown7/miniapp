// ==================================================================================
// 🛒 FUNZIONI CARRELLO
// ==================================================================================

// ==================== 🛒 AGGIUNGI AL CARRELLO ====================
function ordinaProdotto(nome, prezzo) {
    try {
        const prodotto = { 
            nome: Utils.sanitizeHTML(nome), 
            prezzo: typeof prezzo === 'number' ? prezzo : parseFloat(prezzo) || 0,
            timestamp: Date.now()
        };
        
        AppState.aggiungiAlCarrello(prodotto);
        mostraConferma(prodotto.nome, prodotto.prezzo);
        
        // Invia dati a Telegram
        TelegramIntegration.inviaData({
            azione: 'ordine',
            prodotto: prodotto.nome,
            prezzo: prodotto.prezzo,
            carrello: AppState.carrello,
            totale: AppState.totaleCarrello,
            timestamp: Date.now()
        });
    } catch (e) {
        Utils.handleError(e, 'aggiunta al carrello');
    }
}

// ==================== 🔄 AGGIORNA CARRELLO UI ====================
function aggiornaCarrello() {
    try {
        const cartInfo = document.getElementById('cartInfo');
        if (!cartInfo) return;
        
        if (AppState.carrello.length > 0) {
            cartInfo.style.display = 'block';
            cartInfo.innerHTML = `Carrello: <span id="cartCount">${AppState.carrello.length}</span> prodotti - €${AppState.totaleCarrello}`;
        } else {
            cartInfo.style.display = 'none';
        }
    } catch (e) {
        Utils.handleError(e, 'aggiornamento carrello UI');
    }
}

// ==================== ✅ MOSTRA CONFERMA ====================
function mostraConferma(nomeProdotto, prezzo) {
    try {
        const notifica = document.createElement('div');
        notifica.style.cssText = `
            position: fixed; top: 20px; left: 50%; transform: translateX(-50%);
            background: linear-gradient(135deg, #48bb78 0%, #46d1a1 100%);
            color: white; padding: 15px 25px; border-radius: 25px;
            font-weight: bold; z-index: 3000;
            box-shadow: 0 5px 20px rgba(0,0,0,0.3); 
            display: flex; flex-direction: column; align-items: center;
            animation: slideIn 0.3s ease;
        `;
        
        notifica.innerHTML = `
            <div style="margin-bottom: 10px;">✅ Aggiunto al carrello!</div>
            <div style="font-size: 18px;">${Utils.sanitizeHTML(nomeProdotto)}</div>
            <div style="font-size: 20px; margin-top: 5px;">€${Utils.formatPrice(prezzo)}</div>
        `;
        
        document.body.appendChild(notifica);
        
        // Rimuovi dopo 3 secondi
        setTimeout(() => {
            notifica.style.animation = 'slideOut 0.3s ease forwards';
            setTimeout(() => {
                if (notifica.parentNode) {
                    notifica.remove();
                }
            }, 300);
        }, 3000);
    } catch (e) {
        Utils.handleError(e, 'mostra conferma');
    }
}

// ==================== ✅ MOSTRA CONFERMA QUANTITÀ ====================
function mostraConfermaQuantita(prodottoCompleto, prezzo) {
    try {
        const notifica = document.createElement('div');
        notifica.style.cssText = `
            position: fixed; top: 20px; left: 50%; transform: translateX(-50%);
            background: linear-gradient(135deg, #764ba2 0%, #48bb78 100%);
            color: white; padding: 15px 25px; border-radius: 25px;
            font-weight: bold; z-index: 3000;
            box-shadow: 0 5px 20px rgba(0,0,0,0.3); 
            display: flex; flex-direction: column; align-items: center;
            animation: slideIn 0.3s ease;
        `;
        
        notifica.innerHTML = `
            <div style="margin-bottom: 10px;">Aggiungere al carrello?</div>
            <div style="font-size: 18px;">${Utils.sanitizeHTML(prodottoCompleto)}</div>
            <div style="font-size: 20px; margin: 10px 0;">€${Utils.formatPrice(prezzo)}</div>
            <div style="display: flex; gap: 15px; margin-top: 10px;">
                <button id="confirmAddBtn" 
                        style="background: white; color: #48bb78; border: none; 
                               padding: 8px 20px; border-radius: 20px; font-weight: bold;
                               cursor: pointer;">Sì</button>
                <button id="cancelAddBtn" 
                        style="background: rgba(255,255,255,0.3); color: white; border: none; 
                               padding: 8px 20px; border-radius: 20px; font-weight: bold;
                               cursor: pointer;">No</button>
            </div>
        `;
        
        document.body.appendChild(notifica);
        
        // Gestisci conferma
        document.getElementById('confirmAddBtn').addEventListener('click', () => {
            ordinaProdotto(prodottoCompleto, prezzo);
            notifica.style.animation = 'slideOut 0.3s ease forwards';
            setTimeout(() => {
                if (notifica.parentNode) {
                    notifica.remove();
                }
            }, 300);
        });
        
        // Gestisci annullamento
        document.getElementById('cancelAddBtn').addEventListener('click', () => {
            notifica.style.animation = 'slideOut 0.3s ease forwards';
            setTimeout(() => {
                if (notifica.parentNode) {
                    notifica.remove();
                }
            }, 300);
        });
        
        // Rimuovi automaticamente dopo 5 secondi
        setTimeout(() => {
            try {
                if (notifica.parentNode) {
                    notifica.style.animation = 'slideOut 0.3s ease forwards';
                    setTimeout(() => notifica.remove(), 300);
                }
            } catch (err) {
                console.warn('Errore rimozione notifica:', err);
            }
        }, 5000);
    } catch (e) {
        Utils.handleError(e, 'mostra conferma quantità');
    }
}