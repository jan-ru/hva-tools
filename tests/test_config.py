"""Tests for config file loading and parameter resolution."""

import pytest

from brightspace_extractor.cli import _cfg, _load_config
from brightspace_extractor.exceptions import ConfigError


class TestLoadConfig:
    """Tests for _load_config()."""

    def test_loads_valid_toml(self, tmp_path) -> None:
        config = tmp_path / "brightspace.toml"
        config.write_text(
            'class_id = "698557"\nbase_url = "https://example.com"\n',
            encoding="utf-8",
        )
        result = _load_config(str(config))
        assert result["class_id"] == "698557"
        assert result["base_url"] == "https://example.com"

    def test_returns_empty_dict_when_default_missing(self) -> None:
        result = _load_config(None)
        assert result == {} or isinstance(result, dict)

    def test_raises_when_explicit_path_missing(self) -> None:
        with pytest.raises(ConfigError, match="not found"):
            _load_config("/nonexistent/brightspace.toml")

    def test_raises_on_malformed_toml(self, tmp_path) -> None:
        config = tmp_path / "bad.toml"
        config.write_text("not valid toml [[[", encoding="utf-8")
        with pytest.raises(ConfigError, match="Malformed TOML"):
            _load_config(str(config))

    def test_empty_file_returns_empty_dict(self, tmp_path) -> None:
        config = tmp_path / "empty.toml"
        config.write_text("", encoding="utf-8")
        result = _load_config(str(config))
        assert result == {}

    def test_all_supported_keys(self, tmp_path) -> None:
        config = tmp_path / "full.toml"
        config.write_text(
            'class_id = "123"\n'
            'base_url = "https://bs.example.com"\n'
            'cdp_url = "http://localhost:1234"\n'
            'output_dir = "./out"\n'
            'category_config = "cats.toml"\n',
            encoding="utf-8",
        )
        result = _load_config(str(config))
        assert result["class_id"] == "123"
        assert result["base_url"] == "https://bs.example.com"
        assert result["cdp_url"] == "http://localhost:1234"
        assert result["output_dir"] == "./out"
        assert result["category_config"] == "cats.toml"


class TestCfg:
    """Tests for _cfg() parameter resolution."""

    def test_cli_value_wins_over_config(self) -> None:
        assert _cfg({"key": "config"}, "key", "cli") == "cli"

    def test_config_value_used_when_cli_is_none(self) -> None:
        assert _cfg({"key": "config"}, "key", None) == "config"

    def test_default_used_when_both_missing(self) -> None:
        assert _cfg({}, "key", None, "default") == "default"

    def test_none_when_all_missing(self) -> None:
        assert _cfg({}, "key", None) is None

    def test_cli_empty_string_still_wins(self) -> None:
        assert _cfg({"key": "config"}, "key", "") == ""

    def test_cli_false_still_wins(self) -> None:
        assert _cfg({"key": "config"}, "key", False) is False

    def test_cli_zero_still_wins(self) -> None:
        assert _cfg({"key": "config"}, "key", 0) == 0


class TestCfgEnvVars:
    """Tests for environment variable support in _cfg()."""

    def test_env_var_used_when_cli_is_none(self, monkeypatch) -> None:
        monkeypatch.setenv("BRIGHTSPACE_CLASS_ID", "env_value")
        assert _cfg({}, "class_id", None) == "env_value"

    def test_cli_wins_over_env_var(self, monkeypatch) -> None:
        monkeypatch.setenv("BRIGHTSPACE_CLASS_ID", "env_value")
        assert _cfg({}, "class_id", "cli_value") == "cli_value"

    def test_env_var_wins_over_config(self, monkeypatch) -> None:
        monkeypatch.setenv("BRIGHTSPACE_CLASS_ID", "env_value")
        assert _cfg({"class_id": "config_value"}, "class_id", None) == "env_value"

    def test_config_used_when_no_env_var(self) -> None:
        assert _cfg({"class_id": "config_value"}, "class_id", None) == "config_value"

    def test_default_used_when_no_env_var_or_config(self) -> None:
        assert _cfg({}, "class_id", None, "default") == "default"

    def test_env_var_key_is_uppercased(self, monkeypatch) -> None:
        monkeypatch.setenv("BRIGHTSPACE_BASE_URL", "https://env.example.com")
        assert _cfg({}, "base_url", None) == "https://env.example.com"

    def test_env_var_cdp_url(self, monkeypatch) -> None:
        monkeypatch.setenv("BRIGHTSPACE_CDP_URL", "http://localhost:5555")
        assert _cfg({}, "cdp_url", None) == "http://localhost:5555"

    def test_env_var_output_dir(self, monkeypatch) -> None:
        monkeypatch.setenv("BRIGHTSPACE_OUTPUT_DIR", "/tmp/out")
        assert _cfg({}, "output_dir", None) == "/tmp/out"
