import sqlite3
import os

def create_database():
    # Define o caminho para a pasta /data criada
    db_path = os.path.join("data", "sc2_results.db")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Criando a tabela de partidas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            result TEXT,
            duration_s REAL,
            minerals_collected INTEGER,
            workers_built INTEGER
        )
    ''')
    
    conn.commit()
    conn.close()
    print(f"Banco de dados criado com sucesso em: {db_path}")

if __name__ == "__main__":
    create_database()