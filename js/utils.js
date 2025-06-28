// ==================================================================================
// 🔧 UTILITÀ E HELPERS
// ==================================================================================

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