// ==================================================================================
// 🚀 TELEGRAM MINI APP - SISTEMA ORDINI CON STRAIN E QUANTITÀ - VERSIONE MIGLIORATA
// ==================================================================================

// ==================== 📱 INIZIALIZZAZIONE TELEGRAM ====================
let tg = window.Telegram.WebApp;
tg.expand(); // Espande l'app a schermo intero

// ==================== 🗃️ STATE MANAGEMENT CENTRALIZZATO ====================
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

// ==================== 🔧 UTILITÀ E HELPERS ====================
const Utils = {
    // Debounce per eventi frequenti
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },
    
    // Sanitizza stringhe per prevenire XSS
    sanitizeHTML(str) {
        const temp = document.createElement('div');
        temp.textContent = str;
        return temp.innerHTML;
    },
    
    // Formatta prezzo
    formatPrice(price) {
        return typeof price === 'number' ? price.toFixed(0) : '0';
    },
    
    // Validazione prodotto
    validateProduct(prodotto) {
        return prodotto && 
               prodotto.nome && 
               prodotto.prezzi && 
               prodotto.strains && 
               Array.isArray(prodotto.strains) &&
               typeof prodotto.prezzi === 'object';
    },
    
    // Gestione errori
    handleError(error, context = '') {
        console.error(`Errore ${context}:`, error);
        if (tg.showAlert) {
            tg.showAlert(`Si è verificato un errore. Riprova.`);
        }
    }
};

// ==================== 📦 DATI PRODOTTI CON PREZZI QUANTITÀ ====================
const catalogoProdotti = {
    'frozen1': [
        { 
            nome: 'Gelato 41', 
            descrizione: 'Premium Indoor',
            strains: ['Indica Dominant', 'Hybrid 50/50', 'Sativa Leaning'],
            prezzi: {
                '2g': 25,
                '5g': 55, 
                '10g': 100
            },
            media: {
                type: 'image',
                url: 'https://i.ibb.co/bgZND9tz/Screenshot-2023-10-25-alle-22-01-20.png'
            }
        },
        { 
            nome: 'Zkittlez', 
            descrizione: 'Sweet & Fruity',
            strains: ['Indica Pure', 'Hybrid Sweet'],
            prezzi: {
                '2g': 22,
                '5g': 50, 
                '10g': 90
            },
            media: {
                type: 'image',
                url: 'https://via.placeholder.com/400x250/764ba2/white?text=Zkittlez'
            }
        },
        { 
            nome: 'Purple Haze', 
            descrizione: 'Classic Strain',
            strains: ['Sativa Classic', 'Hybrid Purple'],
            prezzi: {
                '2g': 30,
                '5g': 65, 
                '10g': 120
            },
            media: {
                type: 'video',
                url: 'https://www.w3schools.com/html/mov_bbb.mp4'
            }
        }
    ],
    'frozen2': [
        { 
            nome: 'OG Kush', 
            descrizione: 'West Coast Classic',
            strains: ['Indica OG', 'Hybrid Classic'],
            prezzi: {
                '2g': 20,
                '5g': 45, 
                '10g': 80
            },
            media: {
                type: 'image',
                url: 'https://via.placeholder.com/400x250/ea66d2/white?text=OG+Kush'
            }
        },
        { 
            nome: 'White Widow', 
            descrizione: 'Amsterdam Special',
            strains: ['Hybrid Balanced', 'Sativa White'],
            prezzi: {
                '2g': 24,
                '5g': 52, 
                '10g': 95
            },
            media: {
                type: 'image',
                url: 'https://via.placeholder.com/400x250/48bb78/white?text=White+Widow'
            }
        }
    ],
    'salad': [
        { 
            nome: 'Amnesia Haze', 
            descrizione: 'Sativa Power',
            strains: ['Sativa Power', 'Hybrid Energetic'],
            prezzi: {
                '2g': 18,
                '5g': 40, 
                '10g': 75
            },
            media: {
                type: 'image',
                url: 'https://via.placeholder.com/400x250/ff6b6b/white?text=Amnesia+Haze'
            }
        },
        { 
            nome: 'Lemon Haze', 
            descrizione: 'Citrus Flavor',
            strains: ['Sativa Citrus', 'Hybrid Lemon'],
            prezzi: {
                '2g': 16,
                '5g': 35, 
                '10g': 65
            },
            media: {
                type: 'image',
                url: 'https://via.placeholder.com/400x250/ffa502/white?text=Lemon+Haze'
            }
        },
        { 
            nome: 'Jack Herer', 
            descrizione: 'The Legend',
            strains: ['Sativa Legend', 'Hybrid Classic', 'Indica Relax'],
            prezzi: {
                '2g': 26,
                '5g': 58, 
                '10g': 105
            },
            media: {
                type: 'image',
                url: 'https://via.placeholder.com/400x250/3742fa/white?text=Jack+Herer'
            }
        }
    ]
};

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

