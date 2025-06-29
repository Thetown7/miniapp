// ==================================================================================
// 🛒 CART MODAL - GESTIONE MODALE CARRELLO
// ==================================================================================

// ==================== 🛒 CREA PULSANTE CARRELLO FLOTTANTE ====================
function creaBottoneCarrelloFlottante() {
    // Rimuovi vecchio indicatore carrello se esiste
    const oldCartInfo = document.getElementById('cartInfo');
    if (oldCartInfo) oldCartInfo.remove();
    
    // Crea nuovo bottone carrello
    const cartButton = document.createElement('div');
    cartButton.id = 'floatingCartButton';
    cartButton.style.cssText = `
        position: fixed;
        bottom: 30px;
        right: 30px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        width: 70px;
        height: 70px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        box-shadow: 0 8px 25px rgba(0,0,0,0.3);
        transition: all 0.3s ease;
        z-index: 1000;
        border: 3px solid white;
    `;
    
    // Eventi hover
    cartButton.addEventListener('mouseenter', function() {
        this.style.transform = 'scale(1.1)';
        this.style.boxShadow = '0 12px 35px rgba(0,0,0,0.4)';
        mostraTooltipCarrello(this);
    });
    
    cartButton.addEventListener('mouseleave', function() {
        this.style.transform = 'scale(1)';
        this.style.boxShadow = '0 8px 25px rgba(0,0,0,0.3)';
        rimuoviTooltipCarrello();
    });
    
    // Click per aprire modale
    cartButton.addEventListener('click', function() {
        rimuoviTooltipCarrello();
        apriModaleCarrello();
    });
    
    document.body.appendChild(cartButton);
    // Aggiorna badge DOPO aver aggiunto il bottone al DOM
    aggiornaBadgeCarrello();
}

// ==================== 🔄 AGGIORNA BADGE CARRELLO ====================
function aggiornaBadgeCarrello() {
    const cartButton = document.getElementById('floatingCartButton');
    if (!cartButton) return;
    
    const itemCount = AppState.carrello.length;
    
    cartButton.innerHTML = `
        <div style="position: relative;">
            <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M9 2L6 9H3l3 7h12l3-7h-3l-3-7H9z"/>
                <path d="M9 16v5m6-5v5"/>
            </svg>
            ${itemCount > 0 ? `
                <div style="position: absolute; top: -10px; right: -10px; 
                            background: #ff4757; color: white; 
                            width: 24px; height: 24px; border-radius: 50%;
                            display: flex; align-items: center; justify-content: center;
                            font-size: 12px; font-weight: bold;
                            border: 2px solid white;">
                    ${itemCount}
                </div>
            ` : ''}
        </div>
    `;
}

// ==================== 💬 MOSTRA TOOLTIP CARRELLO ====================
function mostraTooltipCarrello(button) {
    rimuoviTooltipCarrello();
    
    if (AppState.carrello.length === 0) return;
    
    const tooltip = document.createElement('div');
    tooltip.id = 'cartTooltip';
    tooltip.style.cssText = `
        position: fixed;
        bottom: 110px;
        right: 30px;
        background: rgba(0, 0, 0, 0.9);
        color: white;
        padding: 12px 20px;
        border-radius: 20px;
        font-size: 14px;
        font-weight: bold;
        white-space: nowrap;
        animation: fadeIn 0.2s ease;
        z-index: 1001;
    `;
    
    tooltip.innerHTML = `
        🛒 ${AppState.carrello.length} prodotti<br>
        💰 Totale: €${AppState.totaleCarrello}
    `;
    
    document.body.appendChild(tooltip);
}

// ==================== 🗑️ RIMUOVI TOOLTIP ====================
function rimuoviTooltipCarrello() {
    const tooltip = document.getElementById('cartTooltip');
    if (tooltip) tooltip.remove();
}

