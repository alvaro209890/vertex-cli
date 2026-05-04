from __future__ import annotations

from pathlib import Path


def _vertex_cli_bundle() -> str:
    return (
        Path(__file__).resolve().parents[2]
        / "vendor"
        / "vertex-cli"
        / "dist"
        / "cli.mjs"
    ).read_text(encoding="utf-8")


def test_deepseek_supports_max_effort_in_vendored_cli() -> None:
    text = _vertex_cli_bundle()

    assert "function isDeepSeekEffortModel(model)" in text
    assert "if (isDeepSeekEffortModel(model)) {\n    return true;\n  }" in text


def test_effort_help_does_not_limit_max_to_opus() -> None:
    text = _vertex_cli_bundle()

    assert "- max: Maximum capability with deepest reasoning" in text
    assert "Maximum capability with deepest reasoning (Opus 4.6 only)" not in text
    assert "Vertex/DeepSeek model" in text