// ==================================================================================
// 📋 TUTTE LE DICHIARAZIONI FUNZIONI
// ==================================================================================

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

// ==================== ⌨️ SETUP KEYBOARD NAVIGATION ====================
function setupKeyboardNavigation() {
    document.addEventListener('keydown', (e) => {
        try {
            switch(e.key) {
                case 'Escape':
                    chiudiCategorieEspanse();
                    chiudiModali();
                    break;
                case 'Enter':
                    if (e.target.classList.contains('product')) {
                        e.target.click();
                    }
                    break;
            }
        } catch (err) {
            console.warn('Errore keyboard navigation:', err);
        }
    });
}

// ==================== 🔄 CHIUDI CATEGORIE ESPANSE ====================
function chiudiCategorieEspanse() {
    try {
        document.querySelectorAll('.product.expanded').forEach(p => {
            // Ripristina elementi originali
            const elementiOriginali = p.querySelectorAll('.product-description, .frozen-badge, .product-name');
            elementiOriginali.forEach(elemento => {
                elemento.style.display = '';
                setTimeout(() => elemento.style.opacity = '1', 10);
            });
            
            // Rimuovi container prodotti
            const container = p.querySelector('.real-products-injected');
            if (container) {
                container.style.animation = 'fadeOut 0.3s ease';
                setTimeout(() => {
                    try {
                        if (container.parentNode) {
                            container.remove();
                        }
                        const closeBtn = p.querySelector('button[style*="position: absolute"]');
                        if (closeBtn && closeBtn.parentNode) {
                            closeBtn.remove();
                        }
                        p.classList.remove('expanded');
                        p.style.gridColumn = '';
                        p.style.minHeight = '';
                        p.style.padding = '';
                        AppState.categoriaEspansa = null;
                    } catch (err) {
                        console.warn('Errore pulizia DOM:', err);
                    }
                }, 300);
            }
        });
    } catch (e) {
        Utils.handleError(e, 'chiusura categorie espanse');
    }
}

// ==================== 🔐 CHIUDI MODALI ====================
function chiudiModali() {
    try {
        document.querySelectorAll('[style*="position: fixed"][style*="z-index"]').forEach(modal => {
            if (modal.parentNode) {
                modal.remove();
            }
        });
    } catch (e) {
        console.warn('Errore chiusura modali:', e);
    }
}

// ==================== 📦 ESPANDI CATEGORIA PRODOTTI ====================
function espandiProdotto(productElement, categoria) {
    try {
        // Validazione
        if (!Utils.validateProduct || !catalogoProdotti[categoria]) {
            console.warn('Dati categoria non validi');
            return;
        }
        
        // Setup espansione
        productElement.classList.add('expanded');
        productElement.style.gridColumn = '1 / -1';
        productElement.style.transition = 'all 0.5s ease';
        productElement.style.minHeight = '400px';
        productElement.style.padding = '20px';
        
        AppState.categoriaEspansa = categoria;
        
        // Nascondi elementi originali della categoria
        const elementiOriginali = productElement.querySelectorAll('.product-description, .frozen-badge, .product-name');
        elementiOriginali.forEach(elemento => {
            elemento.style.transition = 'opacity 0.3s ease';
            elemento.style.opacity = '0';
            setTimeout(() => elemento.style.display = 'none', 300);
        });
        
        // Crea container per card prodotti
        const container = creaContainerProdotti();
        
        // Crea bottone chiudi
        const closeBtn = creaBottoneChiudi(productElement, container);
        
        // Genera card prodotti
        generaCardProdotti(container, categoria);
        
        // Aggiungi al DOM
        productElement.appendChild(container);
        productElement.appendChild(closeBtn);
        
    } catch (e) {
        Utils.handleError(e, 'espansione prodotto');
    }
}