// ==================== 🎭 APRI MODALE CARRELLO ====================
function apriModaleCarrello() {
    // Crea overlay
    const overlay = document.createElement('div');
    overlay.id = 'cartModalOverlay';
    overlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.8);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 2000;
        animation: fadeIn 0.3s ease;
    `;
    
    // Crea modale
    const modal = document.createElement('div');
    modal.style.cssText = `
        background: white;
        width: 90%;
        max-width: 500px;
        max-height: 80vh;
        border-radius: 40px;
        overflow: hidden;
        box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5);
        display: flex;
        flex-direction: column;
        animation: slideIn 0.3s ease;
    `;
    
    // Header modale
    const header = creaHeaderModaleCarrello();
    
    // Contenuto carrello
    const content = creaContenutoCarrello();
    
    // Footer con totale e checkout
    const footer = creaFooterCarrello();
    
    // Assembla modale
    modal.appendChild(header);
    modal.appendChild(content);
    if (AppState.carrello.length > 0) {
        modal.appendChild(footer);
    }
    
    // Click overlay per chiudere
    overlay.addEventListener('click', function(e) {
        if (e.target === overlay) {
            chiudiModaleCarrello();
        }
    });
    
    overlay.appendChild(modal);
    document.body.appendChild(overlay);
}

// ==================== 📋 CREA HEADER MODALE ====================
function creaHeaderModaleCarrello() {
    const header = document.createElement('div');
    header.style.cssText = `
        background: linear-gradient(135deg, #764ba2 0%, #ea66d2 100%);
        padding: 25px;
        color: white;
        display: flex;
        justify-content: space-between;
        align-items: center;
    `;
    
    header.innerHTML = `
        <h2 style="margin: 0; font-size: 24px;">
            🛒 Il Tuo Carrello
        </h2>
        <button onclick="chiudiModaleCarrello()" 
                style="background: rgba(255,255,255,0.2); 
                       border: 2px solid white;
                       color: white; 
                       width: 40px; height: 40px;
                       border-radius: 50%; 
                       font-size: 24px;
                       cursor: pointer;
                       display: flex;
                       align-items: center;
                       justify-content: center;
                       transition: all 0.3s ease;">
            ×
        </button>
    `;
    
    return header;
}

// ==================== 📦 CREA CONTENUTO CARRELLO ====================
function creaContenutoCarrello() {
    const content = document.createElement('div');
    content.style.cssText = `
        flex: 1;
        overflow-y: auto;
        padding: 20px;
        background: #f8f9fa;
    `;
    
    if (AppState.carrello.length === 0) {
        content.innerHTML = `
            <div style="text-align: center; padding: 60px 20px;">
                <div style="font-size: 60px; margin-bottom: 20px;">🛒</div>
                <h3 style="color: #666; margin-bottom: 10px;">Il carrello è vuoto</h3>
                <p style="color: #999;">Aggiungi prodotti per continuare</p>
            </div>
        `;
    } else {
        // Lista prodotti nel carrello
        AppState.carrello.forEach((prodotto, index) => {
            const item = creaItemCarrello(prodotto, index);
            content.appendChild(item);
        });
    }
    
    return content;
}

// ==================== 🎁 CREA SINGOLO ITEM CARRELLO ====================
function creaItemCarrello(prodotto, index) {
    const item = document.createElement('div');
    item.style.cssText = `
        background: white;
        border-radius: 20px;
        padding: 15px;
        margin-bottom: 15px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
    `;
    
    // Estrai info dal nome prodotto
    const [nomeProdotto, info] = prodotto.nome.split(' (');
    const strainQuantita = info ? info.replace(')', '') : '';
    
    item.innerHTML = `
        <div style="flex: 1;">
            <div style="font-weight: bold; font-size: 16px; color: #333; margin-bottom: 5px;">
                ${Utils.sanitizeHTML(nomeProdotto)}
            </div>
            <div style="font-size: 14px; color: #667eea;">
                🧬 ${Utils.sanitizeHTML(strainQuantita)}
            </div>
        </div>
        
        <div style="display: flex; align-items: center; gap: 15px;">
            <div style="font-weight: bold; font-size: 18px; color: #48bb78;">
                €${Utils.formatPrice(prodotto.prezzo)}
            </div>
            
            <button onclick="rimuoviDalCarrello(${index})"
                    style="background: #ff4757;
                           color: white;
                           border: none;
                           width: 35px;
                           height: 35px;
                           border-radius: 50%;
                           cursor: pointer;
                           display: flex;
                           align-items: center;
                           justify-content: center;
                           transition: all 0.3s ease;
                           font-size: 20px;"
                    onmouseover="this.style.transform='scale(1.1)'"
                    onmouseout="this.style.transform='scale(1)'">
                🗑️
            </button>
        </div>
    `;
    
    // Hover effect
    item.addEventListener('mouseenter', () => {
        item.style.transform = 'translateX(5px)';
        item.style.boxShadow = '0 4px 15px rgba(0,0,0,0.15)';
    });
    
    item.addEventListener('mouseleave', () => {
        item.style.transform = 'translateX(0)';
        item.style.boxShadow = '0 2px 10px rgba(0,0,0,0.1)';
    });
    
    return item;
}

// ==================== 💰 CREA FOOTER CARRELLO ====================
function creaFooterCarrello() {
    const footer = document.createElement('div');
    footer.style.cssText = `
        background: white;
        padding: 20px;
        border-top: 2px solid #f0f0f0;
    `;
    
    footer.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
            <div style="font-size: 20px; font-weight: bold; color: #333;">
                Totale:
            </div>
            <div style="font-size: 28px; font-weight: bold; color: #48bb78;">
                €${AppState.totaleCarrello}
            </div>
        </div>
        
        <div style="display: flex; gap: 10px;">
            <button onclick="svuotaCarrelloConConferma()"
                    style="background: #ff4757;
                           color: white;
                           border: none;
                           padding: 15px 25px;
                           border-radius: 25px;
                           font-size: 16px;
                           font-weight: bold;
                           cursor: pointer;
                           transition: all 0.3s ease;"
                    onmouseover="this.style.transform='translateY(-2px)'"
                    onmouseout="this.style.transform='translateY(0)'">
                🗑️ Svuota
            </button>
            
            <button onclick="procediAlCheckout()"
                    style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                           color: white;
                           border: none;
                           padding: 15px 25px;
                           border-radius: 25px;
                           font-size: 16px;
                           font-weight: bold;
                           cursor: pointer;
                           flex: 1;
                           transition: all 0.3s ease;
                           box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);"
                    onmouseover="this.style.transform='translateY(-2px)'"
                    onmouseout="this.style.transform='translateY(0)'">
                Procedi all'Ordine ➜
            </button>
        </div>
    `;
    
    return footer;
}

