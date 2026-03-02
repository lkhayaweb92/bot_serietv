
import sqlite3

def seed_factions():
    conn = sqlite3.connect('dbz.db')
    cursor = conn.cursor()
    
    factions = [
        (1, 'Squadra Z', "Protettori della Terra, combattono per la pace nell'universo.", 0, "https://static.wikia.nocookie.net/dragonball/images/e/ef/Z_Fighters_BoG_01.png"),
        (2, 'Esercito del Fiocco Rosso', 'Organizzazione paramilitare decisa a conquistare il mondo.', 0, "https://static.wikia.nocookie.net/dragonball/images/8/87/Red_Ribbon_Army_Logo.png"),
        (3, 'Pattuglia Galattica', "Polizia interstellare che mantiene l'ordine nella Via Lattea.", 0, "https://static.wikia.nocookie.net/dragonball/images/9/91/Galactic_Patrol_Logo.png")
    ]
    
    cursor.executemany('''
        INSERT OR IGNORE INTO fazione (id, nome, descrizione, punteggio, link_immagine)
        VALUES (?, ?, ?, ?, ?)
    ''', factions)
    
    conn.commit()
    
    cursor.execute('SELECT * FROM fazione')
    print(cursor.fetchall())
    
    conn.close()

if __name__ == '__main__':
    seed_factions()