// ==================== 🎨 CREA CONTAINER PRODOTTI ====================
function creaContainerProdotti() {
    const container = document.createElement('div');
    container.className = 'real-products-injected';
    container.style.cssText = `
        margin-top: 20px;
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
        gap: 15px;
        animation: fadeIn 0.5s ease;
    `;
    return container;
}

// ==================== ❌ CREA BOTTONE CHIUDI ====================
function creaBottoneChiudi(productElement, container) {
    const closeBtn = document.createElement('button');
    closeBtn.innerHTML = '×';
    closeBtn.style.cssText = `
        position: absolute; top: 10px; right: 10px;
        background: rgba(255, 255, 255, 0.9); border: 2px solid #764ba2;
        width: 35px; height: 35px; border-radius: 50%;
        font-size: 24px; cursor: pointer; z-index: 10;
        color: #764ba2; font-weight: bold; transition: all 0.3s ease;
    `;
    
    closeBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        chiudiCategorieEspanse();
    });
    
    return closeBtn;
}

// ==================== 🏷️ GENERA CARD PRODOTTI ====================
function generaCardProdotti(container, categoria) {
    try {
        const prodotti = catalogoProdotti[categoria] || [];
        
        prodotti.forEach(prodotto => {
            if (Utils.validateProduct(prodotto)) {
                const card = creaCardProdotto(prodotto);
                container.appendChild(card);
            } else {
                console.warn('Prodotto non valido saltato:', prodotto);
            }
        });
    } catch (e) {
        Utils.handleError(e, 'generazione card prodotti');
    }
}


// ==================== 🎴 CREA SINGOLA CARD PRODOTTO ====================
function creaCardProdotto(prodotto) {
    const card = document.createElement('div');
    card.style.cssText = `
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        margin-top: 10px; border-radius: 20px; padding: 15px;
        color: white; text-align: center; cursor: pointer;
        transition: all 0.3s ease; border: 2px solid white;
        box-shadow: 0 5px 15px rgba(0,0,0,0.2); position: relative;
        overflow: hidden;
    `;
    
    // Aggiungi banner strain
    const strainBanner = document.createElement('div');
    strainBanner.style.cssText = `
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        background: rgba(0,0,0,0.3);
        padding: 3px 0;
        font-size: 11px;
        font-weight: bold;
        letter-spacing: 1px;
        text-transform: uppercase;
    `;
    strainBanner.textContent = 'Premium';
    
    // Sanitizza dati per sicurezza
    const nomeSecure = Utils.sanitizeHTML(prodotto.nome);
    const descrizioneSecure = Utils.sanitizeHTML(prodotto.descrizione);
    
    // HTML della card (SOLO VISUALIZZAZIONE)
    card.innerHTML = `
        <div style="font-weight: bold; font-size: 16px; margin-bottom: 8px; margin-top: 15px;">${nomeSecure}</div>
        <div style="font-size: 13px; margin-bottom: 12px; opacity: 0.9;">${descrizioneSecure}</div>
        
        <!-- PREZZI PER QUANTITÀ - ANIMATI -->
        <div style="display: flex; justify-content: space-between; gap: 8px; margin-left: 10px; margin-bottom: 15px;">
            <div class="style" data-quantity="2g" </div>
           
                <div>2g</div>
                <div style="font-weight: bold;padding: 8px 0; margin-left: -10px; ">€${Utils.formatPrice(prodotto.prezzi['2g'])}</div>
            </div>
            
            <div class="style" data-quantity="5g" </div>
                <div>5g</div>
                <div style="font-weight: bold;padding: 8px 0; ">€${Utils.formatPrice(prodotto.prezzi['5g'])}</div>
               
            </div>
            
            <div class="style" data-quantity="10g" </div>
                <div>10g</div>
                <div style="font-weight: bold; padding: 8px 0; ">€${Utils.formatPrice(prodotto.prezzi['10g'])}</div>
                
            </div>
        </div>
        
        <!-- INDICATORE CLICK PER DETTAGLI -->
        <div style="background: rgba(255,255,255,0.2); padding: 8px 16px; border-radius: 15px; 
                    font-size: 12px; font-weight: bold; border: 1px solid rgba(255,255,255,0.3);">
            👆 Click per Dettagli
        </div>
    `;
    
    // Aggiungi banner strain
    card.prepend(strainBanner);
    
    // Setup eventi card (SOLO CLICK PER DETTAGLIO)
    setupEventiCardSemplificata(card, prodotto);
    
    // Animazioni bottoni prezzi (solo hover)
    const priceBtns = card.querySelectorAll('.price-btn');
    priceBtns.forEach(btn => {
        btn.addEventListener('mouseenter', () => {
            btn.style.background = 'rgba(255,255,255,0.3)';
            btn.style.transform = 'translateY(-3px)';
            btn.style.boxShadow = '0 5px 15px rgba(0,0,0,0.3)';
        });
        
        btn.addEventListener('mouseleave', () => {
            btn.style.background = 'rgba(255,255,255,0.15)';
            btn.style.transform = 'translateY(0)';
            btn.style.boxShadow = 'none';
        });
    });
    
    return card;
}

