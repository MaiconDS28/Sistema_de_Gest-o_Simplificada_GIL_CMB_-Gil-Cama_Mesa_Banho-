# Sistema de Gestão Simplificada — GIL CMB (Gil Cama Mesa e Banho)

![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=for-the-badge&logo=flask&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-D71F00?style=for-the-badge)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-7952B3?style=for-the-badge&logo=bootstrap&logoColor=white)
![ODS 8](https://img.shields.io/badge/ONU-ODS%208-007f35?style=for-the-badge)

Produto Mínimo Viável (MVP) de uma aplicação web responsiva desenvolvida para modernizar o controle operacional de balcão da loja **GIL CMB (Gil Cama Mesa e Banho)**, localizada em Valparaíso de Goiás — GO.

---

## 1. Contexto e Problema Resolvido

A loja parceira realizava todo o controle de vendas a prazo (*fiado*), encomendas sob pedido e conferência de estoque de forma manual em cadernos de papel. Esse processo analógico gerava perdas de anotações, demora na localização de históricos, erros manuais na soma de saldos devedores e falta de visibilidade sobre itens esgotados.

Este MVP substitui o caderno físico por uma interface digital gratuita, enxuta e acessível, projetada sob medida para a proprietária e sua equipe de atendimento no balcão (tanto pelo celular quanto pelo computador), alinhando-se diretamente ao **ODS 8 — Trabalho Decente e Crescimento Econômico** (Metas 8.2 e 8.3).

---

## 2. Arquitetura e Pilha Tecnológica

O sistema adota a **Arquitetura Monolítica em Camadas (padrão MVC — Model-View-Controller)**, garantindo alta coesão, baixo acoplamento e facilidade de manutenção:

* **Camada de Apresentação (View / Front-end):** HTML5, CSS3, **Bootstrap 5.3** e motor de templates **Jinja2**, personalizados com a identidade visual oficial da loja (`#007f35` e `#181a19`) e diretrizes de acessibilidade.
* **Camada de Controle e Regras de Negócio (Controller / Back-end):** **Python 3.12** com microframework **Flask 3.0**, responsável pelas rotas HTTP, cálculo automático de vendas a prazo, abatimento de pagamentos parciais/totais e baixa transacional de estoque.
* **Camada de Persistência e Dados (Model):** ORM **SQLAlchemy 2.0** integrado ao banco relacional **PostgreSQL 16** (hospedado em nuvem via Supabase) e suporte a **SQLite 3** embarcado para desenvolvimento e testes locais.
* **Camada de Segurança e Autenticação:** **Werkzeug Security** e **Bcrypt / PBKDF2-SHA256** para geração de hashes criptográficos irreversíveis com *salt* aleatório.

---

## 3. Requisitos Implementados

### Requisitos Funcionais (RF)
* **RF01 — Cadastro de Clientes:** Registro de nome completo, apelido/referência e WhatsApp único, com saldo devedor inicial zerado.
* **RF02 — Catálogo de Produtos e Estoque:** Cadastro de itens por categoria (*Cama, Mesa, Banho e Enxoval*), preço unitário, quantidade atual e alerta de estoque mínimo.
* **RF03 — Lançamento de Venda a Prazo (Fiado) / Encomenda:** Cálculo automático do valor total da venda, acréscimo no saldo devedor do cliente e desconto simultâneo no estoque em transação ACID.
* **RF04 — Registro de Pag
