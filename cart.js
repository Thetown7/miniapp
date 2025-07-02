// ==================================================================================
// 🛒 CART.JS - SISTEMA CARRELLO CON ESPANSIONE IN-PLACE
// ==================================================================================

(function() {
    'use strict';

    // ==================== 🎨 STILI CSS CARRELLO ====================
    const injectCartStyles = () => {
        if (document.getElementById('cart-styles')) return;
        
        const style = document.createElement('style');
        style.id = 'cart-styles';
        style.textContent = `
            /* Contenitore Carrello Principale */
            #cartContainer {
                position: fixed;
                bottom: 20px;
                right: 20px;
                z-index: 1000;
                display: flex;
                flex-direction: column;
                align-items: flex-end;
                gap: 10px;
            }

            /* Carrello Espanso */
            #expandedCart {
                background: white;
                border-radius: 20px;
                box-shadow: 0 8px 30px rgba(0,0,0,0.3);
                overflow: hidden;
                max-height: 0;
                opacity: 0;
                transform: translateY(15px);
                transition: all 0.4s ease;
                width: 280px;
                border: 2px solid #764ba2;
            }

            #expandedCart.active {
                max-height: 400px;
                opacity: 1;
                transform: translateY(0);
            }

            /* Header Carrello Espanso */
            .cart-expanded-header {
                background: linear-gradient(135deg, #764ba2 0%, #ea66d2 100%);
                padding: 15px;
                color: white;
                font-weight: bold;
                font-size: 14px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }

            /* Lista Prodotti */
            .cart-items-container {
                max-height: 220px;
                overflow-y: auto;
                padding: 12px;
                background: #f8f9fa;
            }

            .cart-items-container::-webkit-scrollbar {
                width: 4px;
            }

            .cart-items-container::-webkit-scrollbar-track {
                background: #f1f1f1;
            }

            .cart-items-container::-webkit-scrollbar-thumb {
                background: #764ba2;
                border-radius: 2px;
            }

            /* Item Carrello */
            .cart-item-expanded {
                background: white;
                border-radius: 12px;
                padding: 10px;
                margin-bottom: 8px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                box-shadow: 0 2px 6px rgba(0,0,0,0.1);
                transition: all 0.3s ease;
                animation: slideInCart 0.3s ease;
            }

            .cart-item-expanded:hover {
                transform: translateX(-3px);
                box-shadow: 0 3px 10px rgba(0,0,0,0.15);
            }

            /* Footer Carrello */
            .cart-footer-expanded {
                background: white;
                padding: 15px;
                border-top: 2px solid #f0f0f0;
            }

            .cart-total-expanded {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 12px;
                font-size: 16px;
                font-weight: bold;
            }

            .cart-total-amount {
                color: #48bb78;
                font-size: 18px;
            }

            /* Bottoni Footer */
            .cart-actions {
                display: flex;
                gap: 8px;
            }

            .clear-cart-btn {
                background: #ff4757;
                color: white;
                border: none;
                padding: 10px 16px;
                border-radius: 15px;
                font-weight: bold;
                cursor: pointer;
                transition: all 0.3s ease;
                font-size: 12px;
            }

            .clear-cart-btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 3px 10px rgba(255, 71, 87, 0.4);
            }

            .checkout-btn-expanded {
                background: linear-gradient(135deg, #48bb78 0%, #46d1a1 100%);
                color: white;
                border: none;
                padding: 10px 16px;
                border-radius: 15px;
                font-weight: bold;
                cursor: pointer;
                flex: 1;
                transition: all 0.3s ease;
                box-shadow: 0 3px 10px rgba(72, 187, 120, 0.3);
                font-size: 12px;
            }

            .checkout-btn-expanded:hover {
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(72, 187, 120, 0.5);
            }

            /* Bottone Carrello Goccia */
            #floatingCartButton {
                position: relative;
                width: 55px;
                height: 55px;
                background: linear-gradient(135deg, #764ba2 0%, #ea66d2 100%);
                border-radius: 50% 50% 50% 0;
                transform: rotate(-45deg);
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                box-shadow: 0 6px 20px rgba(0,0,0,0.3);
                transition: all 0.3s ease;
                border: 2px solid white;
            }

            #floatingCartButton:hover {
                transform: rotate(-45deg) scale(1.1);
                box-shadow: 0 10px 25px rgba(0,0,0,0.4);
            }

            #floatingCartButton.bounce {
                animation: bounceCart 0.5s ease;
            }

            /* Icona Carrello */
            .cart-icon-wrapper {
                transform: rotate(45deg);
                display: flex;
                align-items: center;
                justify-content: center;
                position: relative;
            }

            /* Badge Contatore */
            #cartBadge {
                position: absolute;
                top: -12px;
                right: -12px;
                background: #ff4757;
                color: white;
                width: 20px;
                height: 20px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 10px;
                font-weight: bold;
                border: 2px solid white;
                transform: rotate(45deg);
                opacity: 0;
                transform: scale(0) rotate(45deg);
                transition: all 0.3s ease;
            }

            #cartBadge.active {
                opacity: 1;
                transform: scale(1) rotate(45deg);
            }

            /* Info Rapide */
            .cart-quick-info {
                background: rgba(0, 0, 0, 0.9);
                color: white;
                padding: 8px 12px;
                border-radius: 15px;
                font-size: 11px;
                font-weight: bold;
                white-space: nowrap;
                opacity: 0;
                transform: translateY(8px);
                transition: all 0.3s ease;
                margin-bottom: 8px;
            }

            .cart-quick-info.show {
                opacity: 1;
                transform: translateY(0);
            }

            /* Carrello Vuoto */
            .empty-cart-message {
                text-align: center;
                padding: 30px 15px;
                color: #666;
            }

            .empty-cart-icon {
                font-size: 45px;
                margin-bottom: 10px;
                opacity: 0.5;
            }

            .empty-cart-message h4 {
                font-size: 14px;
                margin-bottom: 5px;
            }

            .empty-cart-message p {
                font-size: 12px;
            }

            /* Animazioni */
            @keyframes slideInCart {
                from { 
                    opacity: 0; 
                    transform: translateX(20px); 
                }
                to { 
                    opacity: 1; 
                    transform: translateX(0); 
                }
            }

            @keyframes bounceCart {
                0%, 100% { transform: rotate(-45deg) scale(1); }
                50% { transform: rotate(-45deg) scale(1.15); }
            }

            /* Remove Item Button */
            .remove-item-btn {
                background: #ff4757;
                color: white;
                border: none;
                width: 24px;
                height: 24px;
                border-radius: 50%;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: all 0.3s ease;
                font-size: 14px;
                font-weight: bold;
            }

            .remove-item-btn:hover {
                transform: scale(1.1);
                box-shadow: 0 2px 8px rgba(255, 71, 87, 0.4);
            }

            /* Responsive */
            @media (max-width: 480px) {
                #expandedCart {
                    width: calc(100vw - 40px);
                    right: -10px;
                }
                
                #cartContainer {
                    right: 15px;
                    bottom: 15px;
                }
            }

            /* Stili per elementi dei prodotti nel carrello */
            .cart-item-expanded > div:first-child {
                font-size: 12px;
            }

            .cart-item-expanded > div:first-child > div:first-child {
                font-size: 13px;
            }

            .cart-item-expanded > div:first-child > div:last-child {
                font-size: 11px;
            }

            .cart-item-expanded > div:last-child > span {
                font-size: 14px;
            }
        `;
        document.head.appendChild(style);
    };

    // ==================== 🛒 CLASSE CARRELLO ====================
    class CartManager {
        constructor() {
            this.isExpanded = false;
            this.quickInfoTimeout = null;
            this.init();
        }

        init() {
            // Inietta stili
            injectCartStyles();
            
            // Crea struttura carrello
            this.createCartStructure();
            
            // Setup eventi
            this.setupEventListeners();
            
            // Aggiorna UI iniziale
            this.updateCartUI();
        }

        createCartStructure() {
            // Container principale
            const container = document.createElement('div');
            container.id = 'cartContainer';
            
            // Carrello espanso
            const expandedCart = document.createElement('div');
            expandedCart.id = 'expandedCart';
            expandedCart.innerHTML = `
                <div class="cart-expanded-header">
                    <span>🛒 Il Tuo Carrello</span>
                    <span id="cartItemCount">(0)</span>
                </div>
                <div class="cart-items-container" id="cartItemsList">
                    <!-- Items verranno inseriti qui -->
                </div>
                <div class="cart-footer-expanded">
                    <div class="cart-total-expanded">
                        <span>Totale:</span>
                        <span class="cart-total-amount" id="cartTotalAmount">€0</span>
                    </div>
                    <div class="cart-actions">
                        <button class="clear-cart-btn" onclick="cartManager.clearCart()">
                            🗑️ Svuota
                        </button>
                        <button class="checkout-btn-expanded" onclick="cartManager.checkout()">
                            Conferma Ordine ✨
                        </button>
                    </div>
                </div>
            `;
            
            // Info rapide
            const quickInfo = document.createElement('div');
            quickInfo.className = 'cart-quick-info';
            quickInfo.id = 'cartQuickInfo';
            
            // Bottone goccia
            const button = document.createElement('div');
            button.id = 'floatingCartButton';
            button.innerHTML = `
                <div class="cart-icon-wrapper">
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2">
                        <path d="M9 2L6 9H3L3 14C3 15.6569 4.34315 17 6 17H18C19.6569 17 21 15.6569 21 14L21 9H18L15 2H9Z"/>
                        <path d="M9 17V22"/>
                        <path d="M15 17V22"/>
                    </svg>
                    <div id="cartBadge">0</div>
                </div>
            `;
            
            // Assembla struttura
            container.appendChild(expandedCart);
            container.appendChild(quickInfo);
            container.appendChild(button);
            
            document.body.appendChild(container);
        }

        setupEventListeners() {
            const button = document.getElementById('floatingCartButton');
            const expandedCart = document.getElementById('expandedCart');
            
            // Click per toggle espansione
            button.addEventListener('click', () => this.toggleCart());
            
            // Hover per info rapide
            button.addEventListener('mouseenter', () => this.showQuickInfo());
            button.addEventListener('mouseleave', () => this.hideQuickInfo());
            
            // Click fuori per chiudere
            document.addEventListener('click', (e) => {
                if (this.isExpanded && 
                    !button.contains(e.target) && 
                    !expandedCart.contains(e.target)) {
                    this.toggleCart();
                }
            });
            
            // Intercetta modifiche al carrello
            const originalNotifica = AppState.notificaCambiamento;
            AppState.notificaCambiamento = () => {
                // Prima chiama funzioni originali (tranne aggiornaBadgeCarrello che non esiste più)
                if (window.setupMainButton) setupMainButton();
                if (window.inviaStatoATelegram) inviaStatoATelegram();
                
                // Poi aggiorna UI carrello
                this.updateCartUI();
                this.animateCartButton();
            };
        }

        toggleCart() {
            this.isExpanded = !this.isExpanded;
            const expandedCart = document.getElementById('expandedCart');
            
            if (this.isExpanded) {
                this.hideQuickInfo();
                expandedCart.classList.add('active');
                this.renderCartItems();
            } else {
                expandedCart.classList.remove('active');
            }
        }

        showQuickInfo() {
            if (this.isExpanded || AppState.carrello.length === 0) return;
            
            clearTimeout(this.quickInfoTimeout);
            const quickInfo = document.getElementById('cartQuickInfo');
            quickInfo.innerHTML = `
                🛒 ${AppState.carrello.length} prodotti • €${AppState.totaleCarrello}
            `;
            quickInfo.classList.add('show');
        }

        hideQuickInfo() {
            clearTimeout(this.quickInfoTimeout);
            this.quickInfoTimeout = setTimeout(() => {
                const quickInfo = document.getElementById('cartQuickInfo');
                quickInfo.classList.remove('show');
            }, 200);
        }

        updateCartUI() {
            // Aggiorna badge
            const badge = document.getElementById('cartBadge');
            const count = AppState.carrello.length;
            
            if (count > 0) {
                badge.textContent = count;
                badge.classList.add('active');
            } else {
                badge.classList.remove('active');
                if (this.isExpanded) {
                    this.toggleCart();
                }
            }
            
            // Aggiorna contatore header
            const itemCount = document.getElementById('cartItemCount');
            if (itemCount) {
                itemCount.textContent = `(${count})`;
            }
            
            // Aggiorna totale
            const totalAmount = document.getElementById('cartTotalAmount');
            if (totalAmount) {
                totalAmount.textContent = `€${AppState.totaleCarrello}`;
            }
            
            // Se espanso, aggiorna lista
            if (this.isExpanded) {
                this.renderCartItems();
            }
        }

        renderCartItems() {
            const container = document.getElementById('cartItemsList');
            
            if (AppState.carrello.length === 0) {
                container.innerHTML = `
                    <div class="empty-cart-message">
                        <div class="empty-cart-icon">🛒</div>
                        <h4>Carrello Vuoto</h4>
                        <p>Aggiungi prodotti per continuare</p>
                    </div>
                `;
                return;
            }
            
            container.innerHTML = AppState.carrello.map((item, index) => {
                // Estrai info dal nome
                const parts = item.nome.split(' (');
                const productName = parts[0];
                const details = parts[1] ? parts[1].replace(')', '') : '';
                
                return `
                    <div class="cart-item-expanded">
                        <div style="flex: 1;">
                            <div style="font-weight: bold; color: #333; margin-bottom: 2px;">
                                ${this.sanitizeHTML(productName)}
                            </div>
                            <div style="font-size: 11px; color: #667eea;">
                                🧬 ${this.sanitizeHTML(details)}
                            </div>
                        </div>
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <span style="font-weight: bold; color: #48bb78; font-size: 14px;">
                                €${item.prezzo}
                            </span>
                            <button class="remove-item-btn" onclick="cartManager.removeItem(${index})">
                                ×
                            </button>
                        </div>
                    </div>
                `;
            }).join('');
        }

        removeItem(index) {
            AppState.rimuoviDalCarrello(index);
        }

        clearCart() {
            if (confirm('Sei sicuro di voler svuotare il carrello?')) {
                AppState.svuotaCarrello();
                this.showNotification('🗑️ Carrello svuotato!', '#ff4757');
            }
        }

        checkout() {
            if (AppState.carrello.length === 0) {
                this.showNotification('Il carrello è vuoto!', '#ff4757');
                return;
            }
            
            // Chiudi carrello
            this.toggleCart();
            
            // Processa ordine
            if (window.processaOrdineFinale) {
                window.processaOrdineFinale();
            } else {
                console.log('Ordine processato:', AppState.carrello);
                this.showNotification('✅ Ordine Confermato!', '#48bb78');
                AppState.svuotaCarrello();
            }
        }

        animateCartButton() {
            const button = document.getElementById('floatingCartButton');
            button.classList.add('bounce');
            setTimeout(() => button.classList.remove('bounce'), 500);
        }

        showNotification(message, color = '#48bb78') {
            const notification = document.createElement('div');
            notification.style.cssText = `
                position: fixed;
                top: 15px;
                left: 50%;
                transform: translateX(-50%);
                background: ${color};
                color: white;
                padding: 10px 20px;
                border-radius: 20px;
                font-weight: bold;
                box-shadow: 0 4px 15px rgba(0,0,0,0.3);
                z-index: 3000;
                animation: slideInCart 0.3s ease;
                font-size: 12px;
            `;
            notification.textContent = message;
            document.body.appendChild(notification);
            
            setTimeout(() => {
                notification.style.animation = 'fadeOut 0.3s ease';
                setTimeout(() => notification.remove(), 300);
            }, 3000);
        }

        // Utility per sanitizzare HTML
        sanitizeHTML(str) {
            const temp = document.createElement('div');
            temp.textContent = str;
            return temp.innerHTML;
        }
    }

    // ==================== 🚀 INIZIALIZZAZIONE ====================
    let cartManager;
    
    // Attendi che il DOM sia pronto
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            cartManager = new CartManager();
            window.cartManager = cartManager;
        });
    } else {
        cartManager = new CartManager();
        window.cartManager = cartManager;
    }

    // ==================== 🔄 SOSTITUISCI FUNZIONE aggiornaBadgeCarrello ====================
    // Questa funzione viene chiamata da altri punti del codice, quindi la creiamo vuota
    window.aggiornaBadgeCarrello = function() {
        // Ora gestita internamente da CartManager
        if (cartManager) {
            cartManager.updateCartUI();
        }
    };

})();