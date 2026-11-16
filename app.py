import os
import re
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(): pass

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, jsonify
)
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from models import db, Usuario, Cliente, Produto, VendaFiado
from security import (
    gerar_hash_senha, verificar_senha, verificar_bloqueio_ip,
    registrar_falha_login, limpar_tentativas_login, sanitizar_texto,
    validar_telefone, login_required, perfil_proprietaria_required,
    aplicar_cabecalhos_seguranca
)

load_dotenv()


def criar_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv(
        "SECRET_KEY", "gil-cmb-chave-desenvolvimento-local-segura-2026"
    )
    db_url = os.getenv("DATABASE_URL", "sqlite:///gil_cmb.db")
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = os.getenv("FLASK_ENV") == "production"
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=30)

    db.init_app(app)
    app.after_request(aplicar_cabecalhos_seguranca)

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if "usuario_id" in session:
            return redirect(url_for("tela1_painel"))
        if request.method == "POST":
            ip_cliente = request.remote_addr or "local"
            bloqueado, tempo_restante = verificar_bloqueio_ip(ip_cliente)
            if bloqueado:
                flash(f"[!] Muitas tentativas incorretas. Aguarde {tempo_restante} segundos.", "erro")
                return render_template("login.html"), 429

            email = sanitizar_texto(request.form.get("login_email", ""), 150).lower()
            senha = request.form.get("senha", "")
            usuario = Usuario.query.filter_by(login_email=email, ativo=True).first()
            if usuario and verificar_senha(senha, usuario.senha_hash):
                limpar_tentativas_login(ip_cliente)
                session.clear()
                session.permanent = True
                session["usuario_id"] = usuario.id_usuario
                session["nome_usuario"] = usuario.nome_usuario
                session["perfil_acesso"] = usuario.perfil_acesso
                flash(f"[✓] Bem-vinda(o), {usuario.nome_usuario}! Sessão iniciada com segurança.", "sucesso")
                return redirect(url_for("tela1_painel"))
            else:
                registrar_falha_login(ip_cliente)
                flash("[!] Usuário ou senha inválidos. Verifique os dados digitados.", "erro")
                return render_template("login.html"), 401
        return render_template("login.html")

    @app.route("/logout", methods=["POST", "GET"])
    def logout():
        session.clear()
        flash("[✓] Sessão encerrada com segurança.", "sucesso")
        return redirect(url_for("login"))

    @app.route("/")
    @login_required
    def tela1_painel():
        total_a_receber = (
            db.session.query(func.coalesce(func.sum(Cliente.saldo_devedor_atual), 0))
            .filter(Cliente.status_cadastro == "ativo")
            .scalar()
        )
        clientes_pendentes = (
            Cliente.query.filter(
                Cliente.status_cadastro == "ativo",
                Cliente.saldo_devedor_atual > 0
            ).count()
        )
        itens_estoque_baixo = (
            Produto.query.filter(
                Produto.ativo.is_(True),
                Produto.quantidade_estoque <= Produto.estoque_minimo
            ).all()
        )
        return render_template(
            "tela1_painel.html",
            total_a_receber=float(total_a_receber or 0.0),
            clientes_pendentes=clientes_pendentes,
            itens_estoque_baixo=itens_estoque_baixo,
        )

    @app.route("/vendas/nova", methods=["GET", "POST"])
    @login_required
    def tela2_nova_venda():
        clientes = Cliente.query.filter_by(status_cadastro="ativo").order_by(Cliente.nome_completo.asc()).all()
        produtos = Produto.query.filter_by(ativo=True).order_by(Produto.nome_item.asc()).all()
        vencimento_padrao = (date.today() + timedelta(days=30)).isoformat()

        if request.method == "POST":
            try:
                id_cliente = int(request.form.get("id_cliente", 0))
                id_produto = int(request.form.get("id_produto", 0))
                quantidade = int(request.form.get("quantidade", 0))
                tipo_registro = sanitizar_texto(request.form.get("tipo_registro", "fiado"), 20)
                data_venc_str = sanitizar_texto(request.form.get("data_vencimento", ""), 20)

                if tipo_registro not in ("fiado", "encomenda"):
                    tipo_registro = "fiado"

                cliente = db.session.get(Cliente, id_cliente)
                produto = db.session.get(Produto, id_produto)

                if not cliente or cliente.status_cadastro != "ativo":
                    raise ValueError("Selecione uma cliente válida cadastrada na loja.")
                if not produto or not produto.ativo:
                    raise ValueError("Selecione um produto válido do catálogo.")
                if quantidade <= 0:
                    raise ValueError("A quantidade informada deve ser maior que zero (mínimo 1 unidade).")

                if tipo_registro == "fiado" and quantidade > produto.quantidade_estoque:
                    raise ValueError(
                        f"A quantidade solicitada ({quantidade} un.) é maior que o estoque atual de "
                        f"'{produto.nome_item}' ({produto.quantidade_estoque} un.). Digite até {produto.quantidade_estoque} un."
                    )

                try:
                    data_vencimento = date.fromisoformat(data_venc_str)
                except ValueError:
                    raise ValueError("Informe uma data de vencimento válida.")

                valor_total = (Decimal(str(produto.preco_unitario)) * Decimal(quantidade)).quantize(Decimal("0.01"))

                nova_venda = VendaFiado(
                    id_cliente=cliente.id_cliente,
                    id_produto=produto.id_produto,
                    id_usuario=session["usuario_id"],
                    quantidade=quantidade,
                    valor_total=valor_total,
                    valor_pago=Decimal("0.00"),
                    data_venda=date.today(),
                    data_vencimento=data_vencimento,
                    tipo_registro=tipo_registro,
                    status_pagamento="pendente",
                )
                db.session.add(nova_venda)

                cliente.saldo_devedor_atual = (
                    Decimal(str(cliente.saldo_devedor_atual)) + valor_total
                ).quantize(Decimal("0.01"))

                if tipo_registro == "fiado":
                    produto.quantidade_estoque -= quantidade

                db.session.commit()

                flash(
                    f"[✓] Venda de R$ {valor_total:.2f} salva! Estoque atualizado (restam {produto.quantidade_estoque} un.) "
                    f"e novo saldo de {cliente.nome_completo}: R$ {cliente.saldo_devedor_atual:.2f}.",
                    "sucesso"
                )
                return redirect(url_for("tela3_clientes_saldos"))

            except ValueError as erro_validacao:
                db.session.rollback()
                flash(f"[!] Atenção: {str(erro_validacao)}", "erro")
                return render_template(
                    "tela2_nova_venda.html",
                    clientes=clientes,
                    produtos=produtos,
                    vencimento_padrao=vencimento_padrao,
                    form_data=request.form
                ), 400

        return render_template(
            "tela2_nova_venda.html",
            clientes=clientes,
            produtos=produtos,
            vencimento_padrao=vencimento_padrao,
            form_data={}
        )

    @app.route("/clientes-saldos")
    @login_required
    def tela3_clientes_saldos():
        busca = sanitizar_texto(request.args.get("busca", ""), 100)
        filtro = sanitizar_texto(request.args.get("filtro", "todos"), 20)
        pagina = max(1, request.args.get("pagina", 1, type=int))
        por_pagina = 20

        query_vendas = (
            VendaFiado.query.options(
                joinedload(VendaFiado.cliente),
                joinedload(VendaFiado.produto)
            )
            .join(Cliente)
        )

        if busca:
            termo = f"%{busca}%"
            query_vendas = query_vendas.filter(
                db.or_(
                    Cliente.nome_completo.ilike(termo),
                    Cliente.apelido_referencia.ilike(termo),
                    Cliente.telefone_whatsapp.ilike(termo)
                )
            )

        if filtro == "pendentes":
            query_vendas = query_vendas.filter(VendaFiado.status_pagamento.in_(["pendente", "parcial"]))
        elif filtro == "vencidos":
            query_vendas = query_vendas.filter(
                VendaFiado.status_pagamento.in_(["pendente", "parcial"]),
                VendaFiado.data_vencimento < date.today()
            )
        elif filtro == "quitados":
            query_vendas = query_vendas.filter(VendaFiado.status_pagamento == "quitado")

        paginacao = query_vendas.order_by(
            VendaFiado.status_pagamento.asc(),
            VendaFiado.data_vencimento.asc(),
            VendaFiado.id_venda.desc()
        ).paginate(page=pagina, per_page=por_pagina, error_out=False)

        return render_template(
            "tela3_clientes_saldos.html",
            vendas=paginacao.items,
            paginacao=paginacao,
            busca=busca,
            filtro=filtro,
            hoje=date.today()
        )

    @app.route("/vendas/<int:id_venda>/pagamento", methods=["POST"])
    @login_required
    def registrar_pagamento(id_venda):
        venda = db.session.get(VendaFiado, id_venda)
        if not venda:
            flash("[!] Registro de venda não encontrado.", "erro")
            return redirect(url_for("tela3_clientes_saldos")), 404

        try:
            valor_str = str(request.form.get("valor_pagamento", "0")).replace(",", ".").strip()
            valor_pagamento = Decimal(valor_str).quantize(Decimal("0.01"))
        except (InvalidOperation, ValueError):
            flash("[!] Digite um valor numérico válido para o pagamento.", "erro")
            return redirect(url_for("tela3_clientes_saldos")), 400

        saldo_restante = (Decimal(str(venda.valor_total)) - Decimal(str(venda.valor_pago))).quantize(Decimal("0.01"))

        if valor_pagamento <= Decimal("0.00") or valor_pagamento > saldo_restante:
            flash(
                f"[!] O valor pago (R$ {valor_pagamento:.2f}) deve ser entre R$ 0,01 e a dívida restante (R$ {saldo_restante:.2f}).",
                "erro"
            )
            return redirect(url_for("tela3_clientes_saldos")), 400

        venda.valor_pago = (Decimal(str(venda.valor_pago)) + valor_pagamento).quantize(Decimal("0.01"))
        venda.status_pagamento = "quitado" if venda.valor_pago >= Decimal(str(venda.valor_total)) else "parcial"

        cliente = venda.cliente
        novo_saldo_cliente = Decimal(str(cliente.saldo_devedor_atual)) - valor_pagamento
        cliente.saldo_devedor_atual = max(Decimal("0.00"), novo_saldo_cliente).quantize(Decimal("0.01"))

        db.session.commit()
        flash(
            f"[✓] Pagamento de R$ {valor_pagamento:.2f} registrado para {cliente.nome_completo}! "
            f"Status: {venda.status_pagamento.upper()} | Novo saldo devedor: R$ {cliente.saldo_devedor_atual:.2f}.",
            "sucesso"
        )
        return redirect(url_for("tela3_clientes_saldos"))

    @app.route("/clientes/novo", methods=["POST"])
    @login_required
    def cadastrar_cliente():
        try:
            nome = sanitizar_texto(request.form.get("nome_completo", ""), 150)
            apelido = sanitizar_texto(request.form.get("apelido_referencia", ""), 80)
            telefone = validar_telefone(request.form.get("telefone_whatsapp", ""))
            if len(nome) < 3:
                raise ValueError("Informe o nome completo da cliente.")
            if Cliente.query.filter_by(telefone_whatsapp=telefone).first():
                raise ValueError(f"Já existe cliente cadastrada com o telefone {telefone}.")
            novo = Cliente(
                nome_completo=nome,
                telefone_whatsapp=telefone,
                apelido_referencia=apelido,
                saldo_devedor_atual=Decimal("0.00"),
                status_cadastro="ativo",
                data_cadastro=date.today()
            )
            db.session.add(novo)
            db.session.commit()
            flash(f"[✓] Cliente '{nome}' cadastrada com sucesso!", "sucesso")
        except ValueError as e:
            db.session.rollback()
            flash(f"[!] Erro no cadastro: {str(e)}", "erro")

        return redirect(url_for("tela2_nova_venda" if request.form.get("origem") == "tela2" else "tela3_clientes_saldos"))

    @app.route("/produtos", methods=["GET", "POST"])
    @login_required
    def produtos_estoque():
        if request.method == "POST":
            try:
                nome_item = sanitizar_texto(request.form.get("nome_item", ""), 150)
                categoria = sanitizar_texto(request.form.get("categoria", "cama"), 30).lower()
                preco = Decimal(str(request.form.get("preco_unitario", "0")).replace(",", ".").strip()).quantize(Decimal("0.01"))
                estoque = int(request.form.get("quantidade_estoque", "0"))
                minimo = int(request.form.get("estoque_minimo", "2"))
                if len(nome_item) < 3 or preco <= 0 or estoque < 0:
                    raise ValueError("Preencha nome válido, preço positivo e estoque não negativo.")
                item = Produto(
                    nome_item=nome_item,
                    categoria=categoria,
                    preco_unitario=preco,
                    quantidade_estoque=estoque,
                    estoque_minimo=minimo,
                    ativo=True
                )
                db.session.add(item)
                db.session.commit()
                flash(f"[✓] Produto '{nome_item}' cadastrado no estoque!", "sucesso")
                return redirect(url_for("produtos_estoque"))
            except (ValueError, InvalidOperation) as e:
                db.session.rollback()
                flash(f"[!] {str(e)}", "erro")

        produtos = Produto.query.filter_by(ativo=True).order_by(Produto.categoria, Produto.nome_item).all()
        return render_template("produtos_estoque.html", produtos=produtos)

    @app.route("/api/v1/resumo", methods=["GET"])
    @login_required
    def api_resumo():
        total_fiado = (
            db.session.query(func.coalesce(func.sum(Cliente.saldo_devedor_atual), 0))
            .filter(Cliente.status_cadastro == "ativo")
            .scalar()
        )
        return jsonify({
            "loja": "GIL CMB",
            "total_a_receber": float(total_fiado or 0.0),
            "total_clientes_ativos": Cliente.query.filter_by(status_cadastro="ativo").count(),
            "total_produtos_ativos": Produto.query.filter_by(ativo=True).count(),
            "total_vendas_registradas": VendaFiado.query.count()
        })

    @app.route("/api/v1/clientes", methods=["GET"])
    @login_required
    def api_clientes():
        return jsonify([c.to_dict() for c in Cliente.query.filter_by(status_cadastro="ativo").all()])

    @app.route("/api/v1/produtos", methods=["GET"])
    @login_required
    def api_produtos():
        return jsonify([p.to_dict() for p in Produto.query.filter_by(ativo=True).all()])

    @app.route("/api/v1/vendas", methods=["GET"])
    @login_required
    def api_vendas():
        lista = VendaFiado.query.options(joinedload(VendaFiado.cliente), joinedload(VendaFiado.produto)).limit(50).all()
        return jsonify([v.to_dict() for v in lista])

    @app.errorhandler(400)
    def erro_400(e):
        return render_template("erro.html", codigo=400, mensagem="Solicitação inválida. Verifique os dados."), 400

    @app.errorhandler(403)
    def erro_403(e):
        return render_template("erro.html", codigo=403, mensagem="Acesso restrito ao perfil da Proprietária da GIL CMB."), 403

    @app.errorhandler(404)
    def erro_404(e):
        return render_template("erro.html", codigo=404, mensagem="Página não encontrada no sistema da loja GIL CMB."), 404

    @app.errorhandler(500)
    def erro_500(e):
        db.session.rollback()
        return render_template("erro.html", codigo=500, mensagem="Erro interno inesperado. Nenhuma informação foi perdida."), 500

    @app.template_filter("whatsapp_link")
    def whatsapp_link_filter(venda):
        if not venda or not venda.cliente:
            return "#"
        digitos = re.sub(r"\D", "", venda.cliente.telefone_whatsapp or "")
        if len(digitos) in (10, 11):
            digitos = "55" + digitos
        msg = (
            f"Olá {venda.cliente.nome_completo}, tudo bem? Aqui é da loja GIL CMB! "
            f"Lembrete da sua compra ({venda.produto.nome_item}) com saldo restante de "
            f"R$ {venda.saldo_restante:.2f} (vencimento em {venda.data_vencimento.strftime('%d/%m/%Y')})."
        )
        from urllib.parse import quote
        return f"https://wa.me/{digitos}?text={quote(msg)}"

    return app


app = criar_app()

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        if Usuario.query.count() == 0:
            from seed import popular_dados_iniciais
            popular_dados_iniciais()
    app.run(host="127.0.0.1", port=5000, debug=False)
