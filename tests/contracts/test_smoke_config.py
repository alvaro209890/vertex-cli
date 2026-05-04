from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from smoke.lib.config import (
    DEFAULT_TARGETS,
    PROVIDER_SMOKE_DEFAULT_MODELS,
    SmokeConfig,
)


def _settings(**overrides):
    values = {
        "model": "deepseek/deepseek-v4-flash",
        "model_opus": None,
        "model_sonnet": None,
        "model_haiku": None,
        "deepseek_api_key": "",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _smoke_config(**overrides) -> SmokeConfig:
    values = {
        "root": Path("."),
        "results_dir": Path(".smoke-results"),
        "live": False,
        "interactive": False,
        "targets": DEFAULT_TARGETS,
        "provider_matrix": frozenset(),
        "timeout_s": 45.0,
        "prompt": "Reply with exactly: FCC_SMOKE_PONG",
        "claude_bin": "claude",
        "worker_id": "main",
        "settings": _settings(),
    }
    values.update(overrides)
    return SmokeConfig(**values)


def test_deepseek_is_default_smoke_target() -> None:
    assert "deepseek" in DEFAULT_TARGETS


def test_deepseek_provider_configuration_uses_api_key() -> None:
    config = _smoke_config(
        settings=_settings(deepseek_api_key="sk-test"),
    )

    assert config.has_provider_configuration("deepseek")
    assert config.provider_models()[0].full_model == "deepseek/deepseek-v4-flash"


def test_deepseek_provider_matrix_filters_models() -> None:
    config = _smoke_config(
        settings=_settings(deepseek_api_key="sk-test"),
        provider_matrix=frozenset({"deepseek"}),
    )

    assert [model.provider for model in config.provider_models()] == ["deepseek"]


def test_provider_smoke_models_cover_configured_providers_independent_of_model_mapping(
    monkeypatch,
) -> None:
    monkeypatch.delenv("FCC_SMOKE_MODEL_DEEPSEEK", raising=False)
    config = _smoke_config(
        settings=_settings(
            model="deepseek/deepseek-v4-flash",
            deepseek_api_key="deepseek-key",
        )
    )

    models = config.provider_smoke_models()

    assert [model.provider for model in models] == ["deepseek"]
    assert models[0].full_model == PROVIDER_SMOKE_DEFAULT_MODELS["deepseek"]
    assert models[0].source == "provider_default"


def test_provider_smoke_model_override_accepts_model_name_without_prefix(
    monkeypatch,
) -> None:
    monkeypatch.setenv("FCC_SMOKE_MODEL_DEEPSEEK", "deepseek-reasoner")
    config = _smoke_config(
        settings=_settings(
            deepseek_api_key="deepseek-key",
        ),
        provider_matrix=frozenset({"deepseek"}),
    )

    models = config.provider_smoke_models()

    assert models[0].full_model == "deepseek/deepseek-reasoner"
    assert models[0].source == "FCC_SMOKE_MODEL_DEEPSEEK"


def test_provider_smoke_model_override_rejects_wrong_provider_prefix(
    monkeypatch,
) -> None:
    monkeypatch.setenv("FCC_SMOKE_MODEL_DEEPSEEK", "other/model")
    config = _smoke_config(
        settings=_settings(
            deepseek_api_key="deepseek-key",
        ),
        provider_matrix=frozenset({"deepseek"}),
    )

    try:
        config.provider_smoke_models()
    except ValueError as exc:
        assert "FCC_SMOKE_MODEL_DEEPSEEK" in str(exc)
    else:
        raise AssertionError("expected wrong provider prefix to fail")


def test_provider_smoke_matrix_filters_provider_catalog(monkeypatch) -> None:
    monkeypatch.delenv("FCC_SMOKE_MODEL_DEEPSEEK", raising=False)
    config = _smoke_config(
        settings=_settings(
            deepseek_api_key="deepseek-key",
        ),
        provider_matrix=frozenset({"deepseek"}),
    )

    assert [model.provider for model in config.provider_smoke_models()] == ["deepseek"]


def test_provider_smoke_does_not_include_unmapped_providers_without_config(
    monkeypatch,
) -> None:
    monkeypatch.delenv("FCC_SMOKE_MODEL_DEEPSEEK", raising=False)
    config = _smoke_config(settings=_settings(model="deepseek/deepseek-v4-flash"))

    assert config.provider_smoke_models() == []
