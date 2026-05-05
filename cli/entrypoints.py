"""CLI entry points for the installed package."""

from __future__ import annotations

import contextlib
import os
import sys
from pathlib import Path
from typing import Any

CONFIG_DIR = Path.home() / ".config" / "vertex"
ENV_FILE = CONFIG_DIR / ".env"
VERTEX_CLI_CONFIG_DIR = Path.home() / ".vertex"
VERTEX_CLI_SETTINGS_FILE = VERTEX_CLI_CONFIG_DIR / "settings.json"
DEFAULT_MODEL = "deepseek/deepseek-v4-flash"
DEEPSEEK_ONLY_DEFAULT_MODEL = DEFAULT_MODEL
PACKAGE_NAME = "vertex-cli"
MANAGED_VERTEX_CLI_ENV_BASE = {
    "ANTHROPIC_BASE_URL": "http://127.0.0.1:{port}",
    "ANTHROPIC_AUTH_TOKEN": "freecc",
    "DISABLE_LOGIN_COMMAND": "1",
}

VERTEX_API_URL = "https://vertex-api.cursar.space"
VERTEX_WEB_URL = "https://vertex-ad5da.web.app"


def _load_env_template() -> str:
    """Load the canonical root env template from package resources or source."""
    import importlib.resources

    packaged = importlib.resources.files("cli").joinpath("env.example")
    if packaged.is_file():
        return packaged.read_text("utf-8")

    source_template = Path(__file__).resolve().parents[1] / ".env.example"
    if source_template.is_file():
        return source_template.read_text(encoding="utf-8")

    raise FileNotFoundError("Could not find bundled or source .env.example template.")


def _load_runtime_env_values() -> dict[str, str]:
    """Load env values in the same order used by Settings."""
    from dotenv import dotenv_values

    files = [ENV_FILE, Path(".env")]
    if explicit := os.environ.get("VERTEX_ENV_FILE"):
        files.append(Path(explicit))

    values: dict[str, str] = {}
    for env_file in files:
        if env_file.is_file():
            for key, value in dotenv_values(env_file).items():
                values[key] = "" if value is None else value

    return {**values, **os.environ}


def _configured_model_values() -> dict[str, str]:
    """Return model defaults that the vendored CLI should advertise."""
    values = _load_runtime_env_values()
    fallback = _deepseek_model_or_default(values.get("MODEL"))
    return {
        "default": fallback,
        "opus": _deepseek_model_or_default(values.get("MODEL_OPUS"), fallback),
        "sonnet": _deepseek_model_or_default(values.get("MODEL_SONNET"), fallback),
        "haiku": _deepseek_model_or_default(values.get("MODEL_HAIKU"), fallback),
    }


