// ==================================================================================
// 🎨 FUNZIONI INTERFACCIA UTENTE
// ==================================================================================

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