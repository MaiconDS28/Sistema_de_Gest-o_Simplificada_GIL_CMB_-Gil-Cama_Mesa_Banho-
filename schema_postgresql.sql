-- ============================================================================
-- SCRIPT DDL POSTGRESQL 16 (SUPABASE) - SISTEMA DE GESTÃO SIMPLIFICADA GIL CMB
-- Compatível com RNF01 (Hash Bcrypt), RNF02 (OWASP/LGPD) e RNF03 (Índices)
-- ============================================================================

CREATE TABLE IF NOT EXISTS usuario (
    id_usuario SERIAL PRIMARY KEY,
    nome_usuario VARCHAR(120) NOT NULL,
    login_email VARCHAR(150) NOT NULL UNIQUE,
    senha_hash VARCHAR(255) NOT NULL,
    perfil_acesso VARCHAR(20) NOT NULL CHECK (perfil_acesso IN ('proprietaria', 'atendente')),
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    data_criacao TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cliente (
    id_cliente SERIAL PRIMARY KEY,
    nome_completo VARCHAR(150) NOT NULL,
    telefone_whatsapp VARCHAR(30) NOT NULL UNIQUE,
    apelido_referencia VARCHAR(80),
    saldo_devedor_atual NUMERIC(10, 2) NOT NULL DEFAULT 0.00 CHECK (saldo_devedor_atual >= 0),
    status_cadastro VARCHAR(15) NOT NULL DEFAULT 'ativo' CHECK (status_cadastro IN ('ativo', 'inativo')),
    data_cadastro DATE NOT NULL DEFAULT CURRENT_DATE
);

CREATE TABLE IF NOT EXISTS produto (
    id_produto SERIAL PRIMARY KEY,
    nome_item VARCHAR(150) NOT NULL,
    categoria VARCHAR(30) NOT NULL CHECK (categoria IN ('cama', 'mesa', 'banho', 'enxoval')),
    preco_unitario NUMERIC(10, 2) NOT NULL CHECK (preco_unitario > 0),
    quantidade_estoque INTEGER NOT NULL DEFAULT 0 CHECK (quantidade_estoque >= 0),
    estoque_minimo INTEGER NOT NULL DEFAULT 2 CHECK (estoque_minimo >= 0),
    ativo BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS venda_fiado (
    id_venda SERIAL PRIMARY KEY,
    id_cliente INTEGER NOT NULL REFERENCES cliente(id_cliente) ON DELETE RESTRICT,
    id_produto INTEGER NOT NULL REFERENCES produto(id_produto) ON DELETE RESTRICT,
    id_usuario INTEGER NOT NULL REFERENCES usuario(id_usuario) ON DELETE RESTRICT,
    quantidade INTEGER NOT NULL CHECK (quantidade > 0),
    valor_total NUMERIC(10, 2) NOT NULL CHECK (valor_total > 0),
    valor_pago NUMERIC(10, 2) NOT NULL DEFAULT 0.00 CHECK (valor_pago >= 0 AND valor_pago <= valor_total),
    data_venda DATE NOT NULL DEFAULT CURRENT_DATE,
    data_vencimento DATE NOT NULL,
    tipo_registro VARCHAR(20) NOT NULL DEFAULT 'fiado' CHECK (tipo_registro IN ('fiado', 'encomenda')),
    status_pagamento VARCHAR(20) NOT NULL DEFAULT 'pendente' CHECK (status_pagamento IN ('pendente', 'parcial', 'quitado'))
);

CREATE INDEX IF NOT EXISTS idx_cliente_nome ON cliente(nome_completo);
CREATE INDEX IF NOT EXISTS idx_cliente_telefone ON cliente(telefone_whatsapp);
CREATE INDEX IF NOT EXISTS idx_venda_cliente ON venda_fiado(id_cliente);
CREATE INDEX IF NOT EXISTS idx_venda_status_venc ON venda_fiado(status_pagamento, data_vencimento);
