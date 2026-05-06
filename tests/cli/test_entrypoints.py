"""Tests for cli/entrypoints.py — vertex entrypoint logic."""

import os
from contextlib import suppress
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError


def _run_init(tmp_home: Path) -> tuple[str, Path]:
    """Run init() with home directory redirected to tmp_home. Returns (printed output, env_file path)."""
    from cli import entrypoints

    config_dir = tmp_home / ".config" / "vertex"
    env_file = tmp_home / ".config" / "vertex" / ".env"
    printed: list[str] = []

    with (
        patch.object(entrypoints, "CONFIG_DIR", config_dir),
        patch.object(entrypoints, "ENV_FILE", env_file),
        patch(
            "builtins.print",
            side_effect=lambda *a: printed.append(" ".join(str(x) for x in a)),
        ),
        patch("builtins.input", return_value="n"),
    ):
        entrypoints.init()

    return "\n".join(printed), env_file


def test_init_creates_env_file(tmp_path: Path) -> None:
    """init() creates .env from the bundled template when it doesn't exist yet."""
    output, env_file = _run_init(tmp_path)

    assert env_file.exists()
    assert env_file.stat().st_size > 0
    assert str(env_file) in output


def test_init_copies_template_content(tmp_path: Path) -> None:
    """init() writes the canonical root env.example content, not an empty file."""
    template = (Path(__file__).resolve().parents[2] / ".env.example").read_text(
        encoding="utf-8"
    )
    _, env_file = _run_init(tmp_path)

    assert env_file.read_text("utf-8") == template


def test_env_template_loader_uses_root_template_in_source_checkout() -> None:
    """Source checkout fallback uses the root .env.example as the single source."""
    from cli.entrypoints import _load_env_template

    template = (Path(__file__).resolve().parents[2] / ".env.example").read_text(
        encoding="utf-8"
    )

    assert _load_env_template() == template


def test_init_creates_parent_directories(tmp_path: Path) -> None:
    """init() creates ~/.config/vertex/ even if it doesn't exist."""
    config_dir = tmp_path / ".config" / "vertex"
    assert not config_dir.exists()

    _run_init(tmp_path)

    assert config_dir.is_dir()


def test_init_skips_if_env_already_exists(tmp_path: Path) -> None:
    """init() does not overwrite an existing .env and prints a warning."""
    # Create it first
    _run_init(tmp_path)

    env_file = tmp_path / ".config" / "vertex" / ".env"
    env_file.write_text("existing content", encoding="utf-8")

    output, _ = _run_init(tmp_path)

    assert env_file.read_text("utf-8") == "existing content"
    assert "Configuracao ja existe" in output


def test_init_prints_next_step_hint(tmp_path: Path) -> None:
    """init() tells the user to run vertex after editing .env."""
    output, _ = _run_init(tmp_path)

    assert "vertex" in output


def test_vertex_cli_bin_defaults_to_vendored_runtime() -> None:
    """vertex resolves its own vendored CLI runtime, not an openclaude binary."""
    from cli.entrypoints import _vertex_cli_bin

    with patch.dict(os.environ, {}, clear=True):
        assert _vertex_cli_bin().as_posix().endswith("vendor/vertex-cli/bin/vertex")


def test_vertex_cli_bin_allows_explicit_override(tmp_path: Path) -> None:
    """VERTEX_CLI_BIN can point tests or custom installs at another runtime."""
    from cli.entrypoints import _vertex_cli_bin

    override = tmp_path / "vertex"
    with patch.dict(os.environ, {"VERTEX_CLI_BIN": str(override)}):
        assert _vertex_cli_bin() == override


def test_ensure_vertex_cli_state_file_repairs_empty_json(tmp_path: Path) -> None:
    """An empty .claude.json is replaced before the vendored Node CLI parses it."""
    from cli import entrypoints

    config_dir = tmp_path / ".vertex"
    state_file = config_dir / ".claude.json"
    config_dir.mkdir()
    state_file.write_text("", encoding="utf-8")

    with patch.object(entrypoints, "VERTEX_CLI_CONFIG_DIR", config_dir):
        entrypoints._ensure_vertex_cli_state_file()

    assert state_file.read_text(encoding="utf-8") == "{}\n"
    assert state_file.stat().st_mode & 0o777 == 0o600


