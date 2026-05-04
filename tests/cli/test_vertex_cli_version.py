from __future__ import annotations

import json
from pathlib import Path


def test_vendored_vertex_cli_version_matches_python_package() -> None:
    repo = Path(__file__).resolve().parents[2]
    pyproject = (repo / "pyproject.toml").read_text(encoding="utf-8")
    cli_bundle = (repo / "vendor" / "vertex-cli" / "dist" / "cli.mjs").read_text(
        encoding="utf-8"
    )
    cli_package = json.loads(
        (repo / "vendor" / "vertex-cli" / "package.json").read_text(encoding="utf-8")
    )

    assert 'version = "1.2.2"' in pyproject
    assert cli_package["version"] == "1.2.2"
    assert 'version("1.2.2 (Vertex)"' in cli_bundle
    assert 'console.log(`${"1.2.2"} (Vertex)`)' in cli_bundle
    assert 'vertex ${RESET}${rgb(...ACCENT)}v${"1.2.2"}' in cli_bundle
    assert 'vertex ${RESET}${rgb(...ACCENT)}v${"1.0.0"}' not in cli_bundle
    assert (
        'return { name: "Vertex", model: resolvedModel, baseUrl: anthropicBaseUrl, isLocal: true };'
        in cli_bundle
    )


def test_vendored_vertex_cli_status_colors_are_green() -> None:
    repo = Path(__file__).resolve().parents[2]
    cli_bundle = (repo / "vendor" / "vertex-cli" / "dist" / "cli.mjs").read_text(
        encoding="utf-8"
    )

    assert 'const defaultColor = "claude";' in cli_bundle
    assert 'const defaultShimmerColor = "claudeShimmer";' in cli_bundle
    assert 'claude: "ansi:green"' in cli_bundle
    assert 'claudeShimmer: "ansi:greenBright"' in cli_bundle
    assert 'claude: "rgb(44,122,57)"' in cli_bundle
    assert 'claudeShimmer: "rgb(78,186,101)"' in cli_bundle
    assert 'color: "success",\n        fading,\n        tail: "right"' in cli_bundle
    assert 'color: "success",\n      fading: t4,\n      tail: "down"' in cli_bundle


def test_vendored_vertex_cli_has_pt_br_work_status_text() -> None:
    repo = Path(__file__).resolve().parents[2]
    cli_bundle = (repo / "vendor" / "vertex-cli" / "dist" / "cli.mjs").read_text(
        encoding="utf-8"
    )

    assert '"Pensando"' in cli_bundle
    assert '"Respondendo"' in cli_bundle
    assert "`pensando${effortSuffix}`" in cli_bundle
    assert (
        "`pensou por ${Math.max(1, Math.round(thinkingStatus / 1000))}s`" in cli_bundle
    )
    assert '"∴ Pensando"' in cli_bundle
    assert '"✻ Pensando…"' in cli_bundle
    assert '"Carregando sessoes do Vertex…"' in cli_bundle
    assert '" Retomando conversa…"' in cli_bundle
    assert '"Dica: voce pode iniciar o Vertex apenas com `vertex`"' in cli_bundle
    assert '"Accomplishing"' not in cli_bundle
    assert '"Loading Vertex sessions…"' not in cli_bundle
    assert '"Tip: You can launch Vertex with just `vertex`"' not in cli_bundle


def test_vendored_vertex_cli_identity_mentions_creator_and_deepseek() -> None:
    repo = Path(__file__).resolve().parents[2]
    cli_bundle = (repo / "vendor" / "vertex-cli" / "dist" / "cli.mjs").read_text(
        encoding="utf-8"
    )

    assert "created by Alvaro Emanuel Alves Araujo" in cli_bundle
    assert "You are not Anthropic" in cli_bundle
    assert (
        "Vertex runs DeepSeek models through a local Anthropic-compatible proxy"
        in cli_bundle
    )
    assert "You are Claude Code, an AI assistant that orchestrates" not in cli_bundle


def test_vendored_vertex_cli_core_slash_commands_are_pt_br() -> None:
    repo = Path(__file__).resolve().parents[2]
    cli_bundle = (repo / "vendor" / "vertex-cli" / "dist" / "cli.mjs").read_text(
        encoding="utf-8"
    )

    assert 'description: "Adicionar um novo diretorio de trabalho"' in cli_bundle
    assert 'description: "Abrir painel de configuracao"' in cli_bundle
    assert 'description: "Mostrar ajuda e comandos disponiveis"' in cli_bundle
    assert 'description: "Gerenciar servidores MCP"' in cli_bundle
    assert 'description: "Limpar a chave DeepSeek"' in cli_bundle
    assert 'description: "Gerenciar plugins do Vertex"' in cli_bundle
    assert 'progressMessage: "buscando comentarios do PR"' in cli_bundle
    assert 'argumentHint: "<instrucoes opcionais para o resumo>"' in cli_bundle

    assert 'description: "Add a new working directory"' not in cli_bundle
    assert 'description: "Open config panel"' not in cli_bundle
    assert 'description: "Show help and available commands"' not in cli_bundle
    assert 'description: "Manage MCP servers"' not in cli_bundle
    assert 'description: "Clear the DeepSeek API key"' not in cli_bundle
    assert 'description: "Manage Claude Code plugins"' not in cli_bundle
