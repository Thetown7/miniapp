# 📍 Gestione Punti Vendita - Guida Rapida

## 🔧 Come Modificare i Punti Vendita

I punti vendita sono configurati direttamente nel file `seller_bot.py` nella lista `PUNTI_VENDITA` (righe 31-51).

### Struttura di un Punto Vendita
```python
{
    "id": 1,                    # ID univoco del punto (numero)
    "nome": "Nome del Punto",   # Nome visualizzato nel bot
    "apple_maps_url": "https://maps.apple.com/...",    # Link Apple Maps
    "google_maps_url": "https://maps.google.com/...",  # Link Google Maps
    "foto_path": "punti_vendita/punto1.jpg"            # Percorso foto (opzionale)
}
```

### 📝 Per Aggiungere un Nuovo Punto:
1. Apri `seller_bot.py`
2. Trova la lista `PUNTI_VENDITA` (riga ~31)
3. Aggiungi un nuovo dizionario con:
   - ID univoco (numero progressivo)
   - Nome del punto
   - URL Apple Maps
   - URL Google Maps
   - Path della foto (opzionale)

### 🗺️ Come Ottenere gli URL delle Mappe:

#### Apple Maps:
1. Apri Apple Maps sul Mac/iPhone
2. Cerca l'indirizzo
3. Clicca "Condividi" → "Copia Link"

#### Google Maps:
1. Apri Google Maps
2. Cerca l'indirizzo
3. Clicca "Condividi" → "Copia Link"

### 📸 Per Aggiungere Foto:
1. Salva l'immagine nella cartella `punti_vendita/`
2. Nomina il file (es: `punto1.jpg`, `punto2.jpg`)
3. Inserisci il percorso nel campo `foto_path`

## 🎮 Comandi Bot

### Per Admin e Utenti:
- `/point` - Mostra il punto vendita con link diretti e foto

Il formato di visualizzazione è:
```
📍 Point [Nome Punto]

🍎 Apple Maps: [link diretto]

🗺️ Google Maps: [link diretto]

📸 Foto Point: [immagine allegata]
```

## ⚡ Modifiche Immediate

Dopo aver modificato la lista `PUNTI_VENDITA`:
1. Salva il file `seller_bot.py`
2. Riavvia il bot (Ctrl+C e poi `python3 seller_bot.py`)
3. Le modifiche sono subito attive!

## 📋 Esempio Completo

```python
PUNTI_VENDITA = [
    {
        "id": 1,
        "nome": "Ponte Giacomo",
        "apple_maps_url": "https://maps.apple.com/?address=Via%20del%20Corso%201,%2000187%20Roma",
        "google_maps_url": "https://maps.google.com/maps?q=Via+del+Corso+1,+Roma",
        "foto_path": "punti_vendita/ponte_giacomo.jpg"
    }
]
```

## 🛠️ Troubleshooting

- **Foto non si visualizza**: Controlla che il file esista nel percorso specificato
- **Link non funziona**: Verifica che gli URL siano corretti e completi
- **Punto non trovato**: Controlla che l'ID sia univoco e numerico
- **Bot non risponde**: Riavvia il bot dopo le modifiche

---
💡 **Tip**: Testa sempre i link delle mappe prima di inserirli nel bot!