// ==================== 🎭 SETUP EVENTI CARD SEMPLIFICATA ====================
function setupEventiCardSemplificata(card, prodotto) {
    try {
        // Click su card per aprire dettaglio con debounce
        const debouncedClick = Utils.debounce(() => {
            creaFinestraDettaglio(prodotto.nome, prodotto.prezzi, prodotto.descrizione, prodotto.strains, prodotto.media);
        }, 300);
        
        card.addEventListener('click', debouncedClick);
        
        // Effetti hover
        card.addEventListener('mouseenter', () => {
            card.style.transform = 'scale(1.05)';
            card.style.boxShadow = '0 8px 20px rgba(0,0,0,0.3)';
        });
        card.addEventListener('mouseleave', () => {
            card.style.transform = 'scale(1)';
            card.style.boxShadow = '0 5px 15px rgba(0,0,0,0.2)';
        });
    } catch (e) {
        Utils.handleError(e, 'setup eventi card');
    }
}

// ==================== 🏗️ CREA FINESTRA DETTAGLIO ====================
function creaFinestraDettaglio(nomeProdotto, prezzi, descrizione, strains, media) {
    try {
        AppState.strainSelezionata = null; // Reset strain selezionata
        
        // Validazione input
        if (!nomeProdotto || !prezzi || !strains) {
            console.warn('Dati prodotto incompleti');
            return;
        }
        
        // Crea overlay
        const overlay = creaOverlayDettaglio();
        
        // Crea finestra
        const finestra = creaFinestraModal();
        
        // Popola contenuto finestra
        popolaFinestraDettaglio(finestra, nomeProdotto, prezzi, descrizione, strains);
        
        // Mostra media se disponibile
        if (media && media.url) {
            setTimeout(() => mostraMediaProdotto(nomeProdotto.replace(/\s+/g, ''), media), 100);
        }
        
        // Setup chiusura overlay
        overlay.addEventListener('click', function(e) {
            if (e.target === overlay) {
                overlay.remove();
                AppState.strainSelezionata = null;
            }
        });
        
        // Aggiungi al DOM
        overlay.appendChild(finestra);
        document.body.appendChild(overlay);
        
    } catch (e) {
        Utils.handleError(e, 'creazione finestra dettaglio');
    }
}

// ==================== 🌐 CREA OVERLAY DETTAGLIO ====================
function creaOverlayDettaglio() {
    const overlay = document.createElement('div');
    overlay.style.cssText = `
        position: fixed; top: 0; left: 0; right: 0; bottom: 0;
        background: rgba(0, 0, 0, 0.8); display: flex;
        justify-content: center; align-items: center; z-index: 2000;
    `;
    return overlay;
}

// ==================== 🏠 CREA FINESTRA MODAL ====================
function creaFinestraModal() {
    const finestra = document.createElement('div');
    finestra.style.cssText = `
        width: 450px; height: 600px; background: white;
        border-radius: 40px; border: 3px solid #ffff;
        position: relative; overflow-y: auto; overflow-x: hidden;
        scroll-behavior: smooth; scrollbar-width: none; -ms-overflow-style: none;
        box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5);
    `;
    return finestra;
}