def _proxy_settings_fingerprint(values: dict[str, str]) -> str:
    """Return the non-secret proxy config fingerprint exposed by /health."""
    import hashlib
    import json

    payload = {
        "model": values.get("MODEL") or DEEPSEEK_ONLY_DEFAULT_MODEL,
        "model_opus": values.get("MODEL_OPUS") or None,
        "model_sonnet": values.get("MODEL_SONNET") or None,
        "model_haiku": values.get("MODEL_HAIKU") or None,
        "enable_model_thinking": _env_bool(values.get("ENABLE_MODEL_THINKING"), True),
        "enable_opus_thinking": _env_optional_bool(values.get("ENABLE_OPUS_THINKING")),
        "enable_sonnet_thinking": _env_optional_bool(
            values.get("ENABLE_SONNET_THINKING")
        ),
        "enable_haiku_thinking": _env_optional_bool(
            values.get("ENABLE_HAIKU_THINKING")
        ),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _env_bool(value: str | None, default: bool) -> bool:
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_optional_bool(value: str | None) -> bool | None:
    if value is None or value == "":
        return None
    return _env_bool(value, False)


def _deepseek_model_or_default(
    model_ref: str | None, default: str = DEEPSEEK_ONLY_DEFAULT_MODEL
) -> str:
    """Return a DeepSeek model ref; ignore any non-DeepSeek provider config."""
    if model_ref and model_ref.startswith("deepseek/"):
        return model_ref
    return default


def _display_model_name(model_ref: str) -> str:
    """Return a compact model display name for vendored CLI settings."""
    if "/" not in model_ref:
        return model_ref
    provider, model_name = model_ref.split("/", 1)
    return f"{provider}: {model_name}"


# ==================== Firebase Auth na CLI ====================

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BOLD = "\033[1m"


def _needs_auth() -> bool:
    """Verifica se o usuario precisa fazer login."""
    from vertex_auth import get_valid_token

    return get_valid_token() is None


def _run_auth_wizard_if_needed() -> None:
    """Executa o wizard de login se o usuario nao estiver autenticado."""
    if not _needs_auth():
        return
    from cli.setup_wizard import run_login_wizard

    if not run_login_wizard():
        print(f"{YELLOW}Autenticacao necessaria para usar o Vertex.{RESET}")
        print("Rode: vertex auth login")
        sys.exit(1)


def _ensure_remote_account_active() -> str | None:
    """Confirm the hosted dashboard API still accepts this Firebase account."""
    from vertex_auth import clear_auth, get_valid_token

    token = get_valid_token()
    if not token:
        return None

    import urllib.error
    import urllib.request

    req = urllib.request.Request(
        f"{VERTEX_API_URL}/me",
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "User-Agent": f"Vertex CLI/{_installed_vertex_version()}",
        },
        method="GET",
    )
    try:
        response = urllib.request.urlopen(req, timeout=10)
        try:
            payload = _read_json_response(response)
        finally:
            response.close()
        if _contains_insufficient_credits_marker(payload):
            print(
                f"{YELLOW}Saldo insuficiente. Recarregue em {VERTEX_WEB_URL} "
                f"para usar o Vertex.{RESET}"
            )
            sys.exit(1)
    except urllib.error.HTTPError as exc:
        if exc.code == 403 and _is_account_blocked_response(exc):
            print(
                f"{RED}Conta bloqueada. Fale com o suporte para reativar o acesso.{RESET}"
            )
            sys.exit(1)
        if exc.code == 401:
            clear_auth()
            print(
                f"{YELLOW}Sessao expirada. Faca login novamente com `vertex auth login`.{RESET}"
            )
            sys.exit(1)
        print(
            f"{YELLOW}Aviso: nao foi possivel confirmar o status da conta ({exc.code}).{RESET}"
        )
    except Exception:
        print(
            f"{YELLOW}Aviso: nao foi possivel confirmar o status da conta agora.{RESET}"
        )
    return token


def _read_json_response(response: object) -> object | None:
    """Read a small JSON response payload, returning None when unavailable."""
    import json

    read = getattr(response, "read", None)
    if not callable(read):
        return None

    try:
        raw = read(65536)
    except Exception:
        return None
    if not isinstance(raw, bytes) or not raw:
        return None

    try:
        return json.loads(raw.decode("utf-8", "replace"))
    except json.JSONDecodeError:
        return None


def _contains_insufficient_credits_marker(value: object) -> bool:
    """Return True when account status says the user must recharge."""
    if isinstance(value, str):
        normalized = value.lower()
        return (
            "saldo insuficiente" in normalized
            or "sem creditos" in normalized
            or "insufficient credits" in normalized
        )

    if not isinstance(value, dict):
        return False

    credits = value.get("credits")
    if isinstance(credits, dict) and credits.get("balance") == 0:
        return True

    code = str(value.get("code") or value.get("error_code") or "").lower()
    if code in {"insufficient_credits", "no_credits"}:
        return True

    return any(
        _contains_insufficient_credits_marker(value.get(key))
        for key in ("error", "detail", "message")
    )


def _is_account_blocked_response(exc: object) -> bool:
    """Return whether a 403 response explicitly says the account is blocked."""
    import json

    read = getattr(exc, "read", None)
    if not callable(read):
        return False

    try:
        raw = read(4096).decode("utf-8", "replace")
    except Exception:
        return False

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return False

    return _contains_account_block_marker(data)


def _contains_account_block_marker(value: object) -> bool:
    """Return True when a response payload explicitly identifies account block."""
    if isinstance(value, str):
        normalized = value.lower()
        return "conta bloqueada" in normalized or "account blocked" in normalized

    if not isinstance(value, dict):
        return False

    code = str(value.get("code") or value.get("error_code") or "").lower()
    if code in {"account_blocked", "user_blocked"}:
        return True

    return any(
        _contains_account_block_marker(value.get(key))
        for key in ("error", "detail", "message")
    )


def _is_auth_login_request(argv: list[str] | None = None) -> bool:
    """Return whether CLI args request Firebase login."""
    args = list(sys.argv[1:] if argv is None else argv[1:])
    lowered = [arg.lower() for arg in args]
    return tuple(lowered[:2]) == ("auth", "login") or "/login" in lowered


