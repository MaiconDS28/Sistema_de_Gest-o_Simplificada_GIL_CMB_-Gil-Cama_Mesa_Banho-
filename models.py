from datetime import date, datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import CheckConstraint, Index

db = SQLAlchemy()


class Usuario(db.Model):
    __tablename__ = "usuario"
    id_usuario = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nome_usuario = db.Column(db.String(120), nullable=False)
    login_email = db.Column(db.String(150), nullable=False, unique=True, index=True)
    senha_hash = db.Column(db.String(255), nullable=False)
    perfil_acesso = db.Column(db.String(20), nullable=False, default="atendente")
    ativo = db.Column(db.Boolean, nullable=False, default=True)
    data_criacao = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    vendas_registradas = db.relationship("VendaFiado", back_populates="usuario", lazy="select")


class Cliente(db.Model):
    __tablename__ = "cliente"
    id_cliente = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nome_completo = db.Column(db.String(150), nullable=False, index=True)
    telefone_whatsapp = db.Column(db.String(30), nullable=False, unique=True, index=True)
    apelido_referencia = db.Column(db.String(80), nullable=True)
    saldo_devedor_atual = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    status_cadastro = db.Column(db.String(15), nullable=False, default="ativo")
    data_cadastro = db.Column(db.Date, nullable=False, default=date.today)
    vendas = db.relationship("VendaFiado", back_populates="cliente", lazy="select")

    def to_dict(self):
        return {
            "id_cliente": self.id_cliente,
            "nome_completo": self.nome_completo,
            "telefone_whatsapp": self.telefone_whatsapp,
            "apelido_referencia": self.apelido_referencia or "",
            "saldo_devedor_atual": float(self.saldo_devedor_atual or 0.0),
            "status_cadastro": self.status_cadastro,
            "data_cadastro": self.data_cadastro.isoformat() if self.data_cadastro else None,
        }


class Produto(db.Model):
    __tablename__ = "produto"
    id_produto = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nome_item = db.Column(db.String(150), nullable=False, index=True)
    categoria = db.Column(db.String(30), nullable=False)
    preco_unitario = db.Column(db.Numeric(10, 2), nullable=False)
    quantidade_estoque = db.Column(db.Integer, nullable=False, default=0)
    estoque_minimo = db.Column(db.Integer, nullable=False, default=2)
    ativo = db.Column(db.Boolean, nullable=False, default=True)
    vendas = db.relationship("VendaFiado", back_populates="produto", lazy="select")

    def to_dict(self):
        return {
            "id_produto": self.id_produto,
            "nome_item": self.nome_item,
            "categoria": self.categoria,
            "preco_unitario": float(self.preco_unitario or 0.0),
            "quantidade_estoque": self.quantidade_estoque,
            "estoque_minimo": self.estoque_minimo,
            "abaixo_do_minimo": self.quantidade_estoque <= self.estoque_minimo,
            "ativo": self.ativo,
        }


class VendaFiado(db.Model):
    __tablename__ = "venda_fiado"
    id_venda = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_cliente = db.Column(db.Integer, db.ForeignKey("cliente.id_cliente", ondelete="RESTRICT"), nullable=False, index=True)
    id_produto = db.Column(db.Integer, db.ForeignKey("produto.id_produto", ondelete="RESTRICT"), nullable=False)
    id_usuario = db.Column(db.Integer, db.ForeignKey("usuario.id_usuario", ondelete="RESTRICT"), nullable=False)
    quantidade = db.Column(db.Integer, nullable=False)
    valor_total = db.Column(db.Numeric(10, 2), nullable=False)
    valor_pago = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    data_venda = db.Column(db.Date, nullable=False, default=date.today)
    data_vencimento = db.Column(db.Date, nullable=False, index=True)
    tipo_registro = db.Column(db.String(20), nullable=False, default="fiado")
    status_pagamento = db.Column(db.String(20), nullable=False, default="pendente", index=True)

    cliente = db.relationship("Cliente", back_populates="vendas")
    produto = db.relationship("Produto", back_populates="vendas")
    usuario = db.relationship("Usuario", back_populates="vendas_registradas")

    @property
    def saldo_restante(self):
        return float(self.valor_total or 0.0) - float(self.valor_pago or 0.0)

    @property
    def esta_vencida(self):
        return self.status_pagamento != "quitado" and self.data_vencimento < date.today()

    def to_dict(self):
        return {
            "id_venda": self.id_venda,
            "id_cliente": self.id_cliente,
            "cliente_nome": self.cliente.nome_completo if self.cliente else None,
            "id_produto": self.id_produto,
            "produto_nome": self.produto.nome_item if self.produto else None,
            "quantidade": self.quantidade,
            "valor_total": float(self.valor_total or 0.0),
            "valor_pago": float(self.valor_pago or 0.0),
            "saldo_restante": round(self.saldo_restante, 2),
            "data_venda": self.data_venda.isoformat() if self.data_venda else None,
            "data_vencimento": self.data_vencimento.isoformat() if self.data_vencimento else None,
            "tipo_registro": self.tipo_registro,
            "status_pagamento": self.status_pagamento,
            "esta_vencida": self.esta_vencida,
        }
