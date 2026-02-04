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
from paas_charm.paas_config import (
    CONFIG_FILE_NAME,
    PaasConfig,
    PrometheusConfig,
    ScrapeConfig,
    StaticConfig,
    read_paas_config,
)


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
            prometheus={"scrape_configs": [{"job_name": "test", "static_configs": [{"targets": ["*:8000"]}]}]},
        )
        assert config.version == "1"
        assert config.prometheus is not None
        assert config.prometheus.scrape_configs is not None
        assert len(config.prometheus.scrape_configs) == 1
        assert config.prometheus.scrape_configs[0].job_name == "test"

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
        assert config.prometheus is not None
        assert config.prometheus.scrape_configs == []

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


class TestStaticConfig:
    """Tests for StaticConfig Pydantic model."""

    def test_valid_static_config_minimal(self):
        """Test valid minimal static config with only targets."""
        from paas_charm.paas_config import StaticConfig
        static_config = StaticConfig(targets=["*:8000"])
        assert static_config.targets == ["*:8000"]
        assert static_config.labels is None

    def test_valid_static_config_with_labels(self):
        """Test valid static config with targets and labels."""
        from paas_charm.paas_config import StaticConfig
        static_config = StaticConfig(
            targets=["localhost:9090", "*:8000"],
            labels={"env": "prod", "team": "platform"}
        )
        assert static_config.targets == ["localhost:9090", "*:8000"]
        assert static_config.labels == {"env": "prod", "team": "platform"}

    def test_missing_targets(self):
        """Test that targets field is required."""
        from paas_charm.paas_config import StaticConfig
        with pytest.raises(ValidationError) as exc_info:
            StaticConfig()
        errors = exc_info.value.errors()
        assert any(err["loc"] == ("targets",) for err in errors)

    def test_extra_field_forbidden(self):
        """Test that extra fields are forbidden."""
        from paas_charm.paas_config import StaticConfig
        with pytest.raises(ValidationError) as exc_info:
            StaticConfig(targets=["*:8000"], unknown_field="value")
        errors = exc_info.value.errors()
        assert any("extra" in str(err["type"]) for err in errors)


class TestScrapeConfig:
    """Tests for ScrapeConfig Pydantic model."""

    def test_valid_scrape_config_minimal(self):
        """Test valid minimal scrape config with defaults."""
        from paas_charm.paas_config import ScrapeConfig, StaticConfig
        scrape_config = ScrapeConfig(
            job_name="my-job",
            static_configs=[StaticConfig(targets=["*:8000"])]
        )
        assert scrape_config.job_name == "my-job"
        assert scrape_config.metrics_path == "/metrics"  # default
        assert len(scrape_config.static_configs) == 1
        assert scrape_config.static_configs[0].targets == ["*:8000"]

    def test_valid_scrape_config_custom_path(self):
        """Test valid scrape config with custom metrics path."""
        from paas_charm.paas_config import ScrapeConfig, StaticConfig
        scrape_config = ScrapeConfig(
            job_name="custom-job",
            metrics_path="/custom/metrics",
            static_configs=[StaticConfig(targets=["localhost:9090"])]
        )
        assert scrape_config.job_name == "custom-job"
        assert scrape_config.metrics_path == "/custom/metrics"

    def test_valid_scrape_config_multiple_static_configs(self):
        """Test valid scrape config with multiple static configs."""
        from paas_charm.paas_config import ScrapeConfig, StaticConfig
        scrape_config = ScrapeConfig(
            job_name="multi-target",
            static_configs=[
                StaticConfig(targets=["*:8000"], labels={"type": "app"}),
                StaticConfig(targets=["localhost:9090"], labels={"type": "exporter"}),
            ]
        )
        assert scrape_config.job_name == "multi-target"
        assert len(scrape_config.static_configs) == 2

    def test_missing_job_name(self):
        """Test that job_name field is required."""
        from paas_charm.paas_config import ScrapeConfig, StaticConfig
        with pytest.raises(ValidationError) as exc_info:
            ScrapeConfig(static_configs=[StaticConfig(targets=["*:8000"])])
        errors = exc_info.value.errors()
        assert any(err["loc"] == ("job_name",) for err in errors)

    def test_missing_static_configs(self):
        """Test that static_configs field is required."""
        from paas_charm.paas_config import ScrapeConfig
        with pytest.raises(ValidationError) as exc_info:
            ScrapeConfig(job_name="test")
        errors = exc_info.value.errors()
        assert any(err["loc"] == ("static_configs",) for err in errors)

    def test_extra_field_forbidden(self):
        """Test that extra fields are forbidden."""
        from paas_charm.paas_config import ScrapeConfig, StaticConfig
        with pytest.raises(ValidationError) as exc_info:
            ScrapeConfig(
                job_name="test",
                static_configs=[StaticConfig(targets=["*:8000"])],
                scrape_interval="30s"  # Not supported
            )
        errors = exc_info.value.errors()
        assert any("extra" in str(err["type"]) for err in errors)


