import os
from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, PjContrato, CltRegistro, AgrupadorCC, AgrupadorPessoa, OpcaoAgrupador
from data_processor import load_and_process_data

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.config['SECRET_KEY'] = 'rh-via-uno-secret-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(BASE_DIR, "dados.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'connect_args': {'check_same_thread': False, 'timeout': 20},
}
app.config['TEMPLATES_AUTO_RELOAD'] = True

# Init extensions
db.init_app(app)

# Ativar WAL mode no SQLite para permitir leituras simultâneas
from sqlalchemy import event
from sqlalchemy.engine import Engine
import sqlite3

@event.listens_for(Engine, 'connect')
def set_sqlite_pragma(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute('PRAGMA journal_mode=WAL')
        cursor.execute('PRAGMA busy_timeout=10000')
        cursor.close()

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Por favor, faça login para acessar esta página.'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ─────────────────────────────────────────
# DASHBOARD (público)
# ─────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/dados')
def api_dados():
    dados = load_and_process_data()

    if "error" in dados:
        return jsonify({"success": False, "error": dados["error"]}), 500

    meses = dados.get("meses", [])
    if len(meses) > 1:
        for i in range(1, len(meses)):
            mes_atual = meses[i]
            mes_anterior = meses[i - 1]
            pessoas_atual = dados["dados"][mes_atual]["resumo"]["total_pessoas"]
            pessoas_anterior = dados["dados"][mes_anterior]["resumo"]["total_pessoas"]
            dados["dados"][mes_atual]["resumo"]["turnover_abs"] = pessoas_atual - pessoas_anterior

    show_salaries = current_user.is_authenticated
    dados['show_salaries'] = show_salaries
    
    # K-anonymity and Individual Salary Obfuscation (Apenas para não logados)
    if not show_salaries:
        for group_type in ["centros_custo", "agrupadores1", "agrupadores2", "agrupadores3", "centros"]:
            if "dados" in dados:
                for mes, d_mes in dados["dados"].items():
                    if group_type in d_mes:
                        # Para centros, pode ser uma lista. Se for lista, iteramos de forma diferente.
                        if group_type == "centros":
                            for item in d_mes["centros"]:
                                qtd = item.get("total_pessoas", 0)
                                custo = item.get("custo_total", 0)
                                if (0 < qtd < 10) or custo == 0:
                                    item["custo_total"] = -1
                                    item["custo_clt"] = -1
                                    item["custo_pj"] = -1
                        else:
                            for ag, res in d_mes[group_type].items():
                                qtd = res.get("qtd_pessoas", 0)
                                custo = res.get("custo_total", 0)
                                if (0 < qtd < 10) or custo == 0:
                                    res["custo_total"] = -1
                                    res["custo_clt"] = -1
                                    res["custo_pj"] = -1

    if "historico_detalhado" in dados:
        for group_type in ["centros", "agrupadores3"]:
            if group_type in dados["historico_detalhado"]:
                for ag, hist in dados["historico_detalhado"][group_type].items():
                    # K-Anonymity para os graficos e arrays do historico
                    if not show_salaries:
                        for i, qtd in enumerate(hist.get("total_pessoas", [])):
                            custo = hist.get("custo_total", [])[i] if "custo_total" in hist and i < len(hist["custo_total"]) else 0
                            if (0 < qtd < 10) or custo == 0:
                                if "custo_total" in hist and i < len(hist["custo_total"]): hist["custo_total"][i] = -1
                                if "custo_clt" in hist and i < len(hist["custo_clt"]): hist["custo_clt"][i] = -1
                                if "custo_pj" in hist and i < len(hist["custo_pj"]): hist["custo_pj"][i] = -1
                                if "pct_custo" in hist and i < len(hist["pct_custo"]): hist["pct_custo"][i] = -1

                    # Ofuscacao de salarios individuais se nao estiver logado
                    if not show_salaries and "pessoas_hist" in hist:
                        for p in hist["pessoas_hist"]:
                            for m in p.get("salarios", {}):
                                p["salarios"][m] = 0
                            for m in p.get("remuneracoes", {}):
                                p["remuneracoes"][m] = 0

    return jsonify({"success": True, "data": dados})


# ─────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user, remember=True)
            return redirect(url_for('index'))
        flash('Usuário ou senha incorretos.', 'error')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


from functools import wraps
from flask import abort

def editor_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Para acessar esta página é necessário fazer login.', 'error')
            return redirect(url_for('login'))
        if not current_user.is_editor:
            flash('Acesso negado. Apenas editores podem acessar esta página.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function


# ─────────────────────────────────────────
# ADMIN – CRUD PJs
# ─────────────────────────────────────────

@app.route('/admin')
@editor_required
def admin():
    search = request.args.get('q', '').strip()
    query = PjContrato.query
    if search:
        query = query.filter(
            PjContrato.nome.ilike(f'%{search}%') |
            PjContrato.cnpj.ilike(f'%{search}%') |
            PjContrato.centro_custo.ilike(f'%{search}%')
        )
    pjs = query.order_by(PjContrato.nome).all()
    return render_template('admin.html', pjs=pjs, search=search)

@app.route('/admin/usuarios', methods=['GET', 'POST'])
@editor_required
def admin_usuarios():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        role = request.form.get('role', 'viewer')
        
        if not username or not password:
            flash('Usuário e senha são obrigatórios.', 'error')
        elif User.query.filter_by(username=username).first():
            flash('Este nome de usuário já existe.', 'error')
        else:
            new_user = User(username=username, role=role)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            flash(f'Usuário {username} criado com sucesso!', 'success')
            return redirect(url_for('admin_usuarios'))
            
    users = User.query.order_by(User.username).all()
    return render_template('usuarios.html', users=users)


@app.route('/admin/usuarios/editar/<int:user_id>', methods=['POST'])
@editor_required
def admin_usuario_editar(user_id):
    user = User.query.get_or_404(user_id)
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    role = request.form.get('role', 'viewer')

    if not username:
        flash('Nome de usuário é obrigatório.', 'error')
    else:
        existing = User.query.filter_by(username=username).first()
        if existing and existing.id != user_id:
            flash('Este nome de usuário já existe.', 'error')
        else:
            user.username = username
            user.role = role
            if password:
                user.set_password(password)
            db.session.commit()
            flash(f'Usuário {username} atualizado com sucesso!', 'success')
            
    return redirect(url_for('admin_usuarios'))


@app.route('/admin/usuarios/excluir/<int:user_id>', methods=['POST'])
@editor_required
def admin_usuario_excluir(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('Você não pode excluir a si mesmo.', 'error')
    else:
        username = user.username
        db.session.delete(user)
        db.session.commit()
        flash(f'Usuário {username} excluído com sucesso.', 'success')
        
    return redirect(url_for('admin_usuarios'))


@app.route('/admin/pj/novo', methods=['GET', 'POST'])
@editor_required
def pj_novo():
    if request.method == 'POST':
        cnpj = request.form.get('cnpj', '').strip()
        if PjContrato.query.filter_by(cnpj=cnpj).first():
            flash('CNPJ já cadastrado.', 'error')
            return render_template('pj_form.html', pj=None, title='Novo PJ')

        pj = PjContrato()
        _populate_pj(pj, request.form)
        db.session.add(pj)
        db.session.commit()
        flash(f'PJ "{pj.nome}" cadastrado com sucesso!', 'success')
        return redirect(url_for('admin'))

    return render_template('pj_form.html', pj=None, title='Novo PJ')


@app.route('/admin/pj/editar/<int:pj_id>', methods=['GET', 'POST'])
@editor_required
def pj_editar(pj_id):
    pj = PjContrato.query.get_or_404(pj_id)

    if request.method == 'POST':
        _populate_pj(pj, request.form)
        db.session.commit()
        flash(f'PJ "{pj.nome}" atualizado com sucesso!', 'success')
        return redirect(url_for('admin'))

    return render_template('pj_form.html', pj=pj, title=f'Editar: {pj.nome}')


@app.route('/admin/pj/excluir/<int:pj_id>', methods=['POST'])
@editor_required
def pj_excluir(pj_id):
    pj = PjContrato.query.get_or_404(pj_id)
    nome = pj.nome
    db.session.delete(pj)
    db.session.commit()
    flash(f'PJ "{nome}" removido.', 'success')
    return redirect(url_for('admin'))


def _populate_pj(pj, form):
    from datetime import date

    def parse_date(v):
        try:
            return date.fromisoformat(v) if v else None
        except Exception:
            return None

    def parse_float(v):
        try:
            return float(str(v).replace(',', '.')) if v else 0.0
        except Exception:
            return 0.0

    pj.nome = form.get('nome', '').strip()
    pj.cnpj = form.get('cnpj', '').strip()
    pj.razao_social = form.get('razao_social', '').strip()
    pj.cargo = form.get('cargo', '').strip()
    pj.centro_custo = form.get('centro_custo', '').strip()
    pj.data_inicio = parse_date(form.get('data_inicio'))
    pj.data_encerramento = parse_date(form.get('data_encerramento'))
    pj.observacoes = form.get('observacoes', '').strip()
    pj.ativo = form.get('ativo') == 'on'
    pj.valor_2025 = parse_float(form.get('valor_2025'))
    pj.valor_jan_2026 = parse_float(form.get('valor_jan_2026'))
    pj.valor_fev_2026 = parse_float(form.get('valor_fev_2026'))
    pj.valor_mar_2026 = parse_float(form.get('valor_mar_2026'))
    pj.valor_abr_2026 = parse_float(form.get('valor_abr_2026'))
    pj.valor_mai_2026 = parse_float(form.get('valor_mai_2026'))
    pj.valor_jun_2026 = parse_float(form.get('valor_jun_2026'))
    pj.valor_jul_2026 = parse_float(form.get('valor_jul_2026'))
    pj.valor_ago_2026 = parse_float(form.get('valor_ago_2026'))
    pj.valor_set_2026 = parse_float(form.get('valor_set_2026'))
    pj.valor_out_2026 = parse_float(form.get('valor_out_2026'))
    pj.valor_nov_2026 = parse_float(form.get('valor_nov_2026'))
    pj.valor_dez_2026 = parse_float(form.get('valor_dez_2026'))




# ─────────────────────────────────────────
# ADMIN – AGRUPADORES (Configurações)
# ─────────────────────────────────────────

@app.route('/admin/agrupadores')
@editor_required
def agrupadores():
    return render_template('agrupadores.html')


# --- Opções de Agrupadores (Cadastros Base) ---

@app.route('/api/opcoes_agrupador', methods=['GET'])
@editor_required
def api_opcoes_agrupador_list():
    grupo = request.args.get('grupo', type=int)
    query = OpcaoAgrupador.query
    if grupo:
        query = query.filter_by(grupo=grupo)
    registros = query.order_by(OpcaoAgrupador.grupo, OpcaoAgrupador.nome).all()
    return jsonify({'success': True, 'data': [r.to_dict() for r in registros]})

@app.route('/api/opcoes_agrupador', methods=['POST'])
@editor_required
def api_opcoes_agrupador_create():
    data = request.json
    grupo = data.get('grupo')
    nome = (data.get('nome') or '').strip().upper()
    if not grupo or not nome:
        return jsonify({'success': False, 'error': 'Grupo e nome são obrigatórios'}), 400
    if OpcaoAgrupador.query.filter_by(grupo=grupo, nome=nome).first():
        return jsonify({'success': False, 'error': 'Esta opção já existe para este grupo.'}), 400
    
    opcao = OpcaoAgrupador(grupo=grupo, nome=nome)
    db.session.add(opcao)
    db.session.commit()
    return jsonify({'success': True, 'data': opcao.to_dict()})

@app.route('/api/opcoes_agrupador/<int:opcao_id>', methods=['PUT'])
@editor_required
def api_opcoes_agrupador_edit(opcao_id):
    opcao = OpcaoAgrupador.query.get_or_404(opcao_id)
    data = request.json
    novo_nome = (data.get('nome') or '').strip().upper()
    if not novo_nome:
        return jsonify({'success': False, 'error': 'Nome é obrigatório'}), 400
    if OpcaoAgrupador.query.filter_by(grupo=opcao.grupo, nome=novo_nome).first() and opcao.nome != novo_nome:
        return jsonify({'success': False, 'error': 'Esta opção já existe para este grupo.'}), 400
    
    opcao.nome = novo_nome
    db.session.commit()
    return jsonify({'success': True, 'data': opcao.to_dict()})

@app.route('/api/opcoes_agrupador/<int:opcao_id>', methods=['DELETE'])
@editor_required
def api_opcoes_agrupador_delete(opcao_id):
    opcao = OpcaoAgrupador.query.get_or_404(opcao_id)
    db.session.delete(opcao)
    db.session.commit()
    return jsonify({'success': True})


# --- Centro de Custo ---

@app.route('/api/agrupadores/cc', methods=['GET'])
@editor_required
def api_agrupadores_cc_list():
    tipo = request.args.get('tipo', '')
    mes = request.args.get('mes', '2026-06')
    query = AgrupadorCC.query.filter_by(mes_ref=mes)
    if tipo:
        query = query.filter(AgrupadorCC.tipo_contrato == tipo)
    registros = query.order_by(AgrupadorCC.tipo_contrato, AgrupadorCC.centro_custo).all()
    return jsonify({'success': True, 'data': [r.to_dict() for r in registros]})


@app.route('/api/agrupadores/cc/bulk', methods=['POST'])
@editor_required
def api_agrupadores_cc_bulk():
    """Salva múltiplas regras de CC em lote (upsert)."""
    items = request.json.get('items', [])
    mes = request.json.get('mes_ref', '2026-06')
    try:
        for item in items:
            cc = item.get('centro_custo', '').strip()
            tipo = item.get('tipo_contrato', 'TODOS').strip()
            if not cc:
                continue
            reg = AgrupadorCC.query.filter_by(centro_custo=cc, tipo_contrato=tipo, mes_ref=mes).first()
            if reg:
                reg.agrupador1 = item.get('agrupador1') or None
                reg.agrupador2 = item.get('agrupador2') or None
                reg.agrupador3 = item.get('agrupador3') or None
            else:
                db.session.add(AgrupadorCC(
                    centro_custo=cc,
                    tipo_contrato=tipo,
                    mes_ref=mes,
                    agrupador1=item.get('agrupador1') or None,
                    agrupador2=item.get('agrupador2') or None,
                    agrupador3=item.get('agrupador3') or None,
                ))
        db.session.commit()
        return jsonify({'success': True, 'saved': len(items)})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/agrupadores/cc/<int:reg_id>', methods=['DELETE'])
@editor_required
def api_agrupadores_cc_delete(reg_id):
    reg = AgrupadorCC.query.get_or_404(reg_id)
    db.session.delete(reg)
    db.session.commit()
    return jsonify({'success': True})


# --- Pessoas (Exceções individuais) ---

@app.route('/api/agrupadores/pessoas', methods=['GET'])
@editor_required
def api_agrupadores_pessoas_list():
    q = request.args.get('q', '').strip()
    tipo = request.args.get('tipo', '')
    query = AgrupadorPessoa.query
    if q:
        query = query.filter(
            AgrupadorPessoa.nome.ilike(f'%{q}%') |
            AgrupadorPessoa.identificador.ilike(f'%{q}%') |
            AgrupadorPessoa.centro_custo.ilike(f'%{q}%')
        )
    if tipo:
        query = query.filter(AgrupadorPessoa.tipo_contrato == tipo)
    registros = query.order_by(AgrupadorPessoa.tipo_contrato, AgrupadorPessoa.nome).all()
    return jsonify({'success': True, 'data': [r.to_dict() for r in registros]})


@app.route('/api/agrupadores/pessoa', methods=['POST'])
@editor_required
def api_agrupadores_pessoa_save():
    data = request.json
    identificador = (data.get('identificador') or '').strip()
    tipo = (data.get('tipo_contrato') or '').strip()
    mes = (data.get('mes_ref') or '2026-06').strip()
    if not identificador or not tipo:
        return jsonify({'success': False, 'error': 'identificador e tipo_contrato são obrigatórios'}), 400

    reg = AgrupadorPessoa.query.filter_by(identificador=identificador, tipo_contrato=tipo, mes_ref=mes).first()
    if reg:
        reg.nome = data.get('nome') or reg.nome
        reg.centro_custo = data.get('centro_custo') or reg.centro_custo
        reg.agrupador1 = data.get('agrupador1') or None
        reg.agrupador2 = data.get('agrupador2') or None
        reg.agrupador3 = data.get('agrupador3') or None
        if 'inativo' in data:
            reg.inativo = bool(data.get('inativo'))
    else:
        reg = AgrupadorPessoa(
            identificador=identificador,
            tipo_contrato=tipo,
            mes_ref=mes,
            nome=data.get('nome') or '',
            centro_custo=data.get('centro_custo') or '',
            agrupador1=data.get('agrupador1') or None,
            agrupador2=data.get('agrupador2') or None,
            agrupador3=data.get('agrupador3') or None,
            inativo=bool(data.get('inativo', False)),
        )
        db.session.add(reg)

    try:
        db.session.commit()
        return jsonify({'success': True, 'data': reg.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/agrupadores/pessoa/<int:reg_id>', methods=['DELETE'])
@editor_required
def api_agrupadores_pessoa_delete(reg_id):
    reg = AgrupadorPessoa.query.get_or_404(reg_id)
    db.session.delete(reg)
    db.session.commit()
    return jsonify({'success': True})


@app.route('/api/agrupadores/copiar-mes', methods=['POST'])
@editor_required
def api_agrupadores_copiar_mes():
    """Copia regras de um mês para outro (pessoa e/ou CC). Nao sobrescreve registros ja existentes."""
    data = request.json
    mes_origem = (data.get('mes_origem') or '').strip()
    mes_destino = (data.get('mes_destino') or '').strip()
    tipo = data.get('tipo', 'ambos')  # 'pessoa', 'cc', 'ambos'
    if not mes_origem or not mes_destino:
        return jsonify({'success': False, 'error': 'mes_origem e mes_destino são obrigatórios'}), 400

    copiadas_pessoa = 0
    copiadas_cc = 0
    try:
        if tipo in ('pessoa', 'ambos'):
            for reg in AgrupadorPessoa.query.filter_by(mes_ref=mes_origem).all():
                existe = AgrupadorPessoa.query.filter_by(
                    identificador=reg.identificador, tipo_contrato=reg.tipo_contrato, mes_ref=mes_destino
                ).first()
                if not existe:
                    db.session.add(AgrupadorPessoa(
                        identificador=reg.identificador, tipo_contrato=reg.tipo_contrato,
                        mes_ref=mes_destino, nome=reg.nome, centro_custo=reg.centro_custo,
                        agrupador1=reg.agrupador1, agrupador2=reg.agrupador2, agrupador3=reg.agrupador3,
                        inativo=reg.inativo
                    ))
                    copiadas_pessoa += 1

        if tipo in ('cc', 'ambos'):
            for reg in AgrupadorCC.query.filter_by(mes_ref=mes_origem).all():
                existe = AgrupadorCC.query.filter_by(
                    centro_custo=reg.centro_custo, tipo_contrato=reg.tipo_contrato, mes_ref=mes_destino
                ).first()
                if not existe:
                    db.session.add(AgrupadorCC(
                        centro_custo=reg.centro_custo, tipo_contrato=reg.tipo_contrato,
                        mes_ref=mes_destino, agrupador1=reg.agrupador1,
                        agrupador2=reg.agrupador2, agrupador3=reg.agrupador3
                    ))
                    copiadas_cc += 1

        db.session.commit()
        return jsonify({'success': True, 'copiadas_pessoa': copiadas_pessoa, 'copiadas_cc': copiadas_cc})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/pessoas/disponiveis')
@editor_required
def api_pessoas_disponiveis():
    """Lista todas as pessoas únicas (CLT + PJ) com seus CCs mais recentes para autocomplete."""
    import sqlite3
    db_path = os.path.join(BASE_DIR, 'dados.db')
    pessoas = []
    try:
        conn = sqlite3.connect(db_path, timeout=10)
        conn.execute('PRAGMA query_only=ON')

        # CLT: pegar matrícula + nome (último mês disponível por matrícula)
        clt_rows = conn.execute("""
            SELECT matricula, MAX(nome) AS nome, centro_custo
            FROM clt_registros
            GROUP BY matricula
            ORDER BY matricula
        """).fetchall()
        for row in clt_rows:
            pessoas.append({
                'identificador': str(row[0]).strip(),
                'nome': str(row[1] or row[0]).strip(),
                'centro_custo': str(row[2] or '').strip(),
                'tipo_contrato': 'CLT'
            })

        # PJ: cnpj + nome
        pj_rows = conn.execute("""
            SELECT cnpj, nome, centro_custo FROM pj_contratos WHERE ativo = 1 ORDER BY nome
        """).fetchall()
        for row in pj_rows:
            pessoas.append({
                'identificador': str(row[0]).strip(),
                'nome': str(row[1] or '').strip(),
                'centro_custo': str(row[2] or '').strip(),
                'tipo_contrato': 'PJ'
            })

        conn.close()
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

    return jsonify({'success': True, 'data': pessoas})



@app.route('/api/pessoas/todas')
@editor_required
def api_pessoas_todas():
    """
    Lista todas as pessoas (CLT + PJ) com seus agrupadores efetivos.
    Precedência: AgrupadorPessoa (exceção individual) > AgrupadorCC (regra do CC) > vazio
    Suporta filtros: q (nome/matrícula), tipo_contrato, centro_custo
    """
    import sqlite3
    q       = request.args.get('q', '').strip().lower()
    tipo    = request.args.get('tipo', '').strip()
    cc_fil  = request.args.get('cc', '').strip().lower()
    mes     = request.args.get('mes', '2026-06').strip()
    ag1_fil = request.args.get('ag1', '').strip().lower()
    ag2_fil = request.args.get('ag2', '').strip().lower()
    ag3_fil = request.args.get('ag3', '').strip().lower()

    db_path = os.path.join(BASE_DIR, 'dados.db')
    pessoas = []

    try:
        conn = sqlite3.connect(db_path, timeout=10)
        conn.row_factory = sqlite3.Row

        # -- CLT: pessoas do mês selecionado (filtradas pelo mes_ref) --
        clt_rows = conn.execute("""
            SELECT matricula,
                   MAX(nome) AS nome,
                   MAX(centro_custo) AS centro_custo
            FROM clt_registros
            WHERE strftime('%Y-%m', mes) = ?
            GROUP BY matricula
            ORDER BY nome
        """, (mes,)).fetchall()
        for row in clt_rows:
            pessoas.append({
                'identificador': str(row['matricula'] or '').strip(),
                'nome':          str(row['nome'] or row['matricula'] or '').strip(),
                'centro_custo':  str(row['centro_custo'] or '').strip(),
                'tipo_contrato': 'CLT',
            })

        # -- PJ ativos --
        pj_rows = conn.execute("""
            SELECT cnpj, nome, centro_custo
            FROM pj_contratos
            WHERE ativo = 1
            ORDER BY nome
        """).fetchall()
        for row in pj_rows:
            pessoas.append({
                'identificador': str(row['cnpj'] or '').strip(),
                'nome':          str(row['nome'] or '').strip(),
                'centro_custo':  str(row['centro_custo'] or '').strip(),
                'tipo_contrato': 'PJ',
            })

        conn.close()
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

    # Índice de exceções individuais para o mês: (identificador, tipo_contrato) → AgrupadorPessoa
    # Fallback: usa o mês mais recente disponível anterior ao mês pedido
    def _get_excecoes_para_mes(mes_pedido):
        # Tenta o mês exato primeiro
        rows = AgrupadorPessoa.query.filter_by(mes_ref=mes_pedido).all()
        if rows:
            return {(r.identificador, r.tipo_contrato): r for r in rows}
        # Fallback: pega o mês mais recente anterior
        meses_disponiveis = db.session.query(AgrupadorPessoa.mes_ref).distinct().order_by(AgrupadorPessoa.mes_ref.desc()).all()
        for (m,) in meses_disponiveis:
            if m <= mes_pedido:
                rows = AgrupadorPessoa.query.filter_by(mes_ref=m).all()
                return {(r.identificador, r.tipo_contrato): r for r in rows}
        return {}

    def _get_cc_rules_para_mes(mes_pedido):
        rows = AgrupadorCC.query.filter_by(mes_ref=mes_pedido).all()
        if rows:
            d = {}
            for r in rows: d[(r.centro_custo, r.tipo_contrato)] = r
            return d
        meses_disponiveis = db.session.query(AgrupadorCC.mes_ref).distinct().order_by(AgrupadorCC.mes_ref.desc()).all()
        for (m,) in meses_disponiveis:
            if m <= mes_pedido:
                rows = AgrupadorCC.query.filter_by(mes_ref=m).all()
                d = {}
                for r in rows: d[(r.centro_custo, r.tipo_contrato)] = r
                return d
        return {}

    excecoes = _get_excecoes_para_mes(mes)

    # Índice de regras de CC para o mês
    cc_rules = _get_cc_rules_para_mes(mes)

    result = []
    for p in pessoas:
        # Aplicar filtros basicos
        if tipo and p['tipo_contrato'] != tipo:
            continue
        if cc_fil and cc_fil not in p['centro_custo'].lower():
            continue
        if q and q not in p['nome'].lower() and q not in p['identificador'].lower():
            continue

        exc = excecoes.get((p['identificador'], p['tipo_contrato']))
        cc_rule = cc_rules.get((p['centro_custo'], p['tipo_contrato'])) or \
                  cc_rules.get((p['centro_custo'], 'TODOS'))

        # Agrupadores efetivos (exceção > regra CC > None)
        agrupador1 = exc.agrupador1 if exc else (cc_rule.agrupador1 if cc_rule else None)
        agrupador2 = exc.agrupador2 if exc else (cc_rule.agrupador2 if cc_rule else None)
        agrupador3 = exc.agrupador3 if exc else (cc_rule.agrupador3 if cc_rule else None)
        
        # Filtros de Agrupador
        if ag1_fil and (not agrupador1 or agrupador1.lower() != ag1_fil): continue
        if ag2_fil and (not agrupador2 or agrupador2.lower() != ag2_fil): continue
        if ag3_fil and (not agrupador3 or agrupador3.lower() != ag3_fil): continue

        result.append({
            'identificador':  p['identificador'],
            'nome':           p['nome'],
            'centro_custo':   p['centro_custo'],
            'tipo_contrato':  p['tipo_contrato'],
            # Se tem exceção individual
            'tem_excecao':    exc is not None,
            'excecao_id':     exc.id if exc else None,
            'agrupador1':     agrupador1,
            'agrupador2':     agrupador2,
            'agrupador3':     agrupador3,
            # Origem dos dados (para mostrar ao usuário)
            'origem':         'excecao' if exc else ('cc' if cc_rule else 'sem_regra'),
            'inativo':        exc.inativo if exc else False,
        })

    return jsonify({'success': True, 'data': result, 'total': len(result)})


@app.route('/api/meses-disponiveis')
@editor_required
def api_meses_disponiveis():
    """Retorna lista de meses com dados CLT disponíveis (formato YYYY-MM)."""
    import sqlite3
    db_path = os.path.join(BASE_DIR, 'dados.db')
    try:
        conn = sqlite3.connect(db_path, timeout=10)
        rows = conn.execute(
            "SELECT DISTINCT strftime('%Y-%m', mes) as m FROM clt_registros ORDER BY m"
        ).fetchall()
        conn.close()
        meses = [r[0] for r in rows if r[0]]
        return jsonify({'success': True, 'data': meses})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/pessoas/centros')
@editor_required
def api_pessoas_centros():
    """Retorna lista de centros de custo únicos para popular o filtro dropdown."""
    import sqlite3
    db_path = os.path.join(BASE_DIR, 'dados.db')
    centros = set()
    try:
        conn = sqlite3.connect(db_path, timeout=10)
        for row in conn.execute("SELECT DISTINCT centro_custo FROM clt_registros WHERE centro_custo IS NOT NULL ORDER BY centro_custo").fetchall():
            centros.add(str(row[0]).strip())
        for row in conn.execute("SELECT DISTINCT centro_custo FROM pj_contratos WHERE ativo=1 AND centro_custo IS NOT NULL ORDER BY centro_custo").fetchall():
            centros.add(str(row[0]).strip())
        conn.close()
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    return jsonify({'success': True, 'data': sorted(centros)})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5062, debug=True)
