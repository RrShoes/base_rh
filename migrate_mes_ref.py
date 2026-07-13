"""
Recria agrupador_pessoa e agrupador_cc com constraint correta incluindo mes_ref.
SQLite nao suporta DROP CONSTRAINT, entao recriaremos as tabelas.
"""
import sqlite3

conn = sqlite3.connect('dados.db')
conn.execute('PRAGMA journal_mode=WAL')

# --- agrupador_pessoa ---
print("Recriando agrupador_pessoa...")
conn.execute("""
CREATE TABLE IF NOT EXISTS agrupador_pessoa_new (
    id INTEGER PRIMARY KEY,
    identificador TEXT NOT NULL,
    tipo_contrato TEXT NOT NULL,
    mes_ref TEXT NOT NULL DEFAULT '2026-06',
    nome TEXT,
    centro_custo TEXT,
    agrupador1 TEXT,
    agrupador2 TEXT,
    agrupador3 TEXT,
    inativo BOOLEAN DEFAULT 0,
    UNIQUE(identificador, tipo_contrato, mes_ref)
)
""")

# Copy existing data
conn.execute("""
INSERT OR IGNORE INTO agrupador_pessoa_new
    (id, identificador, tipo_contrato, mes_ref, nome, centro_custo, agrupador1, agrupador2, agrupador3, inativo)
SELECT id, identificador, tipo_contrato, mes_ref, nome, centro_custo, agrupador1, agrupador2, agrupador3, inativo
FROM agrupador_pessoa
""")
conn.commit()

# Drop old and rename
conn.execute("DROP TABLE agrupador_pessoa")
conn.execute("ALTER TABLE agrupador_pessoa_new RENAME TO agrupador_pessoa")
conn.commit()
print(f"  agrupador_pessoa recriada com {conn.execute('SELECT count(*) FROM agrupador_pessoa').fetchone()[0]} registros")

# --- agrupador_cc ---
print("Recriando agrupador_cc...")
conn.execute("""
CREATE TABLE IF NOT EXISTS agrupador_cc_new (
    id INTEGER PRIMARY KEY,
    centro_custo TEXT NOT NULL,
    tipo_contrato TEXT NOT NULL DEFAULT 'TODOS',
    mes_ref TEXT NOT NULL DEFAULT '2026-06',
    agrupador1 TEXT,
    agrupador2 TEXT,
    agrupador3 TEXT,
    UNIQUE(centro_custo, tipo_contrato, mes_ref)
)
""")

conn.execute("""
INSERT OR IGNORE INTO agrupador_cc_new
    (id, centro_custo, tipo_contrato, mes_ref, agrupador1, agrupador2, agrupador3)
SELECT id, centro_custo, tipo_contrato, mes_ref, agrupador1, agrupador2, agrupador3
FROM agrupador_cc
""")
conn.commit()

conn.execute("DROP TABLE agrupador_cc")
conn.execute("ALTER TABLE agrupador_cc_new RENAME TO agrupador_cc")
conn.commit()
print(f"  agrupador_cc recriada com {conn.execute('SELECT count(*) FROM agrupador_cc').fetchone()[0]} registros")

# --- Agora copiar para meses anteriores ---
print("\nCopiando para meses 2026-02 a 2026-05...")
meses = ['2026-02', '2026-03', '2026-04', '2026-05']

pessoa_rows = conn.execute(
    "SELECT identificador, tipo_contrato, nome, centro_custo, agrupador1, agrupador2, agrupador3, inativo FROM agrupador_pessoa WHERE mes_ref='2026-06'"
).fetchall()

cc_rows = conn.execute(
    "SELECT centro_custo, tipo_contrato, agrupador1, agrupador2, agrupador3 FROM agrupador_cc WHERE mes_ref='2026-06'"
).fetchall()

for mes in meses:
    count_p = 0
    for r in pessoa_rows:
        try:
            conn.execute(
                "INSERT OR IGNORE INTO agrupador_pessoa (identificador, tipo_contrato, mes_ref, nome, centro_custo, agrupador1, agrupador2, agrupador3, inativo) VALUES (?,?,?,?,?,?,?,?,?)",
                (r[0], r[1], mes, r[2], r[3], r[4], r[5], r[6], r[7])
            )
            count_p += 1
        except Exception as e:
            print(f"  ERRO pessoa {r[0]} mes {mes}: {e}")

    count_c = 0
    for r in cc_rows:
        try:
            conn.execute(
                "INSERT OR IGNORE INTO agrupador_cc (centro_custo, tipo_contrato, mes_ref, agrupador1, agrupador2, agrupador3) VALUES (?,?,?,?,?,?)",
                (r[0], r[1], mes, r[2], r[3], r[4])
            )
            count_c += 1
        except Exception as e:
            print(f"  ERRO cc {r[0]} mes {mes}: {e}")

    print(f"  {mes}: {count_p} pessoas, {count_c} CCs")

conn.commit()
print("\nVerificacao final:")
print("pessoa por mes:", conn.execute("SELECT mes_ref, count(*) FROM agrupador_pessoa GROUP BY mes_ref ORDER BY mes_ref").fetchall())
print("cc por mes:", conn.execute("SELECT mes_ref, count(*) FROM agrupador_cc GROUP BY mes_ref ORDER BY mes_ref").fetchall())
conn.close()
print("\nDONE!")
