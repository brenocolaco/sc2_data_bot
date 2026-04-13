import sqlite3
import os

# Caminho para o seu banco atual
db_path = os.path.join("data", "sc2_results.db")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    # O comando ALTER TABLE adiciona a coluna sem apagar seus jogos antigos
    cursor.execute('ALTER TABLE matches ADD COLUMN difficulty TEXT')
    conn.commit()
    print("Sucesso: Coluna 'difficulty' adicionada!")
except sqlite3.OperationalError:
    print("Aviso: A coluna já existe ou o banco não foi encontrado.")

conn.close()