import sqlite3

def upgrade_db():
    try:
        conn = sqlite3.connect('dados.db')
        conn.execute("ALTER TABLE users ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'viewer'")
        conn.commit()
        conn.close()
        print("Column role added successfully.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    upgrade_db()
