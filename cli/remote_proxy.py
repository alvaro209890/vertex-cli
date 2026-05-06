"""Proxy HTTP local que faz forwarding autenticado para o servidor Vertex remoto.

O Claude Code se conecta a este proxy local (127.0.0.1:<porta>) com
x-api-key: freecc. O proxy obtém um Firebase JWT válido via
TokenWatchdog e encaminha a requisição para o servidor remoto
com Authorization: Bearer <jwt>.

Isto resolve o problema de expiração do token Firebase JWT (1h):
o token nunca chega ao Claude Code — fica apenas no proxy, que o
renova periodicamente via TokenWatchdog.
"""

from __future__ import annotations

import json
import os
import secrets
import socketserver
import threading
from http import HTTPStatus
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any
from urllib.parse import urlparse

from cli.token_watchdog import TokenWatchdog
from vertex_auth import get_valid_token

VERTEX_API_URL = "https://vertex-api.cursar.space"
_VERTEX_HOST = urlparse(VERTEX_API_URL).hostname  # "vertex-api.cursar.space"

_watchdog: TokenWatchdog | None = None
_server: HTTPServer | None = None
_server_thread: threading.Thread | None = None
_port: int = 8084


def _get_token() -> str:
    """Retorna um token válido, usando watchdog se disponível.

    Raises:
        RuntimeError: se não for possível obter um token.
    """
    global _watchdog
    if _watchdog is not None:
        token = _watchdog.token
        if token:
            return token
    # Fallback: refresh síncrono
    fresh = get_valid_token()
    if fresh:
        return fresh
    raise RuntimeError("Não foi possível obter token Firebase válido")


def _installed_version() -> str:
    """Retorna a versão instalada do pacote."""
    from cli.entrypoints import _installed_vertex_version

    return _installed_vertex_version()


def _load_fingerprint() -> str:
    """Carrega o fingerprint das configurações atuais."""
    from cli.entrypoints import _load_runtime_env_values, _proxy_settings_fingerprint

    return _proxy_settings_fingerprint(_load_runtime_env_values())