def _is_logout_request(argv: list[str] | None = None) -> bool:
    """Return whether CLI args request logout."""
    args = list(sys.argv[1:] if argv is None else argv[1:])
    lowered = [arg.lower() for arg in args]
    return (
        tuple(lowered[:2]) == ("auth", "logout")
        or "/logout" in lowered
        or lowered[:1] == ["logout"]
    )


def _is_auth_status_request(argv: list[str] | None = None) -> bool:
    """Return whether CLI args request auth status."""
    args = list(sys.argv[1:] if argv is None else argv[1:])
    lowered = [arg.lower() for arg in args]
    return tuple(lowered[:2]) == ("auth", "status") or "/status" in lowered


def _handle_auth_login_request() -> bool:
    """Handle auth login command."""
    if not _is_auth_login_request():
        return False

    from cli.setup_wizard import run_login_wizard
    from vertex_auth import clear_auth

    clear_auth()
    run_login_wizard()
    return True


def _handle_logout_request() -> bool:
    """Handle logout command."""
    if not _is_logout_request():
        return False

    from vertex_auth import clear_auth

    clear_auth()
    print(f"{GREEN}✓ Logout realizado. Token removido.{RESET}")
    print("  Use `vertex auth login` para autenticar novamente.")
    return True


def _handle_auth_status_request() -> bool:
    """Handle auth status command."""
    if not _is_auth_status_request():
        return False

    from vertex_auth import load_auth

    auth_data = load_auth()
    if auth_data and auth_data.get("id_token"):
        if "--json" in sys.argv:
            import json

            print(
                json.dumps(
                    {"loggedIn": True, "email": auth_data.get("email", "")}, indent=2
                )
            )
        else:
            print(f"{GREEN}✓ Autenticado como {auth_data.get('email', '?')}{RESET}")
    else:
        if "--json" in sys.argv:
            import json

            print(json.dumps({"loggedIn": False}, indent=2))
        else:
            print(f"{YELLOW}Nao autenticado.{RESET}")
            print("Use `vertex auth login` para fazer login.")
    return True


# ==================== Fim Firebase Auth ====================


def _is_version_request(argv: list[str] | None = None) -> bool:
    """Return whether CLI args request only the vendored CLI version."""
    args = list(sys.argv[1:] if argv is None else argv[1:])
    return len(args) == 1 and args[0] in {"--version", "-v", "-V"}


def _managed_vertex_cli_env(port: str) -> dict[str, str]:
    """Return environment values that force the vendored CLI through Vertex."""
    import json

    models = _configured_model_values()
    env = {
        key: value.format(port=port)
        for key, value in MANAGED_VERTEX_CLI_ENV_BASE.items()
    }
    env.update(
        {
            "ANTHROPIC_DEFAULT_OPUS_MODEL": models["opus"],
            "ANTHROPIC_DEFAULT_OPUS_MODEL_NAME": _display_model_name(models["opus"]),
            "ANTHROPIC_DEFAULT_SONNET_MODEL": models["sonnet"],
            "ANTHROPIC_DEFAULT_SONNET_MODEL_NAME": _display_model_name(
                models["sonnet"]
            ),
            "ANTHROPIC_DEFAULT_HAIKU_MODEL": models["haiku"],
            "ANTHROPIC_DEFAULT_HAIKU_MODEL_NAME": _display_model_name(models["haiku"]),
        }
    )
    # Inject extra models so /model picker shows both DeepSeek variants.
    unique_models: list[str] = []
    for m in (models["opus"], models["sonnet"], models["haiku"], models["default"]):
        if m and m not in unique_models:
            unique_models.append(m)
    # Always ensure both known DeepSeek models are in the list
    for known in ("deepseek/deepseek-v4-flash", "deepseek/deepseek-v4-pro"):
        if known not in unique_models:
            unique_models.append(known)
    env["OPENCLAUDE_EXTRA_MODEL_OPTIONS"] = json.dumps(unique_models)
    return env