def test_cli_launches_vendored_vertex_runtime(tmp_path: Path) -> None:
    """cli() launches the vendored runtime for version checks without startup."""
    import sys

    from cli import entrypoints

    vertex_bin = tmp_path / "vertex"
    vertex_bin.write_text("#!/usr/bin/env node\n", encoding="utf-8")
    node_bin = tmp_path / "node"
    node_bin.write_text("", encoding="utf-8")

    with (
        patch.object(entrypoints, "_run_auth_wizard_if_needed") as wizard,
        patch.object(entrypoints, "_start_proxy", return_value=True) as start_proxy,
        patch.object(entrypoints, "_node_bin", return_value=str(node_bin)),
        patch.dict(os.environ, {"VERTEX_CLI_BIN": str(vertex_bin)}, clear=False),
        patch.object(sys, "argv", ["vertex", "--version"]),
        patch("subprocess.run") as run,
        patch("sys.exit", side_effect=SystemExit) as exit_,
    ):
        run.return_value.returncode = 7
        with suppress(SystemExit):
            entrypoints.cli()

    run.assert_called_once()
    assert run.call_args.args[0] == [str(node_bin), str(vertex_bin), "--version"]
    assert "env" not in run.call_args.kwargs
    wizard.assert_not_called()
    start_proxy.assert_not_called()
    exit_.assert_called_once_with(7)


def test_cli_version_does_not_print_launching_banner(tmp_path: Path) -> None:
    """`vertex --version` should only show the vendored CLI version output."""
    import sys

    from cli import entrypoints

    vertex_bin = tmp_path / "vertex"
    vertex_bin.write_text("#!/usr/bin/env node\n", encoding="utf-8")
    node_bin = tmp_path / "node"
    node_bin.write_text("", encoding="utf-8")
    printed: list[str] = []

    with (
        patch.object(entrypoints, "_run_auth_wizard_if_needed") as wizard,
        patch.object(entrypoints, "_start_proxy", return_value=True) as start_proxy,
        patch.object(entrypoints, "_node_bin", return_value=str(node_bin)),
        patch.dict(os.environ, {"VERTEX_CLI_BIN": str(vertex_bin)}, clear=False),
        patch.object(sys, "argv", ["vertex", "--version"]),
        patch(
            "builtins.print",
            side_effect=lambda *a: printed.append(" ".join(str(x) for x in a)),
        ),
        patch("subprocess.run") as run,
        patch("sys.exit", side_effect=SystemExit),
    ):
        run.return_value.returncode = 0
        with suppress(SystemExit):
            entrypoints.cli()

    assert "Launching Vertex CLI..." not in printed
    wizard.assert_not_called()
    start_proxy.assert_not_called()


def test_cli_creates_default_vertex_settings(tmp_path: Path) -> None:
    """cli() connects to remote server by default (no local proxy)."""
    import sys

    from cli import entrypoints

    vertex_bin = tmp_path / "vertex"
    vertex_bin.write_text("#!/usr/bin/env node\n", encoding="utf-8")
    node_bin = tmp_path / "node"
    node_bin.write_text("", encoding="utf-8")
    settings_file = tmp_path / ".vertex" / "settings.json"

    with (
        patch.object(entrypoints, "_run_auth_wizard_if_needed"),
        patch.object(
            entrypoints, "_ensure_remote_account_active", return_value="firebase-token"
        ),
        patch.object(entrypoints, "_node_bin", return_value=str(node_bin)),
        patch.object(entrypoints, "VERTEX_CLI_CONFIG_DIR", settings_file.parent),
        patch.object(entrypoints, "VERTEX_CLI_SETTINGS_FILE", settings_file),
        patch.dict(os.environ, {"VERTEX_CLI_BIN": str(vertex_bin)}, clear=False),
        patch.object(sys, "argv", ["vertex"]),
        patch("subprocess.run") as run,
        patch("sys.exit", side_effect=SystemExit),
        suppress(SystemExit),
    ):
        run.return_value.returncode = 0
        entrypoints.cli()

    # Modo remoto padrao: usa proxy de forwarding local (porta 8084)
    env = run.call_args.kwargs["env"]
    assert env["ANTHROPIC_BASE_URL"] == f"http://127.0.0.1:{entrypoints.REMOTE_PROXY_PORT}"
    assert env["ANTHROPIC_AUTH_TOKEN"] == "freecc"


