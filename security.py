import re
import time
import hashlib
import secrets
from functools import wraps
from flask import session, redirect, url_for, flash, request, jsonify

try:
    import bcrypt
    HAS_BCRYPT = True
except ImportError:
    HAS_BCRYPT = False

TENTATIVAS_LOGIN = {}
MAX_TENTATIVAS = 5
TEMPO_BLOQUEIO_SEGUNDOS = 300


def gerar_hash_senha(senha_limpa: str) -> str:
    if HAS_BCRYPT:
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(senha_limpa.encode("utf-8"), salt)
        return hashed.decode("utf-8")
    salt_hex = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", senha_limpa.encode("utf-8"), salt_hex.encode("utf-8"), 600000)
    return f"pbkdf2:sha256:600000${salt_hex}${dk.hex()}"


def verificar_senha(senha_limpa: str, senha_hash: str) -> bool:
    if not senha_limpa or not senha_hash:
        return False
    if senha_hash.startswith("$2") and HAS_BCRYPT:
        try:
            return bcrypt.checkpw(senha_limpa.encode("utf-8"), senha_hash.encode("utf-8"))
        except ValueError:
            return False
    if senha_hash.startswith("pbkdf2:sha256:"):
        try:
            partes = senha_hash.split("$")
            iteracoes = int(partes[0].split(":")[2])
            salt_hex = partes[1]
            hash_armazenado = partes[2]
            dk = hashlib.pbkdf2_hmac("sha256", senha_limpa.encode("utf-8"), salt_hex.encode("utf-8"), iteracoes)
            return secrets.compare_digest(dk.hex(), hash_armazenado)
        except Exception:
            return False
    return False


def verificar_bloqueio_ip(identificador: str) -> tuple[bool, int]:
    registro = TENTATIVAS_LOGIN.get(identificador)
    if not registro:
        return False, 0
    falhas, ultimo_tempo = registro
    agora = time.time()
    if falhas >= MAX_TENTATIVAS:
        decorrido = agora - ultimo_tempo
        if decorrido < TEMPO_BLOQUEIO_SEGUNDOS:
            return True, int(TEMPO_BLOQUEIO_SEGUNDOS - decorrido)
        TENTATIVAS_LOGIN.pop(identificador, None)
    return False, 0


def registrar_falha_login(identificador: str):
    falhas, _ = TENTATIVAS_LOGIN.get(identificador, (0, 0))
    TENTATIVAS_LOGIN[identificador] = (falhas + 1, time.time())


def limpar_tentativas_login(identificador: str):
    TENTATIVAS_LOGIN.pop(identificador, None)


def sanitizar_texto(valor: str, max_len: int = 150) -> str:
    if not valor:
        return ""
    texto = str(valor).strip()
    texto = re.sub(r"<[^>]*>", "", texto)
    return texto[:max_len]


def validar_telefone(telefone: str) -> str:
    limpo = re.sub(r"[^0-9()\-\s+]", "", str(telefone or "")).strip()
    apenas_digitos = re.sub(r"\D", "", limpo)
    if len(apenas_digitos) < 8 or len(apenas_digitos) > 15:
        raise ValueError("Digite um número de telefone/WhatsApp válido com DDD (ex.: 61 99999-0001).")
    return limpo[:30]


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "usuario_id" not in session:
            if request.path.startswith("/api/"):
                return jsonify({"erro": "Acesso não autorizado. Faça login para continuar."}), 401
            flash("[!] Faça login para acessar o painel da loja GIL CMB.", "erro")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


def perfil_proprietaria_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "usuario_id" not in session:
            if request.path.startswith("/api/"):
                return jsonify({"erro": "Autenticação necessária."}), 401
            return redirect(url_for("login"))
        if session.get("perfil_acesso") != "proprietaria":
            if request.path.startswith("/api/"):
                return jsonify({"erro": "Operação exclusiva para o perfil Proprietária."}), 403
            flash("[!] Permissão negada: esta ação é exclusiva da Proprietária da GIL CMB.", "erro")
            return redirect(url_for("tela1_painel"))
        return f(*args, **kwargs)
    return decorated_function


def aplicar_cabecalhos_seguranca(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "font-src 'self' https://cdn.jsdelivr.net data:; "
        "img-src 'self' data:;"
    )
    return response
