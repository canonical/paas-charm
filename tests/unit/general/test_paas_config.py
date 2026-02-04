# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for paas_config module."""

import pathlib
import tempfile
from unittest.mock import patch

import pytest
import yaml
from pydantic import ValidationError

from paas_charm.exceptions import CharmConfigInvalidError
from paas_charm.paas_config import CONFIG_FILE_NAME, PaasConfig, read_paas_config


class TestPaasConfig:
    """Tests for PaasConfig Pydantic model."""

    def test_valid_config_minimal(self):
        """Test valid minimal configuration with only version."""
        config = PaasConfig(version="1")
        assert config.version == "1"
        assert config.prometheus is None
        assert config.http_proxy is None

    def test_valid_config_with_prometheus(self):
        """Test valid configuration with prometheus section."""
        config = PaasConfig(
            version="1",
            prometheus={"scrape_configs": [{"job_name": "test"}]},
        )
        assert config.version == "1"
        assert config.prometheus == {"scrape_configs": [{"job_name": "test"}]}

    def test_valid_config_with_http_proxy_snake_case(self):
        """Test valid configuration with http_proxy in snake_case."""
        config = PaasConfig(version="1", http_proxy={"domains": ["example.com"]})
        assert config.version == "1"
        assert config.http_proxy == {"domains": ["example.com"]}

    def test_valid_config_with_http_proxy_kebab_case(self):
        """Test valid configuration with http-proxy in kebab-case (alias)."""
        config_data = {"version": "1", "http-proxy": {"domains": ["example.com"]}}
        config = PaasConfig(**config_data)
        assert config.version == "1"
        assert config.http_proxy == {"domains": ["example.com"]}

    def test_missing_version(self):
        """Test that version field is required."""
        with pytest.raises(ValidationError) as exc_info:
            PaasConfig()
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("version",)
        assert "required" in errors[0]["msg"].lower()

    def test_unsupported_version(self):
        """Test that unsupported version raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            PaasConfig(version="2")
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "unsupported" in errors[0]["msg"].lower()

    def test_extra_fields_forbidden(self):
        """Test that extra fields are not allowed."""
        with pytest.raises(ValidationError) as exc_info:
            PaasConfig(version="1", unknown_field="value")
        errors = exc_info.value.errors()
        assert any("extra" in str(error["type"]).lower() for error in errors)

    def test_invalid_version_type(self):
        """Test that version must be a string."""
        with pytest.raises(ValidationError) as exc_info:
            PaasConfig(version=1)
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("version",)


class TestReadPaasConfig:
    """Tests for read_paas_config function."""

    def test_missing_file_returns_none(self, tmp_path):
        """Test that missing config file returns None."""
        config = read_paas_config(tmp_path)
        assert config is None

    def test_valid_config_file(self, tmp_path):
        """Test reading a valid config file."""
        config_path = tmp_path / CONFIG_FILE_NAME
        config_data = {"version": "1", "prometheus": {"scrape_configs": []}}
        with config_path.open("w", encoding="utf-8") as f:
            yaml.dump(config_data, f)

        config = read_paas_config(tmp_path)
        assert config is not None
        assert config.version == "1"
        assert config.prometheus == {"scrape_configs": []}

    def test_empty_file_returns_none(self, tmp_path):
        """Test that empty config file returns None."""
        config_path = tmp_path / CONFIG_FILE_NAME
        config_path.touch()

        config = read_paas_config(tmp_path)
        assert config is None

    def test_file_with_only_whitespace_returns_none(self, tmp_path):
        """Test that file with only whitespace returns None."""
        config_path = tmp_path / CONFIG_FILE_NAME
        with config_path.open("w", encoding="utf-8") as f:
            f.write("   \n\n   \n")

        config = read_paas_config(tmp_path)
        assert config is None

    def test_invalid_yaml_raises_error(self, tmp_path):
        """Test that invalid YAML raises CharmConfigInvalidError."""
        config_path = tmp_path / CONFIG_FILE_NAME
        with config_path.open("w", encoding="utf-8") as f:
            f.write("version: 1\n  invalid: yaml: content")

        with pytest.raises(CharmConfigInvalidError) as exc_info:
            read_paas_config(tmp_path)
        assert "Invalid YAML" in str(exc_info.value)

    def test_invalid_schema_raises_error(self, tmp_path):
        """Test that schema validation error raises CharmConfigInvalidError."""
        config_path = tmp_path / CONFIG_FILE_NAME
        config_data = {"version": "99", "unknown_key": "value"}
        with config_path.open("w", encoding="utf-8") as f:
            yaml.dump(config_data, f)

        with pytest.raises(CharmConfigInvalidError) as exc_info:
            read_paas_config(tmp_path)
        assert "Invalid" in str(exc_info.value)

    def test_missing_version_field_raises_error(self, tmp_path):
        """Test that missing version field raises CharmConfigInvalidError."""
        config_path = tmp_path / CONFIG_FILE_NAME
        config_data = {"prometheus": {}}
        with config_path.open("w", encoding="utf-8") as f:
            yaml.dump(config_data, f)

        with pytest.raises(CharmConfigInvalidError) as exc_info:
            read_paas_config(tmp_path)
        assert "Invalid" in str(exc_info.value)

    def test_file_read_error_raises_error(self, tmp_path):
        """Test that file read error raises CharmConfigInvalidError."""
        config_path = tmp_path / CONFIG_FILE_NAME
        config_path.touch(mode=0o000)  # No read permissions

        try:
            with pytest.raises(CharmConfigInvalidError) as exc_info:
                read_paas_config(tmp_path)
            assert "Failed to read" in str(exc_info.value)
        finally:
            config_path.chmod(0o644)  # Restore permissions for cleanup

    def test_default_charm_root_uses_cwd(self):
        """Test that None charm_root uses current working directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = pathlib.Path(tmpdir)
            config_path = tmp_path / CONFIG_FILE_NAME
            config_data = {"version": "1"}
            with config_path.open("w", encoding="utf-8") as f:
                yaml.dump(config_data, f)

            with patch("pathlib.Path.cwd", return_value=tmp_path):
                config = read_paas_config()
                assert config is not None
                assert config.version == "1"

    def test_config_with_all_fields(self, tmp_path):
        """Test reading a config file with all supported fields."""
        config_path = tmp_path / CONFIG_FILE_NAME
        config_data = {
            "version": "1",
            "prometheus": {
                "scrape_configs": [
                    {
                        "job_name": "job1",
                        "metrics_path": "/metrics",
                        "static_configs": [{"targets": ["*:8080"]}],
                    }
                ]
            },
            "http-proxy": {"domains": ["api.example.com"]},
        }
        with config_path.open("w", encoding="utf-8") as f:
            yaml.dump(config_data, f)

        config = read_paas_config(tmp_path)
        assert config is not None
        assert config.version == "1"
        assert config.prometheus is not None
        assert config.http_proxy is not None
        assert config.http_proxy == {"domains": ["api.example.com"]}