def test_cli_local_proxy_mode(tmp_path: Path) -> None:
    """VERTEX_LOCAL_PROXY=true usa proxy local."""
    import sys

    from cli import entrypoints

    vertex_bin = tmp_path / "vertex"
    vertex_bin.write_text("#!/usr/bin/env node\n", encoding="utf-8")
    node_bin = tmp_path / "node"
    node_bin.write_text("", encoding="utf-8")
    settings_file = tmp_path / ".vertex" / "settings.json"

    with (
        patch.object(entrypoints, "_run_auth_wizard_if_needed"),
        patch.object(entrypoints, "_start_proxy", return_value=True),
        patch.object(entrypoints, "_ensure_vertex_cli_settings"),
        patch.object(entrypoints, "_node_bin", return_value=str(node_bin)),
        patch.object(entrypoints, "VERTEX_CLI_CONFIG_DIR", settings_file.parent),
        patch.object(entrypoints, "VERTEX_CLI_SETTINGS_FILE", settings_file),
        patch.dict(
            os.environ,
            {"VERTEX_CLI_BIN": str(vertex_bin), "VERTEX_LOCAL_PROXY": "true"},
            clear=False,
        ),
        patch.object(sys, "argv", ["vertex"]),
        patch("subprocess.run") as run,
        patch("sys.exit", side_effect=SystemExit),
        suppress(SystemExit),
    ):
        run.return_value.returncode = 0
        entrypoints.cli()

    env = run.call_args.kwargs["env"]
    assert "127.0.0.1" in env["ANTHROPIC_BASE_URL"]


def test_cli_overwrites_stale_openclaude_settings(tmp_path: Path) -> None:
    """cli remote mode uses VERTEX_API_URL regardless of stale settings file."""
    import json
    import sys

    from cli import entrypoints

    vertex_bin = tmp_path / "vertex"
    vertex_bin.write_text("#!/usr/bin/env node\n", encoding="utf-8")
    node_bin = tmp_path / "node"
    node_bin.write_text("", encoding="utf-8")
    settings_file = tmp_path / ".vertex" / "settings.json"
    settings_file.parent.mkdir(parents=True)
    settings_file.write_text(
        json.dumps(
            {
                "env": {
                    "ANTHROPIC_BASE_URL": "https://api.anthropic.com",
                    "OPENAI_API_KEY": "old-openai-key",
                },
                "model": "other/model",
                "provider": "openclaude",
                "customSetting": True,
            }
        ),
        encoding="utf-8",
    )

    with (
        patch.object(entrypoints, "_run_auth_wizard_if_needed"),
        patch.object(
            entrypoints, "_ensure_remote_account_active", return_value="firebase-token"
        ),
        patch.object(entrypoints, "_node_bin", return_value=str(node_bin)),
        patch.object(entrypoints, "VERTEX_CLI_CONFIG_DIR", settings_file.parent),
        patch.object(entrypoints, "VERTEX_CLI_SETTINGS_FILE", settings_file),
        patch.dict(os.environ, {"VERTEX_CLI_BIN": str(vertex_bin)}, clear=False),
        patch.object(sys, "argv", ["vertex"]),
        patch("subprocess.run") as run,
        patch("sys.exit", side_effect=SystemExit),
        suppress(SystemExit),
    ):
        run.return_value.returncode = 0
        entrypoints.cli()

    # Modo remoto: usa proxy de forwarding local (porta 8084)
    env = run.call_args.kwargs["env"]
    expected_url = f"http://127.0.0.1:{entrypoints.REMOTE_PROXY_PORT}"
    assert env["ANTHROPIC_BASE_URL"] == expected_url
    assert env["ANTHROPIC_AUTH_TOKEN"] == "freecc"
    assert env["DISABLE_LOGIN_COMMAND"] == "1"

    settings = json.loads(settings_file.read_text(encoding="utf-8"))
    assert settings["env"]["ANTHROPIC_BASE_URL"] == expected_url
    assert settings["env"]["ANTHROPIC_AUTH_TOKEN"] == "freecc"
    assert settings["env"]["DISABLE_LOGIN_COMMAND"] == "1"
    assert "OPENAI_API_KEY" not in settings["env"]
    assert "provider" not in settings


