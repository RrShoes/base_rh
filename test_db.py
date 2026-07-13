import os
from app import app
import json

with app.test_client() as client:
    # Bypass @login_required by mocking or just checking the function directly
    from app import api_pessoas_todas
    
    # We can invoke api_pessoas_todas directly by setting up a request context
    with app.test_request_context('/api/pessoas/todas'):
        # Because of @login_required, we might need to bypass it.
        # But wait, does @login_required just return 401?
        pass

# Actually, I can just call the sqlite3 code from api_pessoas_todas directly:
import sqlite3
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dados.db')
conn = sqlite3.connect(db_path, timeout=10)
conn.row_factory = sqlite3.Row

clt_rows = conn.execute("""
    SELECT matricula,
            MAX(nome) AS nome,
            MAX(centro_custo) AS centro_custo
    FROM clt_registros
    GROUP BY matricula
    ORDER BY nome, matricula
""").fetchall()

print("CLT rows fetched:", len(clt_rows))

pj_rows = conn.execute("""
    SELECT cnpj, nome, centro_custo
    FROM pj_contratos
    WHERE ativo = 1
    ORDER BY nome
""").fetchall()

print("PJ rows fetched:", len(pj_rows))
conn.close()
