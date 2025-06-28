// ==================================================================================
// 🚀 INIZIALIZZAZIONE PRINCIPALE
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
