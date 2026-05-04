"""Cliente REST Firebase Auth para login e refresh de token."""

from __future__ import annotations

import json
import time
from pathlib import Path

FIREBASE_API_KEY = "AIzaSyA2QV9Wu_PG6n8IUpy-4J_4j-H2dp33HNw"
AUTH_FILE = Path.home() / ".vertex" / "auth.json"
FIREBASE_SIGN_IN_URL = (
    f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"
    f"?key={FIREBASE_API_KEY}"
)
FIREBASE_REFRESH_URL = (
    f"https://securetoken.googleapis.com/v1/token?key={FIREBASE_API_KEY}"
)


def load_auth():
    """Carrega as credenciais salvas de ~/.vertex/auth.json.

    Returns:
        dict com chaves id_token, refresh_token, expires_at, email
        ou None se nao existir.
    """
    try:
        if not AUTH_FILE.exists():
            return None
        raw = AUTH_FILE.read_text("utf-8")
        data = json.loads(raw)
        if "id_token" not in data:
            return None
        return data
    except (json.JSONDecodeError, OSError):
        return None


def save_auth(id_token, refresh_token, expires_in, email=""):
    """Salva as credenciais em ~/.vertex/auth.json."""
    AUTH_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "id_token": id_token,
        "refresh_token": refresh_token,
        "expires_at": time.time() + expires_in,
        "email": email,
    }
    AUTH_FILE.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def clear_auth():
    """Apaga as credenciais (vertex logout)."""
    try:
        if AUTH_FILE.exists():
            AUTH_FILE.unlink()
    except OSError:
        pass


def sign_in_with_email(email, password):
    """Faz login com email e senha via REST API do Firebase Auth.

    Returns:
        dict com id_token, refresh_token, expires_in, email

    Raises:
        ConnectionError: se nao conseguir conectar
        ValueError: se credenciais invalidas
    """
    import httpx

    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True,
    }
    try:
        resp = httpx.post(FIREBASE_SIGN_IN_URL, json=payload, timeout=15)
    except httpx.ConnectError:
        raise ConnectionError(
            "Nao foi possivel conectar ao servidor de autenticacao. "
            "Verifique sua conexao com a internet."
        ) from None
    except httpx.TimeoutException:
        raise ConnectionError("Tempo limite excedido ao tentar autenticar.") from None

    if resp.status_code != 200:
        try:
            err = resp.json()
            msg = err.get("error", {}).get("message", "")
        except Exception:
            msg = ""

        if msg == "EMAIL_NOT_FOUND":
            raise ValueError("Email nao encontrado.")
        elif msg == "INVALID_PASSWORD":
            raise ValueError("Senha incorreta.")
        elif msg == "INVALID_LOGIN_CREDENTIALS":
            raise ValueError("Email ou senha invalidos.")
        elif msg == "USER_DISABLED":
            raise ValueError("Esta conta foi desativada.")
        elif msg == "TOO_MANY_ATTEMPTS_TRY_LATER":
            raise ValueError("Muitas tentativas de login. Tente novamente mais tarde.")
        else:
            raise ValueError(f"Erro de autenticacao: {msg or 'desconhecido'}")

    data = resp.json()
    return {
        "id_token": data["idToken"],
        "refresh_token": data["refreshToken"],
        "expires_in": int(data.get("expiresIn", 3600)),
        "email": data.get("email", email),
    }


def refresh_id_token(auth_data):
    """Tenta renovar o token usando o refresh token.

    Returns:
        dict atualizado ou None se falhar.
    """
    import httpx

    payload = {
        "grant_type": "refresh_token",
        "refresh_token": auth_data["refresh_token"],
    }
    try:
        resp = httpx.post(FIREBASE_REFRESH_URL, json=payload, timeout=15)
    except (httpx.ConnectError, httpx.TimeoutException):
        return None

    if resp.status_code != 200:
        return None

    data = resp.json()
    new_id_token = data.get("id_token")
    new_refresh_token = data.get("refresh_token", auth_data["refresh_token"])
    expires_in = int(data.get("expires_in", 3600))

    if not new_id_token:
        return None

    return {
        "id_token": new_id_token,
        "refresh_token": new_refresh_token,
        "expires_in": expires_in,
        "email": data.get("email", auth_data.get("email", "")),
    }


def get_valid_token():
    """Retorna um token JWT valido, renovando se necessario.

    Returns:
        str: O token JWT valido, ou None se nao for possivel autenticar.
    """
    auth_data = load_auth()
    if auth_data is None:
        return None

    # Token ainda valido (com margem de 60s)
    now = time.time()
    if now < auth_data["expires_at"] - 60:
        return auth_data["id_token"]

    # Tenta renovar
    refreshed = refresh_id_token(auth_data)
    if refreshed is not None:
        save_auth(
            refreshed["id_token"],
            refreshed["refresh_token"],
            refreshed["expires_in"],
            refreshed["email"],
        )
        return refreshed["id_token"]

    # Refresh falhou, precisa login
    clear_auth()
    return None


def get_auth_email():
    """Retorna o email do usuario autenticado, ou None."""
    data = load_auth()
    if data:
        return data.get("email")
    return None