class TestPrometheusConfig:
    """Tests for PrometheusConfig Pydantic model."""

    def test_valid_prometheus_config_empty(self):
        """Test valid prometheus config with no scrape configs."""
        from paas_charm.paas_config import PrometheusConfig
        prom_config = PrometheusConfig()
        assert prom_config.scrape_configs is None

    def test_valid_prometheus_config_with_scrape_configs(self):
        """Test valid prometheus config with scrape configs."""
        from paas_charm.paas_config import PrometheusConfig, ScrapeConfig, StaticConfig
        prom_config = PrometheusConfig(
            scrape_configs=[
                ScrapeConfig(
                    job_name="job1",
                    static_configs=[StaticConfig(targets=["*:8000"])]
                )
            ]
        )
        assert prom_config.scrape_configs is not None
        assert len(prom_config.scrape_configs) == 1
        assert prom_config.scrape_configs[0].job_name == "job1"

    def test_valid_prometheus_config_multiple_jobs(self):
        """Test valid prometheus config with multiple jobs."""
        from paas_charm.paas_config import PrometheusConfig, ScrapeConfig, StaticConfig
        prom_config = PrometheusConfig(
            scrape_configs=[
                ScrapeConfig(
                    job_name="job1",
                    metrics_path="/metrics",
                    static_configs=[StaticConfig(targets=["*:8000"])]
                ),
                ScrapeConfig(
                    job_name="job2",
                    metrics_path="/other_metrics",
                    static_configs=[StaticConfig(targets=["localhost:9090"])]
                ),
            ]
        )
        assert len(prom_config.scrape_configs) == 2
        assert prom_config.scrape_configs[0].job_name == "job1"
        assert prom_config.scrape_configs[1].job_name == "job2"

    def test_extra_field_forbidden(self):
        """Test that extra fields are forbidden."""
        from paas_charm.paas_config import PrometheusConfig
        with pytest.raises(ValidationError) as exc_info:
            PrometheusConfig(global_config={"scrape_interval": "15s"})
        errors = exc_info.value.errors()
        assert any("extra" in str(err["type"]) for err in errors)


class TestPaasConfigWithPrometheus:
    """Tests for PaasConfig with Prometheus configuration."""

    def test_paas_config_with_complete_prometheus_section(self):
        """Test PaasConfig with complete prometheus section."""
        from paas_charm.paas_config import PrometheusConfig, ScrapeConfig, StaticConfig
        config = PaasConfig(
            version="1",
            prometheus=PrometheusConfig(
                scrape_configs=[
                    ScrapeConfig(
                        job_name="app-metrics",
                        metrics_path="/metrics",
                        static_configs=[
                            StaticConfig(
                                targets=["*:8000", "*:8001"],
                                labels={"env": "production"}
                            )
                        ]
                    )
                ]
            )
        )
        assert config.prometheus is not None
        assert config.prometheus.scrape_configs is not None
        assert len(config.prometheus.scrape_configs) == 1
        assert config.prometheus.scrape_configs[0].job_name == "app-metrics"
        assert config.prometheus.scrape_configs[0].static_configs[0].labels == {"env": "production"}

    def test_paas_config_prometheus_from_dict(self):
        """Test PaasConfig with prometheus section from dict (YAML-like)."""
        config_dict = {
            "version": "1",
            "prometheus": {
                "scrape_configs": [
                    {
                        "job_name": "job1",
                        "metrics_path": "/metrics",
                        "static_configs": [
                            {
                                "targets": ["*:8008"],
                                "labels": {"key": "value"}
                            }
                        ]
                    },
                    {
                        "job_name": "job2",
                        "static_configs": [
                            {
                                "targets": ["localhost:9090"]
                            }
                        ]
                    }
                ]
            }
        }
        config = PaasConfig(**config_dict)
        assert config.prometheus is not None
        assert len(config.prometheus.scrape_configs) == 2
        assert config.prometheus.scrape_configs[0].job_name == "job1"
        assert config.prometheus.scrape_configs[0].metrics_path == "/metrics"
        assert config.prometheus.scrape_configs[1].job_name == "job2"
        assert config.prometheus.scrape_configs[1].metrics_path == "/metrics"  # default

    def test_paas_config_empty_prometheus_section(self):
        """Test PaasConfig with empty prometheus section."""
        config_dict = {
            "version": "1",
            "prometheus": {}
        }
        config = PaasConfig(**config_dict)
        assert config.prometheus is not None
        assert config.prometheus.scrape_configs is None