// ==================== 💰 GENERA TABELLA PREZZI CLICCABILI ====================
function generaTabellaPrecci(prezzi) {
    try {
        const prezzoBase = prezzi['2g'] / 2;
        
        const quantita = ['2g', '5g', '10g'];
        const grammi = [2, 5, 10];
        const sconti = [0, 22, 17];
        
        // 🎯 CONTAINER ORIZZONTALE (FLEX)
        let tabella = '<div style="display: flex; gap: 8px; justify-content: space-between;">';
        
        quantita.forEach((q, index) => {
            const grammo = grammi[index];
            const sconto = sconti[index];
            
            const prezzoTeorico = prezzoBase * grammo;
            const prezzoFinale = Math.round(prezzoTeorico * (1 - sconto/100));
            const percentualeScontata = sconto > 0 ? `<br><small>(-${sconto}%)</small>` : '';
            const colorPrezzo = sconto > 0 ? '#48bb78' : '#667eea';
            
            // 🎯 OGNI PREZZO COME BOTTONE COMPATTO
            tabella += `
                <div onclick="selezionaQuantita('${q}', ${prezzoFinale})" 
                     style="flex: 1; text-align: center; padding: 1px 5px; 
                            border-radius: 15px; cursor: pointer; transition: all 0.2s ease;
                            border: 2px solid ${colorPrezzo}; background: white;
                            font-size: 20px; min-height: 50px; display: flex;
                            flex-direction: column; justify-content: center;"
                     onmouseover="this.style.background='${colorPrezzo}'; this.style.color='white'"
                     onmouseout="this.style.background='white'; this.style.color='black'">
                    
                    <div style="font-weight: bold; font-size: 15px;">${q}</div>
                    <div style="color: ${colorPrezzo}; font-weight: bold;">
                        €${Utils.formatPrice(prezzoFinale)}${percentualeScontata}
                    </div>
                </div>
            `;
        });
        
        tabella += '</div>';
        return tabella;
        
    } catch (e) {
        Utils.handleError(e, 'generazione tabella prezzi');
        return '<div>Errore caricamento prezzi</div>';
    }
}

// ==================== 📝 POPOLA FINESTRA DETTAGLIO ====================
function popolaFinestraDettaglio(finestra, nomeProdotto, prezzi, descrizione, strains) {
    try {
        // Sanitizza dati
        const nomeSecure = Utils.sanitizeHTML(nomeProdotto);
        const descrizioneSecure = Utils.sanitizeHTML(descrizione);
        
        // Crea dropdown opzioni strain con sanitizzazione
        const dropdownOptions = strains.map(strain => {
            const strainSecure = Utils.sanitizeHTML(strain);
            return `<div onclick="selectStrain('${strainSecure}', '${nomeSecure}')" 
                          style="padding: 12px 15px; cursor: pointer; border-bottom: 1px solid #eee;
                                 transition: background 0.2s ease; font-weight: 500;"
                          onmouseover="this.style.background='#f0f7ff'"
                          onmouseout="this.style.background='white'">
                        ${strainSecure}
                     </div>`;
        }).join('');
        
        // HTML finestra
        finestra.innerHTML = `
            <div style="background: linear-gradient(135deg, #764ba2 0%, #ea66d2 100%); margin-bottom: -30px; 
                        height: 300px; display: flex; align-items: center; justify-content: center;">
                <div style="background: white; width: 400px; height: 250px; border-radius: 20px;
                            position: relative; overflow: hidden;">
                    <div id="mediaPreview-${nomeProdotto.replace(/\s+/g, '')}" style="width: 100%; height: 100%; display: flex; 
                                                          align-items: center; justify-content: center; position: relative;">
                        <div style="font-size: 18px; color: #666;">📷 Immagine Prodotto</div>
                    </div>
                </div>
            </div>
            <div style="padding: 30px;">
            <!-- DROPDOWN STRAIN -->
                <div style="position: relative; display: inline-block; margin-bottom: 10px;">
                    <div id="strainButton" onclick="toggleStrainDropdown()" 
                         style="background: linear-gradient(135deg, #667eea, #764ba2); color: white; margin-left: 200px; margin-top: 10px;
                                padding: 7px 10px; border-radius: 15px; cursor: pointer;
                               font-size: 15px; font-weight: bold; display: flex; align-items: center;
                                gap: 8px; min-width: 200px; justify-content: space-between;">
                        <span>🧬 Scegli Strain</span>
                        <span id="dropdownArrow">▼</span>
                    </div>
                <h2 style="margin-top: -35px; font-size: 25px;">${nomeSecure}</h2>
                
                
                    <div id="strainDropdown" style="display: none; position: absolute; top: 100%; left: 0;
                                                   background: white; border: 2px solid #667eea; border-radius: 15px;
                                                   box-shadow: 0 8px 25px rgba(0,0,0,0.15); z-index: 100; 
                                                   min-width: 250px; margin-top: 5px; overflow: hidden;">
                        ${dropdownOptions}
                    </div>
                </div>
                
                <p style="color: #000; margin: 20px 0 30px 0; font-weight: bold; line-height: 1.5;">${descrizioneSecure}</p>
                
                <!-- TABELLA PREZZI CLICCABILI -->
               
                <div style="background: #f8f9fa; padding: 10px; border-radius: 10px; margin-bottom: 15px;">
                
                    
                ${generaTabellaPrecci(prezzi)}
            </div>
                      
                
                
                <button id="orderButton" onclick="processOrder('${nomeSecure}', '${JSON.stringify(prezzi).replace(/"/g, '&quot;')}')" 
                        style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                               color: white; border: none; padding: 15px; width: 100%;
                               border-radius: 30px; font-size: 20px; font-weight: bold;
                               opacity: 0.5; cursor: not-allowed; transition: all 0.3s ease;">
                    Seleziona Strain per Continuare
                </button>
            </div>
        `;
    } catch (e) {
        Utils.handleError(e, 'popolamento finestra dettaglio');
    }
}

