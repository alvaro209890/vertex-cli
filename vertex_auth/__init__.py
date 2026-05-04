"""Autenticacao Firebase para a CLI do Vertex.

Pacote separado para evitar import circular com cli/__init__.py.
"""

from .client import (
    clear_auth,
    get_auth_email,
    get_valid_token,
    load_auth,
    refresh_id_token,
    save_auth,
    sign_in_with_email,
)

__all__ = [
    "clear_auth",
    "get_auth_email",
    "get_valid_token",
    "load_auth",
    "refresh_id_token",
    "save_auth",
    "sign_in_with_email",
]
