import os
from flask import Flask
from models import db, OpcaoAgrupador

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(BASE_DIR, "dados.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    # Cria apenas as tabelas que não existem
    db.create_all()

    # Seed initial options for Group 1
    opcoes_grupo_1 = [
        "DIRETO",
        "APOIO INDUSTRIAL",
        "ADM",
        "COMERCIAL",
        "INSS",
        "VERIFICAR"
    ]

    for nome in opcoes_grupo_1:
        if not OpcaoAgrupador.query.filter_by(grupo=1, nome=nome).first():
            db.session.add(OpcaoAgrupador(grupo=1, nome=nome))
            
    db.session.commit()
    print("OpcoesAgrupador seeded successfully.")
