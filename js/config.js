// ==================================================================================
// 📦 CONFIGURAZIONI E DATI PRODOTTI
// ==================================================================================

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