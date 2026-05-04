"""Assistente de login Firebase para a CLI do Vertex."""

from __future__ import annotations

from pathlib import Path

from vertex_auth import save_auth, sign_in_with_email

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BOLD = "\033[1m"


def _banner() -> None:
    print()
    print(f"{GREEN}{'=' * 54}{RESET}")
    print(f"{GREEN}  Bem-vindo ao Vertex — CLI DeepSeek e proxy local{RESET}")
    print(f"{GREEN}{'=' * 54}{RESET}")
    print()


def _email_input() -> str:
    return input(f"{BOLD}Email:{RESET} ").strip()


def _password_input() -> str:
    """Le a senha sem ecoar no terminal."""
    try:
        import getpass

        return getpass.getpass(f"{BOLD}Senha:{RESET} ")
    except (ImportError, KeyboardInterrupt):
        return input(f"{BOLD}Senha:{RESET} ").strip()


def run_login_wizard() -> bool:
    """Executa o fluxo de login interativo.

    Returns:
        True se o login foi bem-sucedido, False se o usuario cancelou.
    """
    _banner()
    print("Faca login com sua conta do Vertex.")
    print("Nao tem conta? Crie uma em https://vertex-ad5da.web.app")
    print()

    email = _email_input()
    if not email:
        print("  Email nao pode ficar vazio.")
        return False

    password = _password_input()
    if not password:
        print("  Senha nao pode ficar vazia.")
        return False

    print()
    print("Autenticando...")

    try:
        result = sign_in_with_email(email, password)
        save_auth(
            result["id_token"],
            result["refresh_token"],
            result["expires_in"],
            result["email"],
        )
        print(f"\n{GREEN}✓ Login realizado como {result['email']}{RESET}")
        return True
    except ValueError as e:
        print(f"\n{RED}Erro: {e}{RESET}")
        return False
    except ConnectionError as e:
        print(f"\n{RED}Erro de conexao: {e}{RESET}")
        return False
    except Exception as e:
        print(f"\n{RED}Erro inesperado: {e}{RESET}")
        return False


def run_setup_wizard(env_path: Path) -> str:
    """Substituido: nao pede mais API key, faz login Firebase.

    Mantida para compatibilidade com a assinatura existente.
    """
    _banner()
    print("O Vertex agora usa autenticacao por email/senha (Firebase).")
    print()
    print("Crie sua conta em https://vertex-ad5da.web.app")
    print("e depois faca login aqui.")
    print()

    if run_login_wizard():
        return ""
    else:
        print(f"\n{YELLOW}Use 'vertex auth login' para tentar novamente.{RESET}")
        return ""