def _remote_vertex_cli_env(auth_token: str) -> dict[str, str]:
    """Return environment values that force the vendored CLI through remote Vertex."""
    import json

    models = _configured_model_values()
    env = {
        "ANTHROPIC_BASE_URL": VERTEX_API_URL,
        "ANTHROPIC_AUTH_TOKEN": auth_token,
        "DISABLE_LOGIN_COMMAND": "1",
        "ANTHROPIC_DEFAULT_OPUS_MODEL": models["opus"],
        "ANTHROPIC_DEFAULT_OPUS_MODEL_NAME": _display_model_name(models["opus"]),
        "ANTHROPIC_DEFAULT_SONNET_MODEL": models["sonnet"],
        "ANTHROPIC_DEFAULT_SONNET_MODEL_NAME": _display_model_name(models["sonnet"]),
        "ANTHROPIC_DEFAULT_HAIKU_MODEL": models["haiku"],
        "ANTHROPIC_DEFAULT_HAIKU_MODEL_NAME": _display_model_name(models["haiku"]),
    }

    unique_models: list[str] = []
    for m in (models["opus"], models["sonnet"], models["haiku"], models["default"]):
        if m and m not in unique_models:
            unique_models.append(m)
    for known in ("deepseek/deepseek-v4-flash", "deepseek/deepseek-v4-pro"):
        if known not in unique_models:
            unique_models.append(known)
    env["OPENCLAUDE_EXTRA_MODEL_OPTIONS"] = json.dumps(unique_models)
    return env


def _ensure_vertex_cli_settings(env_updates: dict[str, str]) -> None:
    """Create/update Vertex CLI settings owned by this wrapper."""
    import json

    VERTEX_CLI_CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    settings: dict[str, Any] = {}
    if VERTEX_CLI_SETTINGS_FILE.exists():
        try:
            raw_settings = json.loads(VERTEX_CLI_SETTINGS_FILE.read_text("utf-8"))
            if isinstance(raw_settings, dict):
                settings = raw_settings
        except json.JSONDecodeError:
            settings = {}

    raw_env = settings.get("env")
    env: dict[str, Any] = dict(raw_env) if isinstance(raw_env, dict) else {}
    for key in (
        "CLAUDE_CODE_USE_OPENAI",
        "CLAUDE_CODE_USE_GEMINI",
        "CLAUDE_CODE_USE_MISTRAL",
        "CLAUDE_CODE_USE_GITHUB",
        "CLAUDE_CODE_USE_BEDROCK",
        "CLAUDE_CODE_USE_VERTEX",
        "OPENAI_API_KEY",
        "OPENAI_BASE_URL",
        "OPENAI_API_BASE",
        "OPENAI_MODEL",
    ):
        env.pop(key, None)
    env.update(env_updates)
    models = _configured_model_values()
    settings.update(
        {
            "env": env,
            "skipDangerousModePermissionPrompt": True,
            "model": models["default"],
        }
    )
    for key in (
        "provider",
        "providerProfile",
        "provider_profile",
        "apiProvider",
    ):
        settings.pop(key, None)
    VERTEX_CLI_SETTINGS_FILE.write_text(
        json.dumps(settings, indent=2) + "\n", encoding="utf-8"
    )


def _vertex_cli_bin() -> Path:
    """Return the vendored Vertex CLI launcher path."""
    if override := os.environ.get("VERTEX_CLI_BIN"):
        return Path(override).expanduser()
    return (
        Path(__file__).resolve().parents[1] / "vendor" / "vertex-cli" / "bin" / "vertex"
    )


def _node_bin() -> str | None:
    """Find a Node.js executable for the vendored CLI runtime."""
    import shutil

    if node := shutil.which("node"):
        return node

    nvm_root = Path.home() / ".nvm" / "versions" / "node"
    candidates = sorted(nvm_root.glob("*/bin/node"), reverse=True)
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return None


def _installed_vertex_version() -> str:
    """Return the installed Python package version used by the proxy."""
    from importlib.metadata import PackageNotFoundError, version

    try:
        return version(PACKAGE_NAME)
    except PackageNotFoundError:
        source_pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
        if source_pyproject.is_file():
            for line in source_pyproject.read_text(encoding="utf-8").splitlines():
                if line.startswith("version = "):
                    return line.split('"', 2)[1]
        return "unknown"


