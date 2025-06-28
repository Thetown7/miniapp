// ==================================================================================
// 📱 TELEGRAM INTEGRATIONS
// ==================================================================================

// ==================== 📱 INIZIALIZZAZIONE TELEGRAM ====================
let tg = window.Telegram.WebApp;
tg.expand(); // Espande l'app a schermo intero

// ==================== 🔄 GESTIONE TELEGRAM AVANZATA ====================
const TelegramIntegration = {
    // Applica tema Telegram
    applicaTema() {
        try {
            if (tg.colorScheme && tg.themeParams) {
                const themeParams = tg.themeParams;
                if (themeParams.bg_color) {
                    document.documentElement.style.setProperty('--tg-bg-color', themeParams.bg_color);
                }
                if (themeParams.text_color) {
                    document.documentElement.style.setProperty('--tg-text-color', themeParams.text_color);
                }
            }
        } catch (e) {
            console.warn('Impossibile applicare tema Telegram:', e);
        }
    },
    
    // Gestisci viewport changes
    gestisciViewport() {
        try {
            if (tg.onEvent) {
                tg.onEvent('viewportChanged', () => {
                    const viewport = tg.viewportHeight;
                    if (viewport) {
                        document.body.style.minHeight = `${viewport}px`;
                    }
                });
            }
        } catch (e) {
            console.warn('Impossibile gestire viewport:', e);
        }
    },
    
    // Invia dati a Telegram con gestione errori
    inviaData(dati) {
        try {
            if (tg.sendData) {
                tg.sendData(JSON.stringify(dati));
                return true;
            }
        } catch (error) {
            Utils.handleError(error, 'invio dati a Telegram');
            return false;
        }
        return false;
    }
};

// ==================== 📱 MAIN BUTTON TELEGRAM ====================
function setupMainButton() {
    try {
        if (!tg.MainButton) return;
        
        if (AppState.carrello.length > 0) {
            tg.MainButton.setText(`Ordina (€${AppState.totaleCarrello})`);
            tg.MainButton.show();
            
            // Rimuovi listener precedenti e aggiungi nuovo
            tg.MainButton.offClick(processaOrdineFinale);
            tg.MainButton.onClick(processaOrdineFinale);
        } else {
            tg.MainButton.hide();
        }
    } catch (e) {
        console.warn('Impossibile configurare MainButton:', e);
    }
}

// ==================== 📤 INVIO STATO A TELEGRAM ====================
function inviaStatoATelegram() {
    const dati = {
        azione: 'aggiornamento_stato',
        carrello: AppState.carrello,
        totale: AppState.totaleCarrello,
        timestamp: Date.now()
    };
    
    TelegramIntegration.inviaData(dati);
}

// ==================== 🏁 PROCESSO ORDINE FINALE ====================
function processaOrdineFinale() {
    try {
        const datiOrdine = {
            azione: 'ordine_finale',
            carrello: AppState.carrello,
            totale: AppState.totaleCarrello,
            timestamp: Date.now(),
            user_id: tg.initDataUnsafe?.user?.id || 'unknown'
        };
        
        if (TelegramIntegration.inviaData(datiOrdine)) {
            // Ordine inviato con successo
            if (tg.showAlert) {
                tg.showAlert('Ordine inviato con successo!');
            }
            AppState.svuotaCarrello();
        }
    } catch (e) {
        Utils.handleError(e, 'processo ordine finale');
    }
}