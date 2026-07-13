import sqlite3

def upgrade_db():
    try:
        conn = sqlite3.connect('dados.db')
        conn.execute('ALTER TABLE clt_registros ADD COLUMN total_rem FLOAT DEFAULT 0.0')
        conn.commit()
        conn.close()
        print("Column total_rem added successfully.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    upgrade_db()