// ==================== 🔄 TOGGLE DROPDOWN STRAIN ====================
function toggleStrainDropdown() {
    try {
        const dropdown = document.getElementById('strainDropdown');
        const arrow = document.getElementById('dropdownArrow');
        
        if (!dropdown || !arrow) return;
        
        if (dropdown.style.display === 'none' || dropdown.style.display === '') {
            dropdown.style.display = 'block';
            dropdown.style.animation = 'fadeIn 0.2s ease';
            arrow.style.transform = 'rotate(180deg)';
            arrow.style.transition = 'transform 0.2s ease';
        } else {
            dropdown.style.display = 'none';
            arrow.style.transform = 'rotate(0deg)';
        }
    } catch (e) {
        Utils.handleError(e, 'toggle dropdown strain');
    }
}

// ==================== ✅ SELEZIONA STRAIN ====================
function selectStrain(strain, nomeProdotto) {
    try {
        AppState.strainSelezionata = strain;
        
        // Aggiorna button dropdown
        const strainButton = document.getElementById('strainButton');
        if (strainButton) {
            strainButton.innerHTML = `
                <span>🧬 ${Utils.sanitizeHTML(strain)}</span>
                <span id="dropdownArrow" style="transform: rotate(0deg); transition: transform 0.2s ease;">▼</span>
            `;
            strainButton.onclick = () => toggleStrainDropdown();
        }
        
        // Chiudi dropdown
        const dropdown = document.getElementById('strainDropdown');
        if (dropdown) {
            dropdown.style.display = 'none';
        }
        
        // Abilita button ordine
        const orderButton = document.getElementById('orderButton');
        if (orderButton) {
            orderButton.style.opacity = '1';
            orderButton.style.cursor = 'pointer';
            orderButton.innerHTML = `SCEGLI QUANTITÀ`;
        }
        
        console.log(`Strain selezionata: ${strain} per ${nomeProdotto}`);
    } catch (e) {
        Utils.handleError(e, 'selezione strain');
    }
}

// ==================== 🎯 SELEZIONA QUANTITÀ CLICCABILE ====================
function selezionaQuantita(quantita, prezzo) {
    try {
        if (!AppState.strainSelezionata) {
            if (tg.showAlert) {
                tg.showAlert('Seleziona prima una strain!');
            }
            return;
        }
        
        // Trova nome prodotto dalla finestra
        const titleElement = document.querySelector('h2');
        if (!titleElement) return;
        
        const nomeProdotto = titleElement.textContent;
        const prodottoCompleto = `${nomeProdotto} (${AppState.strainSelezionata}) - ${quantita}`;
        
        // Mostra conferma prima di aggiungere al carrello
        mostraConfermaQuantita(prodottoCompleto, prezzo);
    } catch (e) {
        Utils.handleError(e, 'selezione quantità');
    }
}

