import sqlite3
conn = sqlite3.connect('dados.db')
conn.row_factory = sqlite3.Row
row = conn.execute('SELECT mes FROM clt_registros LIMIT 1').fetchone()
print('mes sample:', row['mes'])
print('mes type:', type(row['mes']))
rows = conn.execute("SELECT DISTINCT strftime('%Y-%m', mes) as m FROM clt_registros ORDER BY m").fetchall()
print('meses distintos:', [r['m'] for r in rows])
# Count by month
counts = conn.execute("SELECT strftime('%Y-%m', mes) as m, count(DISTINCT matricula) as n FROM clt_registros GROUP BY m ORDER BY m").fetchall()
print('pessoas por mes:')
for r in counts:
    print(f"  {r['m']}: {r['n']} pessoas")
conn.close()
