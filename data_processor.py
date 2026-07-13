import pandas as pd
import os
import datetime

def load_and_process_data():
    file_path_clt = 'Base.xlsx'
    file_path_pj = 'PJ - CONTRATOS REAJUSTADOS.xlsx'
    
    if not os.path.exists(file_path_clt):
        return {"error": "Arquivo Base.xlsx não encontrado."}
        
    try:
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dados.db')

        # --- PROCESS CLT ---
        df_clt_clean = pd.DataFrame()
        clt_loaded_from_db = False
        
        if os.path.exists(db_path):
            import sqlite3
            conn = sqlite3.connect(db_path, timeout=15, check_same_thread=False)
            conn.execute('PRAGMA query_only=ON')
            try:
                clt_rows = conn.execute(
                    "SELECT centro_custo, matricula, nome, situacao, custo_total, total_rem, mes "
                    "FROM clt_registros"
                ).fetchall()
                
                if clt_rows:
                    df_clt_clean = pd.DataFrame(clt_rows, columns=['centro_custo', 'matricula', 'nome', 'situacao', 'custo_total', 'total_rem', 'mes'])
                    df_clt_clean['mes'] = pd.to_datetime(df_clt_clean['mes'], errors='coerce')
                    df_clt_clean['tipo_contrato'] = 'CLT'
                    clt_loaded_from_db = True
            except sqlite3.OperationalError:
                # Table might not exist yet
                pass
            finally:
                conn.close()

        if not clt_loaded_from_db and os.path.exists(file_path_clt):
            df_clt = pd.read_excel(file_path_clt, sheet_name='base', header=None, skiprows=1)
            
            df_clt_clean = pd.DataFrame({
                'centro_custo': df_clt[3].astype(str).str.strip(),
                'matricula': df_clt[4].astype(str).str.strip(),
                'nome': df_clt[5].astype(str).str.strip(),
                'situacao': pd.to_numeric(df_clt[34], errors='coerce').fillna(0),
                'custo_total': pd.to_numeric(df_clt[35], errors='coerce').fillna(0),
                'total_rem': pd.to_numeric(df_clt[13], errors='coerce').fillna(0),
                'mes': df_clt[36],
                'tipo_contrato': 'CLT'
            })
            
            df_clt_clean['mes'] = pd.to_datetime(df_clt_clean['mes'], errors='coerce')
            df_clt_clean.dropna(subset=['matricula', 'mes'], inplace=True)
            df_clt_clean = df_clt_clean[df_clt_clean['centro_custo'] != 'nan']
        
        # --- PROCESS PJ (Banco SQLite ou fallback para Excel) ---
        df_pj = pd.DataFrame()
        
        if os.path.exists(db_path):
            # Leitura do banco SQLite com timeout para evitar bloqueio
            import sqlite3
            conn = sqlite3.connect(db_path, timeout=15, check_same_thread=False)
            conn.execute('PRAGMA journal_mode=WAL')
            conn.execute('PRAGMA query_only=ON')
            pj_rows = conn.execute(
                "SELECT cnpj, centro_custo, razao_social, "
                "valor_jan_2026, valor_fev_2026, valor_mar_2026, valor_abr_2026, "
                "valor_mai_2026, valor_jun_2026, valor_jul_2026, valor_ago_2026, "
                "valor_set_2026, valor_out_2026, valor_nov_2026, valor_dez_2026 "
                "FROM pj_contratos WHERE ativo = 1"
            ).fetchall()
            conn.close()
            
            MES_COLS = [
                ('2026-01', 3), ('2026-02', 4), ('2026-03', 5), ('2026-04', 6),
                ('2026-05', 7), ('2026-06', 8), ('2026-07', 9), ('2026-08', 10),
                ('2026-09', 11), ('2026-10', 12), ('2026-11', 13), ('2026-12', 14),
            ]
            
            pj_records = []
            for row in pj_rows:
                cnpj = str(row[0]).strip()
                cc = str(row[1]).strip()
                razao = str(row[2]).strip() if row[2] else cnpj
                for mes_str, col_idx in MES_COLS:
                    valor = float(row[col_idx] or 0)
                    if valor > 0:
                        pj_records.append({
                            'centro_custo': cc,
                            'matricula': cnpj,
                            'nome': razao,
                            'situacao': 1,
                            'custo_total': valor,
                            'total_rem': valor,
                            'mes': pd.to_datetime(mes_str),
                            'tipo_contrato': 'PJ'
                        })
            
            if pj_records:
                df_pj = pd.DataFrame(pj_records)
                df_pj = df_pj[df_pj['centro_custo'] != 'nan']

        elif os.path.exists(file_path_pj):
            # Fallback: Excel (antes do seed)
            df_pj_raw = pd.read_excel(file_path_pj, sheet_name='PJS ATIVOS', skiprows=2)
            date_cols = [c for c in df_pj_raw.columns if isinstance(c, (pd.Timestamp, datetime.datetime))]
            
            if 'CNPJ' in df_pj_raw.columns and 'CENTRO DE CUSTO' in df_pj_raw.columns:
                df_pj_melt = pd.melt(df_pj_raw, id_vars=['CNPJ', 'CENTRO DE CUSTO'], value_vars=date_cols, var_name='mes', value_name='custo_total')
                df_pj_melt['custo_total'] = pd.to_numeric(df_pj_melt['custo_total'], errors='coerce').fillna(0)
                df_pj_melt = df_pj_melt[df_pj_melt['custo_total'] > 0]
                df_pj = pd.DataFrame({
                    'centro_custo': df_pj_melt['CENTRO DE CUSTO'].astype(str).str.strip(),
                    'matricula': df_pj_melt['CNPJ'].astype(str).str.strip(),
                    'situacao': 1,
                    'custo_total': df_pj_melt['custo_total'],
                    'total_rem': df_pj_melt['custo_total'],
                    'mes': pd.to_datetime(df_pj_melt['mes'], errors='coerce'),
                    'tipo_contrato': 'PJ'
                })
                df_pj.dropna(subset=['matricula', 'mes'], inplace=True)
                df_pj = df_pj[df_pj['centro_custo'] != 'nan']

        
        # --- COMBINE ---
        df_clean = pd.concat([df_clt_clean, df_pj], ignore_index=True)
        df_clean['mes_str'] = df_clean['mes'].dt.strftime('%Y-%m')
        
        # Remove Janeiro (2026-01)
        df_clean = df_clean[df_clean['mes_str'] != '2026-01'].copy()
        
        # Flags
        df_clean['sit_1'] = (df_clean['situacao'] == 1).astype(int)
        df_clean['sit_2'] = (df_clean['situacao'] == 2).astype(int)
        df_clean['sit_3'] = (df_clean['situacao'] == 3).astype(int)
        df_clean['is_clt'] = (df_clean['tipo_contrato'] == 'CLT').astype(int)
        df_clean['is_clt_ativo'] = ((df_clean['tipo_contrato'] == 'CLT') & (df_clean['situacao'] == 1)).astype(int)
        df_clean['is_pj'] = (df_clean['tipo_contrato'] == 'PJ').astype(int)
        
        # Auxiliar columns for aggregation
        df_clean['custo_clt'] = df_clean.apply(lambda row: row['custo_total'] if row['is_clt_ativo'] else 0, axis=1)
        df_clean['custo_pj'] = df_clean.apply(lambda row: row['custo_total'] if row['is_pj'] else 0, axis=1)
        # Fix custo_total to only include active clt and pj
        df_clean['custo_total'] = df_clean['custo_clt'] + df_clean['custo_pj']
        
        # --- LOAD AGRUPADORES FROM DB (indexed by mes_ref) ---
        # excecoes_by_mes: {mes_ref: {(identificador, tipo_contrato): row}}
        # cc_rules_by_mes: {mes_ref: {(centro_custo, tipo_contrato): row}}
        excecoes_by_mes = {}
        cc_rules_by_mes = {}
        metas_by_mes = {}
        meses_pessoa = []
        meses_cc = []
        meses_metas = []
        try:
            import sqlite3
            conn = sqlite3.connect(db_path, timeout=10)
            conn.row_factory = sqlite3.Row
            for r in conn.execute("SELECT * FROM agrupador_pessoa ORDER BY mes_ref").fetchall():
                m = str(r['mes_ref'])
                if m not in excecoes_by_mes:
                    excecoes_by_mes[m] = {}
                    meses_pessoa.append(m)
                excecoes_by_mes[m][(str(r['identificador']).strip(), str(r['tipo_contrato']).strip())] = r
            for r in conn.execute("SELECT * FROM agrupador_cc ORDER BY mes_ref").fetchall():
                m = str(r['mes_ref'])
                if m not in cc_rules_by_mes:
                    cc_rules_by_mes[m] = {}
                    meses_cc.append(m)
                cc_rules_by_mes[m][(str(r['centro_custo']).strip().lower(), str(r['tipo_contrato']).strip())] = r
            for r in conn.execute("SELECT * FROM meta_centro_custo ORDER BY mes_ref").fetchall():
                m = str(r['mes_ref'])
                if m not in metas_by_mes:
                    metas_by_mes[m] = {}
                    meses_metas.append(m)
                metas_by_mes[m][str(r['centro_custo']).strip().lower()] = int(r['meta_pessoas'])
            conn.close()
        except Exception:
            pass
        
        meses_pessoa_sorted = sorted(set(meses_pessoa))
        meses_cc_sorted = sorted(set(meses_cc))
        meses_metas_sorted = sorted(set(meses_metas))

        def _best_mes(mes_row, meses_sorted):
            """Retorna o mes disponivel mais recente <= mes_row, ou None."""
            candidatos = [m for m in meses_sorted if m <= mes_row]
            return candidatos[-1] if candidatos else (meses_sorted[0] if meses_sorted else None)

        def apply_agrupadores(row):
            mes_row = str(row['mes_str'])  # formato YYYY-MM
            # 1. Try Excecao do mês (ou fallback)
            best_m = _best_mes(mes_row, meses_pessoa_sorted)
            exc = excecoes_by_mes.get(best_m, {}).get((str(row['matricula']), row['tipo_contrato'])) if best_m else None
            if exc:
                return pd.Series([exc['agrupador1'], exc['agrupador2'], exc['agrupador3']])
            # 2. Try CC specific type
            best_mc = _best_mes(mes_row, meses_cc_sorted)
            cc_dict = cc_rules_by_mes.get(best_mc, {}) if best_mc else {}
            cc = str(row['centro_custo']).lower()
            cc_r = cc_dict.get((cc, row['tipo_contrato']))
            if cc_r:
                return pd.Series([cc_r['agrupador1'], cc_r['agrupador2'], cc_r['agrupador3']])
            # 3. Try CC TODOS
            cc_all = cc_dict.get((cc, 'TODOS'))
            if cc_all:
                return pd.Series([cc_all['agrupador1'], cc_all['agrupador2'], cc_all['agrupador3']])
            return pd.Series(['', '', ''])

        def check_inativo(row):
            mes_row = str(row['mes_str'])
            best_m = _best_mes(mes_row, meses_pessoa_sorted)
            exc = excecoes_by_mes.get(best_m, {}).get((str(row['matricula']), row['tipo_contrato'])) if best_m else None
            return bool(exc and exc['inativo'])

        df_clean[['agrupador1', 'agrupador2', 'agrupador3']] = df_clean.apply(apply_agrupadores, axis=1)
        df_clean['inativo'] = df_clean.apply(check_inativo, axis=1)

        # Filtra (remove) pessoas inativas antes das consolidações
        df_clean = df_clean[~df_clean['inativo']]
        
        # Replace Nones with empty string for clean grouping
        df_clean['agrupador1'] = df_clean['agrupador1'].fillna('')
        df_clean['agrupador2'] = df_clean['agrupador2'].fillna('')
        df_clean['agrupador3'] = df_clean['agrupador3'].fillna('')

        # Agrupamento por Mês, Centro de Custo e Agrupadores
        agrupado_centro = df_clean.groupby(['mes_str', 'centro_custo', 'agrupador1', 'agrupador2', 'agrupador3']).agg(
            qtd_pessoas=('matricula', 'count'),
            qtd_clt=('is_clt_ativo', 'sum'),
            qtd_pj=('is_pj', 'sum'),
            custo_total=('custo_total', 'sum'),
            custo_clt=('custo_clt', 'sum'),
            custo_pj=('custo_pj', 'sum'),
            sit_1=('sit_1', 'sum'),
            sit_2=('sit_2', 'sum'),
            sit_3=('sit_3', 'sum')
        ).reset_index()

        # Limita meses exibidos ao último mês com dados CLT
        # Isso evita que meses futuros (só com PJ) apareçam como padrão
        meses_clt = sorted(df_clt_clean['mes'].dt.strftime('%Y-%m').dropna().unique().tolist())
        ultimo_mes_clt = meses_clt[-1] if meses_clt else None
        
        todos_meses = sorted(df_clean['mes_str'].dropna().unique().tolist())
        if ultimo_mes_clt:
            meses_disponiveis = [m for m in todos_meses if m <= ultimo_mes_clt]
        else:
            meses_disponiveis = todos_meses
        

        # --- Histórico ---
        historico = {
            'meses': meses_disponiveis,
            'custo_total': [],
            'custo_clt': [],
            'custo_pj': [],
            'total_pessoas': [],
            'total_clt': [],
            'total_pj': [],
            'entradas': [],
            'saidas': [],
            'entradas_clt': [],
            'saidas_clt': [],
            'entradas_pj': [],
            'saidas_pj': [],
            'inss': [],
            'inss_clt': [],
            'inss_pj': [],
            'rescisao': [],
            'rescisao_clt': [],
            'rescisao_pj': []
        }
        
        matriculas_por_mes = {}
        matriculas_clt_por_mes = {}
        matriculas_pj_por_mes = {}
        for mes in meses_disponiveis:
            df_mes = df_clean[df_clean['mes_str'] == mes]
            matriculas_por_mes[mes] = set(df_mes['matricula'].unique())
            
            df_mes_clt = df_mes[df_mes['tipo_contrato'] == 'CLT']
            matriculas_clt_por_mes[mes] = set(df_mes_clt['matricula'].unique())
            
            df_mes_pj = df_mes[df_mes['tipo_contrato'] == 'PJ']
            matriculas_pj_por_mes[mes] = set(df_mes_pj['matricula'].unique())
            
            historico['total_pessoas'].append(len(matriculas_por_mes[mes]))
            historico['total_clt'].append(int(df_mes['is_clt'].sum()))
            historico['total_pj'].append(int(df_mes['is_pj'].sum()))
            
            historico['custo_total'].append(float(df_mes['custo_total'].sum()))
            historico['custo_clt'].append(float(df_mes['custo_clt'].sum()))
            historico['custo_pj'].append(float(df_mes['custo_pj'].sum()))
            
            historico['inss'].append(int((df_mes['situacao'] == 2).sum()))
            historico['inss_clt'].append(int((df_mes_clt['situacao'] == 2).sum()))
            historico['inss_pj'].append(int((df_mes_pj['situacao'] == 2).sum()))
            
            historico['rescisao'].append(int((df_mes['situacao'] == 3).sum()))
            historico['rescisao_clt'].append(int((df_mes_clt['situacao'] == 3).sum()))
            historico['rescisao_pj'].append(int((df_mes_pj['situacao'] == 3).sum()))
            
        for i, mes in enumerate(meses_disponiveis):
            if i == 0:
                historico['entradas'].append(0)
                historico['saidas'].append(0)
                historico['entradas_clt'].append(0)
                historico['saidas_clt'].append(0)
                historico['entradas_pj'].append(0)
                historico['saidas_pj'].append(0)
            else:
                mes_anterior = meses_disponiveis[i-1]
                
                mat_atual = matriculas_por_mes[mes]
                mat_anterior = matriculas_por_mes[mes_anterior]
                historico['entradas'].append(len(mat_atual - mat_anterior))
                historico['saidas'].append(len(mat_anterior - mat_atual))
                
                mat_clt_atual = matriculas_clt_por_mes[mes]
                mat_clt_anterior = matriculas_clt_por_mes[mes_anterior]
                historico['entradas_clt'].append(len(mat_clt_atual - mat_clt_anterior))
                historico['saidas_clt'].append(len(mat_clt_anterior - mat_clt_atual))
                
                mat_pj_atual = matriculas_pj_por_mes[mes]
                mat_pj_anterior = matriculas_pj_por_mes[mes_anterior]
                historico['entradas_pj'].append(len(mat_pj_atual - mat_pj_anterior))
                historico['saidas_pj'].append(len(mat_pj_anterior - mat_pj_atual))
        
        dados_por_mes = {}
        for mes in meses_disponiveis:
            df_mes_centro = agrupado_centro[agrupado_centro['mes_str'] == mes]
            centros = []
            
            for _, row in df_mes_centro.iterrows():
                cc = str(row['centro_custo']).strip().lower()
                best_m = _best_mes(mes, meses_metas_sorted)
                meta = metas_by_mes.get(best_m, {}).get(cc, 0) if best_m else 0

                centros.append({
                    'agrupador': row['centro_custo'],
                    'agrupador1': str(row['agrupador1']) if row['agrupador1'] else '',
                    'agrupador2': str(row['agrupador2']) if row['agrupador2'] else '',
                    'agrupador3': str(row['agrupador3']) if row['agrupador3'] else '',
                    'qtd_clt': int(row['qtd_clt']),
                    'qtd_pj': int(row['qtd_pj']),
                    'total_pessoas': int(row['qtd_clt']) + int(row['qtd_pj']),
                    'meta_pessoas': meta,
                    'custo_total': float(row['custo_total']),
                    'custo_clt': float(row['custo_clt']),
                    'custo_pj': float(row['custo_pj']),
                    'sit_1': int(row['sit_1']),
                    'sit_2': int(row['sit_2']),
                    'sit_3': int(row['sit_3'])
                })
                
            centros = sorted(centros, key=lambda x: x['custo_total'], reverse=True)
            
            dados_por_mes[mes] = {
                'resumo': {
                    'total_pessoas': sum([c['total_pessoas'] for c in centros]),
                    'custo_total': sum([c['custo_total'] for c in centros]),
                    'total_clt': sum([c['qtd_clt'] for c in centros]),
                    'total_pj': sum([c['qtd_pj'] for c in centros]),
                    'custo_clt': sum([c['custo_clt'] for c in centros]),
                    'custo_pj': sum([c['custo_pj'] for c in centros]),
                    'turnover_abs': 0
                },
                'centros': centros
            }
            
        # --- Histórico Detalhado (Visão 360) ---
        historico_detalhado = {'centros': {}, 'agrupadores3': {}}
        
        for agrupador in df_clean['centro_custo'].unique():
            df_g = df_clean[df_clean['centro_custo'] == agrupador]
            hist = {
                'meses': meses_disponiveis, 'custo_total': [], 'total_pessoas': [], 
                'entradas': [], 'saidas': [], 'inss': [], 'rescisao': [], 
                'pct_custo': [], 'pct_pessoas': [],
                'custo_clt': [], 'custo_pj': [], 'total_clt': [], 'total_pj': []
            }
            
            matriculas_ant = set()
            for i, mes in enumerate(meses_disponiveis):
                df_mes = df_g[df_g['mes_str'] == mes]
                mat_atual = set(df_mes['matricula'].unique())
                
                custo = float(df_mes['custo_total'].sum())
                pessoas = len(mat_atual)
                
                entradas = len(mat_atual - matriculas_ant) if i > 0 else 0
                saidas = len(matriculas_ant - mat_atual) if i > 0 else 0
                
                pct_c = (custo / historico['custo_total'][i] * 100) if historico['custo_total'][i] > 0 else 0
                pct_p = (pessoas / historico['total_pessoas'][i] * 100) if historico['total_pessoas'][i] > 0 else 0
                
                hist['custo_total'].append(custo)
                hist['total_pessoas'].append(pessoas)
                hist['inss'].append(int((df_mes['situacao'] == 2).sum()))
                hist['rescisao'].append(int((df_mes['situacao'] == 3).sum()))
                hist['entradas'].append(entradas)
                hist['saidas'].append(saidas)
                hist['pct_custo'].append(pct_c)
                hist['pct_pessoas'].append(pct_p)
                
                hist['custo_clt'].append(float(df_mes['custo_clt'].sum()))
                hist['custo_pj'].append(float(df_mes['custo_pj'].sum()))
                hist['total_clt'].append(int(df_mes['is_clt'].sum()))
                hist['total_pj'].append(int(df_mes['is_pj'].sum()))
                
                matriculas_ant = mat_atual
                
            historico_detalhado['centros'][agrupador] = hist

        for ag3 in df_clean['agrupador3'].unique():
            agrupador_name = ag3 if ag3 else 'Sem Classificação'
            df_g = df_clean[df_clean['agrupador3'] == ag3]
            hist = {
                'meses': meses_disponiveis, 'custo_total': [], 'total_pessoas': [], 
                'entradas': [], 'saidas': [], 'inss': [], 'rescisao': [], 
                'pct_custo': [], 'pct_pessoas': [],
                'custo_clt': [], 'custo_pj': [], 'total_clt': [], 'total_pj': []
            }
            
            pessoas = {}
            for index, row in df_g.iterrows():
                mat = str(row['matricula'])
                if mat not in pessoas:
                    pessoas[mat] = {
                        'nome': str(row['nome']), 
                        'matricula': mat, 
                        'tipo_contrato': str(row['tipo_contrato']).strip().lower(),
                        'salarios': {},
                        'remuneracoes': {}
                    }
                pessoas[mat]['salarios'][row['mes_str']] = float(row['custo_total'])
                pessoas[mat]['remuneracoes'][row['mes_str']] = float(row['total_rem'] if 'total_rem' in row and pd.notna(row['total_rem']) else row['custo_total'])
            hist['pessoas_hist'] = list(pessoas.values())
            
            matriculas_ant = set()
            for i, mes in enumerate(meses_disponiveis):
                df_mes = df_g[df_g['mes_str'] == mes]
                mat_atual = set(df_mes['matricula'].unique())
                
                custo = float(df_mes['custo_total'].sum())
                pessoas = len(mat_atual)
                
                entradas = len(mat_atual - matriculas_ant) if i > 0 else 0
                saidas = len(matriculas_ant - mat_atual) if i > 0 else 0
                
                pct_c = (custo / historico['custo_total'][i] * 100) if historico['custo_total'][i] > 0 else 0
                pct_p = (pessoas / historico['total_pessoas'][i] * 100) if historico['total_pessoas'][i] > 0 else 0
                
                hist['custo_total'].append(custo)
                hist['total_pessoas'].append(pessoas)
                hist['inss'].append(int((df_mes['situacao'] == 2).sum()))
                hist['rescisao'].append(int((df_mes['situacao'] == 3).sum()))
                hist['entradas'].append(entradas)
                hist['saidas'].append(saidas)
                hist['pct_custo'].append(pct_c)
                hist['pct_pessoas'].append(pct_p)
                
                hist['custo_clt'].append(float(df_mes['custo_clt'].sum()))
                hist['custo_pj'].append(float(df_mes['custo_pj'].sum()))
                hist['total_clt'].append(int(df_mes['is_clt'].sum()))
                hist['total_pj'].append(int(df_mes['is_pj'].sum()))
                
                matriculas_ant = mat_atual
                
            historico_detalhado['agrupadores3'][agrupador_name] = hist
        
        hist_total = {
            'meses': meses_disponiveis, 'custo_total': [], 'total_pessoas': [], 
            'entradas': [], 'saidas': [], 'inss': [], 'rescisao': [], 
            'pct_custo': [], 'pct_pessoas': [],
            'custo_clt': [], 'custo_pj': [], 'total_clt': [], 'total_pj': []
        }
        
        pessoas_total = {}
        for index, row in df_clean.iterrows():
            mat = str(row['matricula'])
            if mat not in pessoas_total:
                pessoas_total[mat] = {
                    'nome': str(row['nome']), 
                    'matricula': mat, 
                    'tipo_contrato': str(row['tipo_contrato']).strip().lower(),
                    'salarios': {},
                    'remuneracoes': {}
                }
            pessoas_total[mat]['salarios'][row['mes_str']] = float(row['custo_total'])
            pessoas_total[mat]['remuneracoes'][row['mes_str']] = float(row['total_rem'] if 'total_rem' in row and pd.notna(row['total_rem']) else row['custo_total'])
        hist_total['pessoas_hist'] = list(pessoas_total.values())
        
        matriculas_ant_total = set()
        for i, mes in enumerate(meses_disponiveis):
            df_mes = df_clean[df_clean['mes_str'] == mes]
            mat_atual_total = set(df_mes['matricula'].unique())
            
            custo = float(df_mes['custo_total'].sum())
            pessoas_qtd = len(mat_atual_total)
            
            entradas = len(mat_atual_total - matriculas_ant_total) if i > 0 else 0
            saidas = len(matriculas_ant_total - mat_atual_total) if i > 0 else 0
            
            hist_total['custo_total'].append(custo)
            hist_total['total_pessoas'].append(pessoas_qtd)
            hist_total['inss'].append(int((df_mes['situacao'] == 2).sum()))
            hist_total['rescisao'].append(int((df_mes['situacao'] == 3).sum()))
            hist_total['entradas'].append(entradas)
            hist_total['saidas'].append(saidas)
            
            hist_total['custo_clt'].append(float(df_mes['custo_clt'].sum()))
            hist_total['custo_pj'].append(float(df_mes['custo_pj'].sum()))
            hist_total['total_clt'].append(int(df_mes['is_clt'].sum()))
            hist_total['total_pj'].append(int(df_mes['is_pj'].sum()))
            
            matriculas_ant_total = mat_atual_total
            
        historico_detalhado['agrupadores3']['TOTAL GERAL'] = hist_total
        
        return {
            'meses': meses_disponiveis,
            'dados': dados_por_mes,
            'historico': historico,
            'historico_detalhado': historico_detalhado
        }
        
    except Exception as e:
        import traceback
        return {"error": str(e), "traceback": traceback.format_exc()}

if __name__ == '__main__':
    print(load_and_process_data())