// ==================== 🗑️ RIMUOVI DAL CARRELLO ====================
function rimuoviDalCarrello(index) {
    AppState.rimuoviDalCarrello(index);
    
    // Aggiorna modale
    const overlay = document.getElementById('cartModalOverlay');
    if (overlay) {
        overlay.remove();
        apriModaleCarrello();
    }
    
    // Aggiorna badge
    aggiornaBadgeCarrello();
}

// ==================== 🗑️ SVUOTA CARRELLO CON CONFERMA ====================
function svuotaCarrelloConConferma() {
    if (confirm('Sei sicuro di voler svuotare il carrello?')) {
        AppState.svuotaCarrello();
        chiudiModaleCarrello();
        aggiornaBadgeCarrello();
        
        // Mostra notifica
        const notifica = document.createElement('div');
        notifica.style.cssText = `
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: #ff4757;
            color: white;
            padding: 15px 25px;
            border-radius: 25px;
            font-weight: bold;
            z-index: 3000;
            animation: slideIn 0.3s ease;
        `;
        notifica.textContent = '🗑️ Carrello svuotato!';
        
        document.body.appendChild(notifica);
        
        setTimeout(() => {
            notifica.style.animation = 'slideOut 0.3s ease forwards';
            setTimeout(() => notifica.remove(), 300);
        }, 2000);
    }
}

// ==================== ✅ PROCEDI AL CHECKOUT ====================
function procediAlCheckout() {
    chiudiModaleCarrello();
    processaOrdineFinale();
}

// ==================== ❌ CHIUDI MODALE CARRELLO ====================
function chiudiModaleCarrello() {
    const overlay = document.getElementById('cartModalOverlay');
    if (overlay) {
        overlay.style.animation = 'fadeOut 0.3s ease forwards';
        const modal = overlay.querySelector('div');
        if (modal) {
            modal.style.animation = 'slideOut 0.3s ease forwards';
        }
        setTimeout(() => overlay.remove(), 300);
    }
}

// ==================== 🔄 OVERRIDE AGGIORNA CARRELLO ====================
const aggiornaCarrelloOriginale = aggiornaCarrello;
function aggiornaCarrello() {
    aggiornaCarrelloOriginale();
    aggiornaBadgeCarrello();
}

// ==================== 🎯 ANIMA BOTTONE CARRELLO ====================
function animaBottoneCarrello() {
    const cartButton = document.getElementById('floatingCartButton');
    if (!cartButton) return;
    
    // Aggiungi animazione pulse
    cartButton.style.animation = 'pulse 0.6s ease';
    
    // Rimuovi animazione dopo completamento
    setTimeout(() => {
        cartButton.style.animation = '';
    }, 600);
}