// ==================== 🏁 PROCESSA ORDINE DA DETTAGLIO ====================
function processOrder(nomeProdotto, prezziString) {
    try {
        if (!AppState.strainSelezionata) {
            if (tg.showAlert) {
                tg.showAlert('Seleziona una strain prima di ordinare!');
            }
            return;
        }
        
        // Mostra selettore quantità
        mostraSelettoreQuantita(nomeProdotto, prezziString, AppState.strainSelezionata);
    } catch (e) {
        Utils.handleError(e, 'processo ordine');
    }
}

// ==================== 📊 MOSTRA SELETTORE QUANTITÀ ====================
function mostraSelettoreQuantita(nomeProdotto, prezziString, strain) {
    try {
        const prezzi = JSON.parse(prezziString.replace(/&quot;/g, '"'));
        
        // Sanitizza input
        const nomeSecure = Utils.sanitizeHTML(nomeProdotto);
        const strainSecure = Utils.sanitizeHTML(strain);
        
        // Crea overlay selettore
        const overlay = document.createElement('div');
        overlay.style.cssText = `
            position: fixed; top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0, 0, 0, 0.9); display: flex;
            justify-content: center; align-items: center; z-index: 3000;
        `;
        
        // Crea selettore
        const selector = document.createElement('div');
        selector.style.cssText = `
            background: black; padding: 30px; border-radius: 20px;
            text-align: center; max-width: 300px; width: 90%;
        `;
        
        selector.innerHTML = `
            <h3 style="margin: 0 0 20px 0;">${nomeSecure}</h3>
            <p style="margin: 0 0 20px 0; color: #667eea; font-weight: bold;">🧬 ${strainSecure}</p>
            <p style="margin: 0 0 20px 0;">Seleziona quantità:</p>
            
            <div style="display: flex; flex-direction: column; gap: 10px;">
                <button onclick="orderFromDetail('${nomeSecure}', '${strainSecure}', '2g', ${prezzi['2g']})" 
                        style="background: #48bb78; color: white; border: none; padding: 15px; 
                               border-radius: 15px; font-weight: bold; cursor: pointer;">
                    2g - €${Utils.formatPrice(prezzi['2g'])}
                </button>
                <button onclick="orderFromDetail('${nomeSecure}', '${strainSecure}', '5g', ${prezzi['5g']})" 
                        style="background: #48bb78; color: white; border: none; padding: 15px; 
                               border-radius: 15px; font-weight: bold; cursor: pointer;">
                    5g - €${Utils.formatPrice(prezzi['5g'])} (-8%)
                </button>
                <button onclick="orderFromDetail('${nomeSecure}', '${strainSecure}', '10g', ${prezzi['10g']})" 
                        style="background: #48bb78; color: white; border: none; padding: 15px; 
                               border-radius: 15px; font-weight: bold; cursor: pointer;">
                    10g - €${Utils.formatPrice(prezzi['10g'])} (-17%)
                </button>
            </div>
            
            <button onclick="this.closest('[style*=\"position: fixed\"]').remove()" 
                    style="background: #ff4757; color: white; border: none; padding: 10px 20px; 
                           border-radius: 15px; margin-top: 15px; cursor: pointer;">
                Annulla
            </button>
        `;
        
        overlay.appendChild(selector);
        document.body.appendChild(overlay);
    } catch (e) {
        Utils.handleError(e, 'mostra selettore quantità');
    }
}

// ==================== ✅ ORDINA DA DETTAGLIO ====================
function orderFromDetail(nomeProdotto, strain, quantita, prezzo) {
    try {
        const prodottoCompleto = `${nomeProdotto} (${strain}) - ${quantita}`;
        ordinaProdotto(prodottoCompleto, prezzo);
        
        // Chiudi tutte le finestre
        chiudiModali();
    } catch (e) {
        Utils.handleError(e, 'ordine da dettaglio');
    }
}

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