def _read_proxy_health(port: str) -> dict[str, Any] | None:
    """Return local proxy health JSON, or None when no compatible server responds."""
    import json
    import urllib.request

    health_url = f"http://127.0.0.1:{port}/health"
    try:
        with urllib.request.urlopen(health_url, timeout=1) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _terminate_vertex_proxy_processes() -> int:
    """Terminate stale background ``python -m vertex_proxy`` processes."""
    import subprocess

    if os.name == "nt":
        return 0

    try:
        output = subprocess.check_output(
            ["ps", "-eo", "pid=,args="],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        return 0

    current_pid = os.getpid()
    killed = 0
    for line in output.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            pid_text, args = stripped.split(maxsplit=1)
            pid = int(pid_text)
        except ValueError:
            continue
        if pid == current_pid:
            continue
        if "vertex_proxy" not in args:
            continue
        try:
            os.kill(pid, 15)
            killed += 1
        except OSError:
            continue
    return killed


def _wait_for_proxy_health(
    port: str, *, expected_version: str, attempts: int = 15
) -> bool:
    import time

    for _ in range(attempts):
        time.sleep(1)
        health = _read_proxy_health(port)
        if health and health.get("version") == expected_version:
            return True
    return False


def _wait_for_proxy_down(port: str, *, attempts: int = 10) -> bool:
    import time

    for _ in range(attempts):
        time.sleep(0.5)
        if _read_proxy_health(port) is None:
            return True
    return False


def _start_proxy() -> bool:
    """Start the Vertex proxy in background. Returns True if ready."""
    import subprocess

    port = os.environ.get("VERTEX_PORT", "8083")
    expected_version = _installed_vertex_version()
    expected_fingerprint = _proxy_settings_fingerprint(_load_runtime_env_values())
    health = _read_proxy_health(port)
    if health is not None:
        if (
            health.get("version") == expected_version
            and health.get("settings_fingerprint") == expected_fingerprint
        ):
            return True
        print("Restarting Vertex proxy...")
        if _terminate_vertex_proxy_processes():
            _wait_for_proxy_down(port)
    else:
        print("Starting Vertex proxy...")

    subprocess.Popen(
        [
            sys.executable,
            "-m",
            "vertex_proxy",
        ],
        env={**os.environ, "PORT": port},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    if _wait_for_proxy_health(port, expected_version=expected_version):
        return True

    print(f"Warning: Proxy may not have started on port {port}.")
    return False


def _record_usage_to_api(model: str, tokens: int) -> None:
    """Registra uso de tokens na API remota."""
    from vertex_auth import get_valid_token

    token = get_valid_token()
    if not token:
        return  # silenciosamente falha se nao estiver autenticado

    import json
    import urllib.request

    url = f"{VERTEX_API_URL}/usage"
    body = json.dumps({"model": model, "tokens": tokens}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with contextlib.suppress(Exception):
        urllib.request.urlopen(req, timeout=5)


def _ensure_vendor_npm_deps(vertex_bin: Path) -> None:
    """Run npm install in the vendor directory if node_modules is missing."""
    vendor_dir = vertex_bin.parents[1]
    node_modules = vendor_dir / "node_modules"
    if node_modules.is_dir():
        return
    package_json = vendor_dir / "package.json"
    if not package_json.is_file():
        return
    import subprocess

    print("Instalando dependencias do Vertex CLI...")
    try:
        subprocess.run(
            ["npm", "install", "--production", "--silent"],
            cwd=str(vendor_dir),
            capture_output=True,
            timeout=120,
        )
    except Exception:
        print("Aviso: falha ao instalar dependencias Node.js.")


def _is_local_proxy_requested() -> bool:
    """Return True when the user explicitly requests the local proxy mode."""
    return os.environ.get("VERTEX_LOCAL_PROXY") == "true"


def cli() -> None:
    """Launch Vertex CLI: ensure auth + proxy are running, open the vendored CLI runtime.

    Comportamento:
      - Padrão: modo remoto (conecta ao servidor vertex-api.cursar.space)
      - VERTEX_LOCAL_PROXY=true: modo local (inicia proxy na máquina do usuário)
    """
    import subprocess

    # Comandos de autenticacao
    if _is_version_request():
        # Deve ser processado antes do auth para permitir --version sem login
        vertex_cli = _vertex_cli_bin()
        node_bin = _node_bin()
        if vertex_cli.is_file() and node_bin:
            _ensure_vendor_npm_deps(vertex_cli)
            proc = subprocess.run([node_bin, str(vertex_cli), *sys.argv[1:]])
            sys.exit(proc.returncode)
        else:
            print(_installed_vertex_version())
            return

    if _handle_logout_request():
        return
    if _handle_auth_login_request():
        return
    if _handle_auth_status_request():
        return

    vertex_cli = _vertex_cli_bin()
    if not vertex_cli.is_file():
        print(f"Error: Vertex CLI runtime not found at {vertex_cli}")
        print(
            "Reinstall Vertex or rebuild the package with vendor/vertex-cli included."
        )
        sys.exit(1)
    node_bin = _node_bin()
    if node_bin is None:
        print("Error: Node.js is required to run the Vertex CLI runtime.")
        print("Install Node.js 20+ and run vertex again.")
        sys.exit(1)

    # Garante que as dependencias Node.js do vendor estao instaladas
    _ensure_vendor_npm_deps(vertex_cli)

    # Verifica autenticacao
    _run_auth_wizard_if_needed()
    remote_auth_token = _ensure_remote_account_active()

    # Decide modo: remoto (padrão) vs local
    env = os.environ.copy()
    for key in (
        "CLAUDE_CODE_USE_OPENAI",
        "CLAUDE_CODE_USE_GEMINI",
        "CLAUDE_CODE_USE_MISTRAL",
        "CLAUDE_CODE_USE_GITHUB",
        "CLAUDE_CODE_USE_BEDROCK",
        "CLAUDE_CODE_USE_VERTEX",
    ):
        env.pop(key, None)
    env["CLAUDE_CONFIG_DIR"] = str(VERTEX_CLI_CONFIG_DIR)

    if _is_local_proxy_requested():
        # ─── Modo local (proxy na máquina do usuário) ───
        port = os.environ.get("VERTEX_PORT", "8083")
        local_env = _managed_vertex_cli_env(port)
        _ensure_vertex_cli_settings(local_env)
        _start_proxy()
        env.update(local_env)
        env["VERTEX_DASHBOARD_URL"] = f"http://localhost:{port}/dashboard"
    else:
        # ─── Modo remoto (padrão) ───
        print("Conectando ao servidor Vertex...")
        if not remote_auth_token:
            print(
                f"{YELLOW}Sessao expirada. Faca login novamente com "
                f"`vertex auth login`.{RESET}"
            )
            sys.exit(1)
        remote_env = _remote_vertex_cli_env(remote_auth_token)
        _ensure_vertex_cli_settings(remote_env)
        env.update(remote_env)
        env["VERTEX_DASHBOARD_URL"] = VERTEX_API_URL

    # Set NODE_OPTIONS memory limit when not user-overridden
    if "NODE_OPTIONS" not in env:
        env["NODE_OPTIONS"] = "--max-old-space-size=8192"

    # Launch Vertex CLI
    print("Launching Vertex CLI...")
    try:
        proc = subprocess.run([node_bin, str(vertex_cli), *sys.argv[1:]], env=env)
        sys.exit(proc.returncode)
    except FileNotFoundError:
        print(f"Error: Vertex CLI runtime not found at {vertex_cli}")
        sys.exit(1)


def serve() -> None:
    """Start the FastAPI server (registered as `vertex-proxy` script)."""
    if _handle_logout_request():
        return
    if _handle_auth_login_request():
        return
    if _handle_auth_status_request():
        return

    try:
        import uvicorn
        from config.settings import get_settings

        from cli.process_registry import kill_all_best_effort
    except ImportError:
        print(
            "Erro: O modo servidor requer dependencias adicionais.\n"
            "Instale com: pip install vertex-cli[server]"
        )
        sys.exit(1)

    settings = get_settings()
    try:
        uvicorn.run(
            "api.app:create_app",
            factory=True,
            host=settings.host,
            port=settings.port,
            log_level="debug",
            timeout_graceful_shutdown=5,
        )
    finally:
        kill_all_best_effort()


def init() -> None:
    """Scaffold config at ~/.config/vertex/.env (registered as `vertex-init`)."""
    if ENV_FILE.exists():
        print(f"Configuracao ja existe em {ENV_FILE}")
        print("Apague esse arquivo primeiro se quiser recriar do zero.")
        return

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    template = _load_env_template()
    ENV_FILE.write_text(template, encoding="utf-8")
    print(f"Configuracao criada em {ENV_FILE}")

    from cli.setup_wizard import run_login_wizard

    answer = input("Fazer login agora? [S/n]: ").strip().lower()
    if answer in ("", "s", "sim", "y", "yes"):
        run_login_wizard()
        print("\n✓ Login realizado. Rode: vertex")
    else:
        print("\nDepois faca login com: vertex auth login")
