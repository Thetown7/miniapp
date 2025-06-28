// ==================================================================================
// 🗃️ STATE MANAGEMENT CENTRALIZZATO
// ==================================================================================

const AppState = {
    carrello: [],
    totaleCarrello: 0,
    strainSelezionata: null,
    categoriaEspansa: null,
    
    // Metodi per gestire lo stato
    aggiungiAlCarrello(prodotto) {
        this.carrello.push(prodotto);
        this.totaleCarrello += prodotto.prezzo;
        this.salvaStato();
        this.notificaCambiamento();
    },
    
    svuotaCarrello() {
        this.carrello = [];
        this.totaleCarrello = 0;
        this.salvaStato();
        this.notificaCambiamento();
    },
    
    rimuoviDalCarrello(index) {
        if (index >= 0 && index < this.carrello.length) {
            this.totaleCarrello -= this.carrello[index].prezzo;
            this.carrello.splice(index, 1);
            this.salvaStato();
            this.notificaCambiamento();
        }
    },
    
    salvaStato() {
        try {
            if (typeof Storage !== "undefined") {
                sessionStorage.setItem('telegramAppState', JSON.stringify({
                    carrello: this.carrello,
                    totaleCarrello: this.totaleCarrello,
                    strainSelezionata: this.strainSelezionata,
                    timestamp: Date.now()
                }));
            }
        } catch (e) {
            console.warn('Impossibile salvare stato:', e);
        }
    },
    
    caricaStato() {
        try {
            if (typeof Storage !== "undefined") {
                const saved = sessionStorage.getItem('telegramAppState');
                if (saved) {
                    const state = JSON.parse(saved);
                    // Verifica che i dati non siano troppo vecchi (1 ora)
                    if (Date.now() - state.timestamp < 3600000) {
                        this.carrello = state.carrello || [];
                        this.totaleCarrello = state.totaleCarrello || 0;
                        this.strainSelezionata = state.strainSelezionata;
                        this.notificaCambiamento();
                    }
                }
            }
        } catch (e) {
            console.warn('Impossibile caricare stato salvato:', e);
        }
    },
    
    notificaCambiamento() {
        aggiornaCarrello();
        setupMainButton();
        inviaStatoATelegram();
    }
};