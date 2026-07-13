from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='viewer')  # 'editor' or 'viewer'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
        
    @property
    def is_editor(self):
        return self.role == 'editor'


class PjContrato(db.Model):
    __tablename__ = 'pj_contratos'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), nullable=False)
    cnpj = db.Column(db.String(20), unique=True, nullable=False)
    razao_social = db.Column(db.String(200))
    data_inicio = db.Column(db.Date)
    data_encerramento = db.Column(db.Date)
    cargo = db.Column(db.String(100))
    centro_custo = db.Column(db.String(100))
    observacoes = db.Column(db.Text)
    ativo = db.Column(db.Boolean, default=True)

    # Valores mensais 2025
    valor_2025 = db.Column(db.Float, default=0.0)

    # Valores mensais 2026 (Jan-Dez)
    valor_jan_2026 = db.Column(db.Float, default=0.0)
    valor_fev_2026 = db.Column(db.Float, default=0.0)
    valor_mar_2026 = db.Column(db.Float, default=0.0)
    valor_abr_2026 = db.Column(db.Float, default=0.0)
    valor_mai_2026 = db.Column(db.Float, default=0.0)
    valor_jun_2026 = db.Column(db.Float, default=0.0)
    valor_jul_2026 = db.Column(db.Float, default=0.0)
    valor_ago_2026 = db.Column(db.Float, default=0.0)
    valor_set_2026 = db.Column(db.Float, default=0.0)
    valor_out_2026 = db.Column(db.Float, default=0.0)
    valor_nov_2026 = db.Column(db.Float, default=0.0)
    valor_dez_2026 = db.Column(db.Float, default=0.0)

    def get_valor_mes(self, mes_str):
        """Retorna o valor para um mês no formato YYYY-MM"""
        mapping = {
            '2026-01': self.valor_jan_2026,
            '2026-02': self.valor_fev_2026,
            '2026-03': self.valor_mar_2026,
            '2026-04': self.valor_abr_2026,
            '2026-05': self.valor_mai_2026,
            '2026-06': self.valor_jun_2026,
            '2026-07': self.valor_jul_2026,
            '2026-08': self.valor_ago_2026,
            '2026-09': self.valor_set_2026,
            '2026-10': self.valor_out_2026,
            '2026-11': self.valor_nov_2026,
            '2026-12': self.valor_dez_2026,
        }
        return mapping.get(mes_str, 0.0) or 0.0

    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'cnpj': self.cnpj,
            'razao_social': self.razao_social,
            'data_inicio': self.data_inicio.isoformat() if self.data_inicio else None,
            'data_encerramento': self.data_encerramento.isoformat() if self.data_encerramento else None,
            'cargo': self.cargo,
            'centro_custo': self.centro_custo,
            'observacoes': self.observacoes,
            'ativo': self.ativo,
            'valor_2025': self.valor_2025 or 0,
            'valor_jan_2026': self.valor_jan_2026 or 0,
            'valor_fev_2026': self.valor_fev_2026 or 0,
            'valor_mar_2026': self.valor_mar_2026 or 0,
            'valor_abr_2026': self.valor_abr_2026 or 0,
            'valor_mai_2026': self.valor_mai_2026 or 0,
            'valor_jun_2026': self.valor_jun_2026 or 0,
            'valor_jul_2026': self.valor_jul_2026 or 0,
            'valor_ago_2026': self.valor_ago_2026 or 0,
            'valor_set_2026': self.valor_set_2026 or 0,
            'valor_out_2026': self.valor_out_2026 or 0,
            'valor_nov_2026': self.valor_nov_2026 or 0,
            'valor_dez_2026': self.valor_dez_2026 or 0,
        }

class CltRegistro(db.Model):
    __tablename__ = 'clt_registros'
    id = db.Column(db.Integer, primary_key=True)
    matricula = db.Column(db.String(50), nullable=False)
    nome = db.Column(db.String(200))
    centro_custo = db.Column(db.String(100))
    mes = db.Column(db.Date, nullable=False)
    situacao = db.Column(db.Integer)
    custo_total = db.Column(db.Float)
    total_rem = db.Column(db.Float)

    def to_dict(self):
        return {
            'id': self.id,
            'matricula': self.matricula,
            'nome': self.nome,
            'centro_custo': self.centro_custo,
            'mes': self.mes.isoformat() if self.mes else None,
            'situacao': self.situacao,
            'custo_total': self.custo_total,
            'total_rem': self.total_rem
        }