def test_start_proxy_reuses_matching_running_proxy() -> None:
    """A matching proxy version is reused."""
    from cli import entrypoints

    expected_fingerprint = "abcdef1234567890"
    with (
        patch.object(entrypoints, "_installed_vertex_version", return_value="1.1.6"),
        patch.object(
            entrypoints,
            "_proxy_settings_fingerprint",
            return_value=expected_fingerprint,
        ),
        patch.object(
            entrypoints,
            "_read_proxy_health",
            return_value={
                "status": "healthy",
                "version": "1.1.6",
                "settings_fingerprint": expected_fingerprint,
            },
        ),
        patch.object(entrypoints, "_terminate_vertex_proxy_processes") as terminate,
        patch.object(entrypoints, "_wait_for_proxy_down") as wait_down,
        patch("subprocess.Popen") as popen,
    ):
        assert entrypoints._start_proxy() is True

    terminate.assert_not_called()
    wait_down.assert_not_called()
    popen.assert_not_called()


def test_start_proxy_restarts_stale_running_proxy() -> None:
    """A running proxy without the installed version is terminated and replaced."""
    from cli import entrypoints

    expected_fingerprint = "abcdef1234567890"
    with (
        patch.object(entrypoints, "_installed_vertex_version", return_value="1.1.6"),
        patch.object(
            entrypoints,
            "_proxy_settings_fingerprint",
            return_value=expected_fingerprint,
        ),
        patch.object(
            entrypoints,
            "_read_proxy_health",
            return_value={
                "status": "healthy",
                "version": "1.1.5",
                "settings_fingerprint": expected_fingerprint,
            },
        ),
        patch.object(
            entrypoints, "_terminate_vertex_proxy_processes", return_value=1
        ) as terminate,
        patch.object(entrypoints, "_wait_for_proxy_down") as wait_down,
        patch.object(entrypoints, "_wait_for_proxy_health", return_value=True),
        patch("subprocess.Popen") as popen,
    ):
        assert entrypoints._start_proxy() is True

    terminate.assert_called_once()
    wait_down.assert_called_once_with("8083")
    popen.assert_called_once()
    assert popen.call_args.kwargs["env"]["PORT"] == "8083"


def test_cli_logout_clears_auth(tmp_path: Path) -> None:
    """`vertex /logout` clears Firebase auth and prints confirmation."""
    import sys

    from cli import entrypoints
    from vertex_auth import client as auth_client
    from vertex_auth.client import save_auth

    auth_file = tmp_path / "auth.json"

    # Pre-authenticate by saving a fake token
    with patch.object(auth_client, "AUTH_FILE", auth_file):
        save_auth("test-id-token", "test-refresh-token", 3600, "test@example.com")

    printed: list[str] = []

    with (
        patch.object(auth_client, "AUTH_FILE", auth_file),
        patch.object(sys, "argv", ["vertex", "/logout"]),
        patch(
            "builtins.print",
            side_effect=lambda *a: printed.append(" ".join(str(x) for x in a)),
        ),
        patch("subprocess.run") as run,
    ):
        entrypoints.cli()

    run.assert_not_called()
    assert not auth_file.exists()
    assert "Logout realizado" in "\n".join(printed)


def test_cli_auth_login_runs_setup_wizard(tmp_path: Path) -> None:
    """`vertex auth login` runs the interactive login wizard."""
    import sys

    from cli import entrypoints

    printed: list[str] = []

    with (
        patch.object(sys, "argv", ["vertex", "auth", "login"]),
        patch(
            "builtins.print",
            side_effect=lambda *a: printed.append(" ".join(str(x) for x in a)),
        ),
        patch("builtins.input", side_effect=["", ""]),
        patch("subprocess.run") as run,
    ):
        entrypoints.cli()

    run.assert_not_called()
    output = "\n".join(printed)
    assert "Bem-vindo ao Vertex" in output


