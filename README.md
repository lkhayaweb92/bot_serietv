# 🐲 Bot SerieTV - Dragon Ball RPG

Un bot Telegram RPG completo e avvincente basato sull'universo di Dragon Ball! 
Combatti contro Boss storici, colleziona personaggi unici e scala le classifiche stagionali in questo GDR testuale ricco di funzionalità.

## ✨ Caratteristiche Principali

*   **🔥 Saghe Dinamiche**: Rivivi le saghe storiche (Saga di Pilaf, 21° Torneo Tenkaichi, ecc.) che cambiano periodicamente.
*   **⚔️ Raid Boss**: Combattimenti cooperativi in tempo reale. Unisciti agli altri giocatori per sconfiggere nemici iconici (Re Pilaf, Olong, ecc.).
*   **🏆 Achievements & Progressi**: Sistema di obiettivi automatici che traccia Boss sconfitti, Livelli raggiunti e Personaggi ottenuti.
*   **🃏 Collezione**: Colleziona decine di personaggi e sticker rari.
*   **📅 Stagioni & Pass**: Sistema a stagioni con date di scadenza, classifiche dedicate e premi esclusivi per i migliori guerrieri.
*   **😂 Meccaniche Lore-Friendly**: Include chicche come gli "Attacchi Goffi" dei boss contro i nuovi giocatori (i boss inciampano se attacchi da livello < 5!).

## 🛠 Installazione

### Prerequisiti
*   Python 3.8+
*   Un Bot Token di Telegram (ottenibile da @BotFather)

### Setup

1.  **Clona il repository**:
    ```bash
    git clone https://github.com/lkhayaweb92/bot_serietv.git
    cd bot_serietv
    ```

2.  **Configura l'ambiente**:
    Il progetto utilizza un file `settings.py` per le configurazioni sensibili.
    Copia il file di esempio e rinominalo:
    ```bash
    # Windows
    copy settings.py.example settings.py
    # Linux/Mac
    cp settings.py.example settings.py
    ```
    Apri `settings.py` e inserisci il tuo **BOT TOKEN** e gli ID dei gruppi Telegram di amministrazione/gioco.

3.  **Installa le dipendenze**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Avvia il Bot**:
    ```bash
    python main.py
    ```

## 🎮 Comandi Utili

### Giocatore
| Comando | Descrizione |
| :--- | :--- |
| `/start` | Avvia il bot, registra l'utente e mostra il menu di benvenuto |
| `/menu` | Apre il pannello di controllo principale |
| `/profilo` | Mostra statistiche, livello, esperienza e monete |
| `/daily` | Riscatta la ricompensa giornaliera |

### Admin (Gestione Saghe)
| Comando | Descrizione |
| :--- | :--- |
| `/season_list` | Mostra tutte le saghe disponibili, lo stato e le date di scadenza |
| `/season_set [ID] [Giorni]` | Attiva una specifica saga. Opzionale: imposta la durata in giorni |
| `/spawn_boss` | Forza l'apparizione immediata di un Boss della saga attiva |
| `/set_lv [User] [Lv]` | Imposta manualmente il livello di un utente (utile per test) |

## 🛡 Sicurezza e Struttura
Il progetto è strutturato per separare il codice dalla configurazione sensibile:
*   `main.py`: Logica principale e gestione comandi.
*   `model.py`: Modelli Database (SQLAlchemy) e logica di gioco core.
*   `settings.py`: (Non versionato) Contiene i Token segreti.
*   `settings.py.example`: Template sicuro per la configurazione.

## 🤝 Contribuire
Sentiti libero di aprire **Issues** per segnalare bug o **Pull Requests** per proporre nuove funzionalità!

## 📜 Licenza
Questo progetto è distribuito "così com'è". Divertiti!