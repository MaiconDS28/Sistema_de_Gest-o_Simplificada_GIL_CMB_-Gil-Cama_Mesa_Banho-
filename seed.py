import sys
from datetime import date, timedelta
from decimal import Decimal
from models import db, Usuario, Cliente, Produto, VendaFiado
from security import gerar_hash_senha


def popular_dados_iniciais():
    if Usuario.query.count() > 0:
        return
    u_prop = Usuario(
        nome_usuario="Gil (Proprietária)",
        login_email="gil@gilcmb.com.br",
        senha_hash=gerar_hash_senha("GilCMB2026"),
        perfil_acesso="proprietaria",
        ativo=True
    )
    u_atend = Usuario(
        nome_usuario="Estefani (Atendente)",
        login_email="atendente@gilcmb.com.br",
        senha_hash=gerar_hash_senha("Balcao2026"),
        perfil_acesso="atendente",
        ativo=True
    )
    


if __name__ == "__main__":
    from app import app
    with app.app_context():
        db.create_all()
        popular_dados_iniciais()