def test_cli_auth_status_reports_not_authenticated(tmp_path: Path) -> None:
    """`vertex auth status` reports not authenticated when no valid token."""
    import sys

    from cli import entrypoints
    from vertex_auth import client as auth_client

    auth_file = tmp_path / "auth.json"
    printed: list[str] = []

    with (
        patch.object(auth_client, "AUTH_FILE", auth_file),
        patch.object(sys, "argv", ["vertex", "auth", "status"]),
        patch(
            "builtins.print",
            side_effect=lambda *a: printed.append(" ".join(str(x) for x in a)),
        ),
        patch("subprocess.run") as run,
    ):
        entrypoints.cli()

    run.assert_not_called()
    output = "\n".join(printed)
    assert "Nao autenticado" in output
    assert "Use `vertex auth login`" in output


def test_cli_auth_status_reports_authenticated(tmp_path: Path) -> None:
    """`vertex auth status` reports email when authenticated."""
    import sys

    from cli import entrypoints
    from vertex_auth import client as auth_client

    auth_file = tmp_path / "auth.json"

    printed: list[str] = []

    with (
        patch.object(auth_client, "AUTH_FILE", auth_file),
        patch.object(sys, "argv", ["vertex", "auth", "status"]),
        patch(
            "builtins.print",
            side_effect=lambda *a: printed.append(" ".join(str(x) for x in a)),
        ),
        patch("subprocess.run") as run,
    ):
        # Pre-write auth data so the status shows as authenticated
        import json
        import time

        auth_file.parent.mkdir(parents=True, exist_ok=True)
        auth_file.write_text(
            json.dumps(
                {
                    "id_token": "test-id-token",
                    "refresh_token": "test-refresh-token",
                    "expires_at": time.time() + 3600,
                    "email": "user@example.com",
                }
            ),
            encoding="utf-8",
        )
        entrypoints.cli()

    run.assert_not_called()
    output = "\n".join(printed)
    assert "Autenticado como user@example.com" in output


def test_remote_account_check_uses_cli_user_agent() -> None:
    """Remote status checks should avoid Cloudflare blocking urllib defaults."""
    from cli import entrypoints

    response = MagicMock()
    response.read.return_value = b"{}"
    with (
        patch.object(entrypoints, "_installed_vertex_version", return_value="1.2.3"),
        patch("vertex_auth.get_valid_token", return_value="test-token"),
        patch("urllib.request.urlopen", return_value=response) as urlopen,
    ):
        token = entrypoints._ensure_remote_account_active()

    req = urlopen.call_args.args[0]
    assert token == "test-token"
    assert req.get_header("User-agent") == "Vertex CLI/1.2.3"
    assert req.get_header("Accept") == "application/json"
    response.close.assert_called_once()


def test_update_check_returns_highest_available_version() -> None:
    """Returns the highest version between the API and GitHub."""
    from cli import entrypoints

    with (
        patch.object(entrypoints, "_fetch_latest_version_from_api", return_value="1.2.5"),
        patch.object(
            entrypoints, "_fetch_latest_version_from_github", return_value="1.2.6"
        ),
    ):
        # GitHub has higher version, should be returned
        assert entrypoints._get_latest_version() == "1.2.6"

    with (
        patch.object(entrypoints, "_fetch_latest_version_from_api", return_value="1.2.6"),
        patch.object(
            entrypoints, "_fetch_latest_version_from_github", return_value="1.2.4"
        ),
    ):
        # API has higher version, should be returned
        assert entrypoints._get_latest_version() == "1.2.6"


def test_remote_account_check_exits_when_credits_are_empty() -> None:
    """Remote mode should stop before launching when the account has no balance."""
    import sys

    from cli import entrypoints

    response = MagicMock()
    response.read.return_value = b'{"credits":{"balance":0}}'
    printed: list[str] = []

    with (
        patch("vertex_auth.get_valid_token", return_value="test-token"),
        patch("urllib.request.urlopen", return_value=response),
        patch.object(sys, "argv", ["vertex"]),
        patch("sys.exit", side_effect=SystemExit) as exit_,
        patch(
            "builtins.print",
            side_effect=lambda *a: printed.append(" ".join(str(x) for x in a)),
        ),
        suppress(SystemExit),
    ):
        entrypoints._ensure_remote_account_active()

    exit_.assert_called_once_with(1)
    assert "Saldo insuficiente" in "\n".join(printed)
    assert entrypoints.VERTEX_WEB_URL in "\n".join(printed)
    response.close.assert_called_once()