// ==================== 📷 MOSTRA MEDIA PRODOTTO ====================
function mostraMediaProdotto(prodottoNome, media) {
    try {
        const preview = document.getElementById(`mediaPreview-${prodottoNome}`);
        if (!preview) {
            console.log('❌ Preview non trovato per:', prodottoNome);
            return;
        }
        
        console.log('🎯 Caricando media:', media.url);
        preview.innerHTML = ''; // Pulisci contenuto
        
        if (media.type === 'image') {
            const img = document.createElement('img');
            img.src = media.url;
            img.style.cssText = 'width: 100%; height: 100%; object-fit: cover; border-radius: 20px;';
            
            img.onload = () => console.log('✅ Immagine caricata:', media.url);
            img.onerror = () => {
                console.log('❌ Errore caricamento:', media.url);
                preview.innerHTML = '<div style="font-size: 18px; color: #666;">📷 Immagine Non Disponibile</div>';
            };
            
            preview.appendChild(img);
            
        } else if (media.type === 'video') {
            const video = document.createElement('video');
            video.src = media.url;
            video.controls = true;
            video.style.cssText = 'width: 100%; height: 100%; border-radius: 20px; object-fit: cover;';
            
            video.onerror = () => {
                preview.innerHTML = '<div style="font-size: 18px; color: #666;">🎥 Video Non Disponibile</div>';
            };
            
            preview.appendChild(video);
            
        } else {
            preview.innerHTML = '<div style="font-size: 18px; color: #666;">📷 Formato Non Supportato</div>';
        }
    } catch (e) {
        Utils.handleError(e, 'mostra media prodotto');
    }
}

// ==================================================================================
// 🎨 ANIMAZIONI E STILI (INVARIATI)
// ==================================================================================

// ==================== 🎭 AGGIUNGI ANIMAZIONI CSS ====================
if (!document.getElementById('expansion-animations')) {
    const style = document.createElement('style');
    style.id = 'expansion-animations';
    style.textContent = `
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        @keyframes fadeOut {
            from { opacity: 1; transform: translateY(0); }
            to { opacity: 0; transform: translateY(20px); }
        }
        
        @keyframes slideIn {
            from { transform: translateX(-50%) translateY(-100%); opacity: 0; }
            to { transform: translateX(-50%) translateY(0); opacity: 1; }
        }
        
        @keyframes slideOut {
            from { transform: translateX(-50%) translateY(0); opacity: 1; }
            to { transform: translateX(-50%) translateY(-100%); opacity: 0; }
        }
        
        .product.expanded {
            z-index: 10;
            box-shadow: 0 20px 40px rgba(0,0,0,0.3) !important;
        }
    `;
    document.head.appendChild(style);
}

// ==================================================================================
// 🚀 INIZIALIZZAZIONE FINALE
// ==================================================================================

// ==================== 🏁 INIZIALIZZAZIONE CLICK CATEGORIE ====================
document.addEventListener('DOMContentLoaded', function() {
    try {
        // Carica stato salvato
        AppState.caricaStato();
        
        // Applica tema Telegram
        TelegramIntegration.applicaTema();
        TelegramIntegration.gestisciViewport();
        
        // Setup keyboard navigation
        setupKeyboardNavigation();
        
        const products = document.querySelectorAll('.product');
        
        products.forEach((product, index) => {
            // Determina categoria basandosi sull'indice
            let categoria = 'frozen1';
            if (index === 1) categoria = 'frozen2';
            if (index === 2) categoria = 'salad';
            
            // Validazione categoria
            if (!catalogoProdotti[categoria]) {
                console.warn(`Categoria non valida: ${categoria}`);
                return;
            }
            
            // Setup card categoria
            product.setAttribute('data-category', categoria);
            product.style.cursor = 'pointer';
            product.style.position = 'relative';
            
            // Event listener per espansione con debounce
            const debouncedExpand = Utils.debounce(() => {
                if (product.classList.contains('expanded')) return;
                
                // Chiudi tutte le altre categorie espanse
                chiudiCategorieEspanse();
                
                // Espandi questa categoria
                espandiProdotto(product, categoria);
            }, 200);
            
            product.addEventListener('click', debouncedExpand);
        });
        
        // Setup iniziale main button
        setupMainButton();
        
    } catch (e) {
        Utils.handleError(e, 'inizializzazione DOM');
    }
});

// ==================== ✅ APP PRONTA ====================
try {
    tg.ready();
    console.log('🚀 Telegram Mini App inizializzata con successo');
} catch (e) {
    console.error('❌ Errore inizializzazione Telegram:', e);
}

// dividi il file inn piu parti fann uno dove potrai aggiungere facilmente i prodotti i nomi le info e i video
// aggiustare lo stile dei bottoni creare unn altra variante piu compatta
// rivedere il sistema degli sconti
// andare avanti col carrello
// integrazioni con tg