class RemoteProxyHandler(BaseHTTPRequestHandler):
    """Handler HTTP para o proxy de forwarding remoto."""

    # Silencia logs de request do BaseHTTPRequestHandler
    def log_message(self, format: str, *args: Any) -> None:
        from loguru import logger as loguru_logger

        loguru_logger.debug("RemoteProxy: {} {}", self.client_address, format % args)

    def _send_json(
        self, status_code: int, data: dict[str, object]
    ) -> None:
        """Envia uma resposta JSON."""
        body = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _validate_local_auth(self) -> bool:
        """Valida a autenticação local (x-api-key: freecc).

        Returns:
            True se autenticado, False caso contrário.
        """
        api_key = self.headers.get("x-api-key", "")
        auth = self.headers.get("authorization", "")
        token = api_key
        if not token and auth.lower().startswith("bearer "):
            token = auth.split(" ", 1)[1]

        return secrets.compare_digest(token, "freecc")

    def _build_upstream_url(self) -> str:
        """Constrói a URL do servidor remoto a partir do path da request."""
        path = self.path
        parsed = urlparse(path)
        return f"{VERTEX_API_URL}{parsed.path}" + (
            f"?{parsed.query}" if parsed.query else ""
        )

    def _build_upstream_headers(self) -> dict[str, str]:
        """Constrói os headers para o servidor remoto, com token Firebase."""
        headers: dict[str, str] = {}
        # Copia headers de forma case-insensitive, normalizando para lowercase
        for key, value in self.headers.items():
            headers[key.lower()] = value

        # Remove headers problemáticos que não devem ir para o upstream
        for key in (
            "host", "x-api-key", "x-forwarded-for", "x-forwarded-proto",
            "x-real-ip", "connection", "accept-encoding", "transfer-encoding",
            "content-length", "via", "x-forwarded-host",
        ):
            headers.pop(key, None)

        # Remove todos os x-forwarded-*
        for key in list(headers):
            if key.startswith("x-forwarded-"):
                del headers[key]

        # Força headers padrão para evitar bloqueio do Cloudflare
        headers["accept"] = "*/*"
        headers["user-agent"] = "Vertex CLI/1.2.6"

        # Injeta token Firebase fresco
        try:
            token = _get_token()
            headers["authorization"] = f"Bearer {token}"
        except RuntimeError:
            headers["authorization"] = "Bearer invalid"

        return headers

    def _read_body(self) -> bytes:
        """Lê o body da requisição."""
        content_length = int(self.headers.get("content-length", 0))
        if content_length > 0:
            return self.rfile.read(content_length)
        return b""

    # === Rotas ===

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path == "/health" or path == "":
            self._handle_health()
        else:
            self._handle_proxy("GET")

    def do_POST(self) -> None:
        self._handle_proxy("POST")

    def do_PUT(self) -> None:
        self._handle_proxy("PUT")

    def do_DELETE(self) -> None:
        self._handle_proxy("DELETE")

    def do_PATCH(self) -> None:
        self._handle_proxy("PATCH")

    def do_OPTIONS(self) -> None:
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, PATCH, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def _handle_health(self) -> None:
        """Rota /health: retorna status do proxy."""
        self._send_json(
            200,
            {
                "status": "healthy",
                "version": _installed_version(),
                "settings_fingerprint": _load_fingerprint(),
                "mode": "remote-proxy",
                "has_token": _watchdog is not None and _watchdog.token is not None,
            },
        )

    def _handle_token_refresh(self) -> None:
        """Rota /token/refresh: força refresh do token."""
        global _watchdog
        if _watchdog is not None:
            _watchdog.refresh_now()
            self._send_json(
                200,
                {
                    "status": "refreshed",
                    "has_token": _watchdog.token is not None,
                },
            )
        else:
            self._send_json(
                500,
                {"status": "error", "detail": "Watchdog not running"},
            )

    def _handle_proxy(self, method: str) -> None:
        """Faz o forwarding da requisição para o servidor remoto."""
        import urllib.error
        import urllib.request

        # Valida autenticação local
        if not self._validate_local_auth():
            self._send_json(401, {"error": "Invalid API key"})
            return

        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        # Rota de refresh de token
        if path == "/token/refresh" and method == "POST":
            self._handle_token_refresh()
            return

        upstream_url = self._build_upstream_url()
        body = self._read_body()
        headers = self._build_upstream_headers()
        is_streaming = "/v1/messages" in path

        try:
            if is_streaming:
                self._proxy_streaming(method, upstream_url, body, headers)
            else:
                self._proxy_normal(method, upstream_url, body, headers)
        except urllib.error.HTTPError as e:
            status_code = e.code
            error_body = e.read()
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(error_body)))
            self.end_headers()
            self.wfile.write(error_body)
        except urllib.error.URLError as e:
            self._send_json(502, {"error": f"Upstream connection error: {e.reason}"})
        except Exception as e:
            from loguru import logger as loguru_logger

            loguru_logger.error("RemoteProxy error: {}: {}", type(e).__name__, e)
            self._send_json(502, {"error": "Proxy error"})

    def _proxy_normal(
        self,
        method: str,
        url: str,
        body: bytes,
        headers: dict[str, str],
    ) -> None:
        """Faz forwarding de uma requisição normal (não-streaming)."""
        import urllib.request

        req = urllib.request.Request(
            url,
            data=body or None,
            headers=headers,
            method=method,
        )
        with urllib.request.urlopen(req, timeout=120) as upstream:
            content = upstream.read()
            status_code = upstream.status

            self.send_response(status_code)
            self.send_header("Content-Length", str(len(content)))
            ct = upstream.headers.get("Content-Type", "application/json")
            self.send_header("Content-Type", ct)
            self.end_headers()
            self.wfile.write(content)

    def _proxy_streaming(
        self,
        method: str,
        url: str,
        body: bytes,
        headers: dict[str, str],
    ) -> None:
        """Faz forwarding de uma requisição de streaming (SSE)."""
        import urllib.request
        from loguru import logger as loguru_logger

        req = urllib.request.Request(
            url,
            data=body or None,
            headers=headers,
            method=method,
        )
        with urllib.request.urlopen(req, timeout=300) as upstream:
            # Envia status code e headers
            self.send_response(upstream.status)
            ct = upstream.headers.get("Content-Type", "text/event-stream")
            self.send_header("Content-Type", ct)
            self.end_headers()

            # Stream do body
            while True:
                chunk = upstream.read(65536)
                if not chunk:
                    break
                try:
                    self.wfile.write(chunk)
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    loguru_logger.debug("Client desconectou durante streaming")
                    break


class ThreadedHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    """HTTPServer com suporte a threading para múltiplas conexões simultâneas."""
    allow_reuse_address = True
    daemon_threads = True


def start_remote_proxy(port: int = 8084) -> tuple[HTTPServer, threading.Thread]:
    """Inicia o proxy de forwarding remoto em background.

    Args:
        port: Porta para o proxy escutar (padrão 8084).

    Returns:
        Tupla (server, thread) para gerenciamento do ciclo de vida.
    """
    global _watchdog, _server, _server_thread, _port

    _port = port

    # Inicia o watchdog de token
    _watchdog = TokenWatchdog()
    _watchdog.start()

    # Cria o servidor HTTP
    _server = ThreadedHTTPServer(("127.0.0.1", port), RemoteProxyHandler)

    # Roda em thread separada
    _server_thread = threading.Thread(
        target=_server.serve_forever,
        name="remote-proxy",
        daemon=True,
    )
    _server_thread.start()

    from loguru import logger as loguru_logger
    loguru_logger.info(
        "Remote proxy iniciado em http://127.0.0.1:{}", port
    )

    return _server, _server_thread


def stop_remote_proxy() -> None:
    """Para o proxy de forwarding remoto e o watchdog."""
    global _watchdog, _server, _server_thread

    if _watchdog is not None:
        _watchdog.stop()
        _watchdog = None

    if _server is not None:
        _server.shutdown()
        _server.server_close()
        _server = None
        _server_thread = None

    from loguru import logger as loguru_logger
    loguru_logger.info("Remote proxy parado.")