def test_remote_account_check_ignores_non_account_403() -> None:
    """A Cloudflare/WAF 403 must not be reported as a blocked account."""
    from cli import entrypoints

    printed: list[str] = []
    error = HTTPError(
        entrypoints.VERTEX_API_URL,
        403,
        "Forbidden",
        {},
        BytesIO(b"error code: 1010"),
    )

    with (
        patch("vertex_auth.get_valid_token", return_value="test-token"),
        patch("urllib.request.urlopen", side_effect=error),
        patch("sys.exit", side_effect=AssertionError("should not exit")) as exit_,
        patch(
            "builtins.print",
            side_effect=lambda *a: printed.append(" ".join(str(x) for x in a)),
        ),
    ):
        entrypoints._ensure_remote_account_active()

    exit_.assert_not_called()
    assert "Aviso: nao foi possivel confirmar o status da conta (403)." in "\n".join(
        printed
    )


def test_remote_account_check_exits_on_explicit_account_block() -> None:
    """Explicit backend account blocks still stop the CLI."""
    import sys

    from cli import entrypoints

    error = HTTPError(
        entrypoints.VERTEX_API_URL,
        403,
        "Forbidden",
        {},
        BytesIO(b'{"error":"Conta bloqueada"}'),
    )

    with (
        patch("vertex_auth.get_valid_token", return_value="test-token"),
        patch("urllib.request.urlopen", side_effect=error),
        patch.object(sys, "argv", ["vertex"]),
        patch("sys.exit", side_effect=SystemExit) as exit_,
        patch("builtins.print"),
        suppress(SystemExit),
    ):
        entrypoints._ensure_remote_account_active()

    exit_.assert_called_once_with(1)


def test_remote_account_check_exits_on_structured_account_block() -> None:
    """Structured backend block payloads should also stop the CLI."""
    import sys

    from cli import entrypoints

    error = HTTPError(
        entrypoints.VERTEX_API_URL,
        403,
        "Forbidden",
        {},
        BytesIO(b'{"detail":{"code":"account_blocked","message":"blocked"}}'),
    )

    with (
        patch("vertex_auth.get_valid_token", return_value="test-token"),
        patch("urllib.request.urlopen", side_effect=error),
        patch.object(sys, "argv", ["vertex"]),
        patch("sys.exit", side_effect=SystemExit) as exit_,
        patch("builtins.print"),
        suppress(SystemExit),
    ):
        entrypoints._ensure_remote_account_active()

    exit_.assert_called_once_with(1)


def test_install_script_uses_vertex_cli_repository() -> None:
    """The public installer must install the vertex-cli repository."""
    script = (
        Path(__file__).resolve().parents[2] / "scripts" / "install-vertex.sh"
    ).read_text(encoding="utf-8")

    assert "github.com/alvaro209890/vertex-cli.git" in script
    assert "github.com/alvaro209890/Vertex.git" not in script


def test_setup_wizard_screen_is_portuguese(tmp_path: Path, capsys) -> None:
    """The first-run setup wizard should be user-facing Portuguese."""
    from cli.setup_wizard import run_setup_wizard

    with patch("builtins.input", side_effect=["", ""]):
        run_setup_wizard(tmp_path / ".env")

    output = capsys.readouterr().out
    assert "Bem-vindo ao Vertex" in output
    assert "O Vertex agora usa autenticacao por email/senha" in output


def test_cli_blocks_anthropic_setup_token() -> None:
    """The Anthropic token/OAuth setup command is forwarded to the vendored CLI."""
    import sys

    from cli import entrypoints

    with (
        patch.object(sys, "argv", ["vertex", "setup-token"]),
        patch.object(entrypoints, "_run_auth_wizard_if_needed"),
        patch.object(
            entrypoints, "_ensure_remote_account_active", return_value="firebase-token"
        ),
        patch.object(entrypoints, "_start_proxy", return_value=True),
        patch.object(entrypoints, "_node_bin", return_value="/usr/bin/node"),
        patch.object(entrypoints, "_ensure_vertex_cli_settings"),
        patch("subprocess.run") as run,
        patch("sys.exit", side_effect=SystemExit),
        suppress(SystemExit),
    ):
        entrypoints.cli()

    run.assert_called_once()
    args = run.call_args.args[0]
    assert "setup-token" in args