class AgrupadorCC(db.Model):
    """Regras de agrupamento por Centro de Custo (configuração em massa)."""
    __tablename__ = 'agrupador_cc'
    id = db.Column(db.Integer, primary_key=True)
    centro_custo = db.Column(db.String(200), nullable=False)
    tipo_contrato = db.Column(db.String(10), nullable=False, default='TODOS')  # CLT, PJ, TODOS
    mes_ref = db.Column(db.String(7), nullable=False, default='2026-06')       # YYYY-MM
    agrupador1 = db.Column(db.String(100))   # Tipo de área: DIRETO, ADM, APOIO INDUSTRIAL, COMERCIAL...
    agrupador2 = db.Column(db.String(100))   # Dono do pacote: JOELSON, LAIRTON, SERGIO...
    agrupador3 = db.Column(db.String(100))   # Ajuste/Label: texto livre

    __table_args__ = (
        db.UniqueConstraint('centro_custo', 'tipo_contrato', 'mes_ref', name='uq_agrupador_cc'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'centro_custo': self.centro_custo,
            'tipo_contrato': self.tipo_contrato,
            'mes_ref': self.mes_ref or '2026-06',
            'agrupador1': self.agrupador1 or '',
            'agrupador2': self.agrupador2 or '',
            'agrupador3': self.agrupador3 or '',
        }


class AgrupadorPessoa(db.Model):
    """Exceções de agrupamento por pessoa (sobrescreve a regra do CC)."""
    __tablename__ = 'agrupador_pessoa'
    id = db.Column(db.Integer, primary_key=True)
    identificador = db.Column(db.String(100), nullable=False)   # matrícula (CLT) ou CNPJ (PJ)
    tipo_contrato = db.Column(db.String(10), nullable=False)    # CLT ou PJ
    mes_ref = db.Column(db.String(7), nullable=False, default='2026-06')  # YYYY-MM
    nome = db.Column(db.String(200))                             # Para exibição e busca
    centro_custo = db.Column(db.String(200))                    # CC atual (informativo)
    agrupador1 = db.Column(db.String(100))
    agrupador2 = db.Column(db.String(100))
    agrupador3 = db.Column(db.String(100))
    inativo = db.Column(db.Boolean, default=False)

    __table_args__ = (
        db.UniqueConstraint('identificador', 'tipo_contrato', 'mes_ref', name='uq_agrupador_pessoa'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'identificador': self.identificador,
            'tipo_contrato': self.tipo_contrato,
            'mes_ref': self.mes_ref or '2026-06',
            'nome': self.nome or '',
            'centro_custo': self.centro_custo or '',
            'agrupador1': self.agrupador1 or '',
            'agrupador2': self.agrupador2 or '',
            'agrupador3': self.agrupador3 or '',
            'inativo': bool(self.inativo)
        }

class OpcaoAgrupador(db.Model):
    """Opções predefinidas para os agrupadores (1, 2 e 3)."""
    __tablename__ = 'opcoes_agrupador'
    id = db.Column(db.Integer, primary_key=True)
    grupo = db.Column(db.Integer, nullable=False) # 1, 2, ou 3
    nome = db.Column(db.String(100), nullable=False)

    __table_args__ = (
        db.UniqueConstraint('grupo', 'nome', name='uq_opcao_agrupador'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'grupo': self.grupo,
            'nome': self.nome
        }

class MetaCentroCusto(db.Model):
    __tablename__ = 'meta_centro_custo'
    id = db.Column(db.Integer, primary_key=True)
    centro_custo = db.Column(db.String(200), nullable=False)
    mes_ref = db.Column(db.String(7), nullable=False) # YYYY-MM
    meta_pessoas = db.Column(db.Integer, nullable=False, default=0)

    __table_args__ = (
        db.UniqueConstraint('centro_custo', 'mes_ref', name='uq_meta_cc'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'centro_custo': self.centro_custo,
            'mes_ref': self.mes_ref,
            'meta_pessoas': self.meta_pessoas
        }

