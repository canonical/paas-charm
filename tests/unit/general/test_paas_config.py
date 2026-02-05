# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for paas_config module."""

import pathlib
import tempfile
from unittest.mock import patch

import pytest
import yaml
from pydantic import ValidationError

from paas_charm.exceptions import PaasConfigError
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
        """Test valid minimal configuration (empty)."""
        config = PaasConfig()
        assert config.prometheus is None

    def test_valid_config_with_prometheus(self):
        """Test valid configuration with prometheus section."""
        config = PaasConfig(
            prometheus={
                "scrape_configs": [
                    {"job_name": "test", "static_configs": [{"targets": ["*:8000"]}]}
                ]
            },
        )
        assert config.prometheus is not None
        assert config.prometheus.scrape_configs is not None
        assert len(config.prometheus.scrape_configs) == 1
        assert config.prometheus.scrape_configs[0].job_name == "test"

    def test_extra_fields_forbidden(self):
        """Test that extra fields are not allowed."""
        with pytest.raises(ValidationError) as exc_info:
            PaasConfig(unknown_field="value")
        errors = exc_info.value.errors()
        assert any("extra" in str(error["type"]).lower() for error in errors)


class TestReadPaasConfig:
    """Tests for read_paas_config function."""

    def test_missing_file_returns_empty_config(self, tmp_path):
        """Test that missing config file returns empty PaasConfig."""
        config = read_paas_config(tmp_path)
        assert config == PaasConfig()
        assert config.prometheus is None

    def test_valid_config_file(self, tmp_path):
        """Test reading a valid config file."""
        config_path = tmp_path / CONFIG_FILE_NAME
        config_data = {"prometheus": {"scrape_configs": []}}
        with config_path.open("w", encoding="utf-8") as f:
            yaml.dump(config_data, f)

        config = read_paas_config(tmp_path)
        assert config.prometheus is not None
        assert config.prometheus.scrape_configs == []

    def test_empty_file_returns_empty_config(self, tmp_path):
        """Test that empty config file returns empty PaasConfig."""
        config_path = tmp_path / CONFIG_FILE_NAME
        config_path.touch()

        config = read_paas_config(tmp_path)
        assert config == PaasConfig()
        assert config.prometheus is None

    def test_file_with_only_whitespace_returns_empty_config(self, tmp_path):
        """Test that file with only whitespace returns empty PaasConfig."""
        config_path = tmp_path / CONFIG_FILE_NAME
        with config_path.open("w", encoding="utf-8") as f:
            f.write("   \n\n   \n")

        config = read_paas_config(tmp_path)
        assert config == PaasConfig()
        assert config.prometheus is None

    def test_invalid_yaml_raises_error(self, tmp_path):
        """Test that invalid YAML raises PaasConfigError."""
        config_path = tmp_path / CONFIG_FILE_NAME
        with config_path.open("w", encoding="utf-8") as f:
            f.write("version: 1\n  invalid: yaml: content")

        with pytest.raises(PaasConfigError) as exc_info:
            read_paas_config(tmp_path)
        assert "Invalid YAML" in str(exc_info.value)

    def test_invalid_schema_raises_error(self, tmp_path):
        """Test that schema validation error raises PaasConfigError."""
        config_path = tmp_path / CONFIG_FILE_NAME
        config_data = {"unknown_key": "value"}
        with config_path.open("w", encoding="utf-8") as f:
            yaml.dump(config_data, f)

        with pytest.raises(PaasConfigError) as exc_info:
            read_paas_config(tmp_path)
        assert "Invalid" in str(exc_info.value)

    def test_file_read_error_raises_error(self, tmp_path):
        """Test that file read error raises PaasConfigError."""
        config_path = tmp_path / CONFIG_FILE_NAME
        config_path.touch(mode=0o000)  # No read permissions

        try:
            with pytest.raises(PaasConfigError) as exc_info:
                read_paas_config(tmp_path)
            assert "Failed to read" in str(exc_info.value)
        finally:
            config_path.chmod(0o644)  # Restore permissions for cleanup

    def test_default_charm_root_uses_cwd(self):
        """Test that None charm_root uses current working directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = pathlib.Path(tmpdir)
            config_path = tmp_path / CONFIG_FILE_NAME
            config_data = {"prometheus": {"scrape_configs": []}}
            with config_path.open("w", encoding="utf-8") as f:
                yaml.dump(config_data, f)

            with patch("pathlib.Path.cwd", return_value=tmp_path):
                config = read_paas_config()
                assert config.prometheus is not None

    def test_config_with_all_fields(self, tmp_path):
        """Test reading a config file with all supported fields."""
        config_path = tmp_path / CONFIG_FILE_NAME
        config_data = {
            "prometheus": {
                "scrape_configs": [
                    {
                        "job_name": "job1",
                        "metrics_path": "/metrics",
                        "static_configs": [{"targets": ["*:8080"]}],
                    }
                ]
            },
        }
        with config_path.open("w", encoding="utf-8") as f:
            yaml.dump(config_data, f)

        config = read_paas_config(tmp_path)
        assert config.prometheus is not None


class TestStaticConfig:
    """Tests for StaticConfig Pydantic model."""

    def test_valid_static_config_minimal(self):
        """Test valid minimal static config with only targets."""

        static_config = StaticConfig(targets=["*:8000"])
        assert static_config.targets == ["*:8000"]
        assert static_config.labels is None

    def test_valid_static_config_with_labels(self):
        """Test valid static config with targets and labels."""

        static_config = StaticConfig(
            targets=["localhost:9090", "*:8000"], labels={"env": "prod", "team": "platform"}
        )
        assert static_config.targets == ["localhost:9090", "*:8000"]
        assert static_config.labels == {"env": "prod", "team": "platform"}

    def test_missing_targets(self):
        """Test that targets field is required."""

        with pytest.raises(ValidationError) as exc_info:
            StaticConfig()
        errors = exc_info.value.errors()
        assert any(err["loc"] == ("targets",) for err in errors)

    def test_extra_field_forbidden(self):
        """Test that extra fields are forbidden."""

        with pytest.raises(ValidationError) as exc_info:
            StaticConfig(targets=["*:8000"], unknown_field="value")
        errors = exc_info.value.errors()
        assert any("extra" in str(err["type"]) for err in errors)


class TestScrapeConfig:
    """Tests for ScrapeConfig Pydantic model."""

    def test_valid_scrape_config_minimal(self):
        """Test valid minimal scrape config with defaults."""

        scrape_config = ScrapeConfig(
            job_name="my-job", static_configs=[StaticConfig(targets=["*:8000"])]
        )
        assert scrape_config.job_name == "my-job"
        assert scrape_config.metrics_path == "/metrics"  # default
        assert len(scrape_config.static_configs) == 1
        assert scrape_config.static_configs[0].targets == ["*:8000"]

    def test_valid_scrape_config_custom_path(self):
        """Test valid scrape config with custom metrics path."""

        scrape_config = ScrapeConfig(
            job_name="custom-job",
            metrics_path="/custom/metrics",
            static_configs=[StaticConfig(targets=["localhost:9090"])],
        )
        assert scrape_config.job_name == "custom-job"
        assert scrape_config.metrics_path == "/custom/metrics"

    def test_valid_scrape_config_multiple_static_configs(self):
        """Test valid scrape config with multiple static configs."""

        scrape_config = ScrapeConfig(
            job_name="multi-target",
            static_configs=[
                StaticConfig(targets=["*:8000"], labels={"type": "app"}),
                StaticConfig(targets=["localhost:9090"], labels={"type": "exporter"}),
            ],
        )
        assert scrape_config.job_name == "multi-target"
        assert len(scrape_config.static_configs) == 2

    def test_missing_job_name(self):
        """Test that job_name field is required."""

        with pytest.raises(ValidationError) as exc_info:
            ScrapeConfig(static_configs=[StaticConfig(targets=["*:8000"])])
        errors = exc_info.value.errors()
        assert any(err["loc"] == ("job_name",) for err in errors)

    def test_missing_static_configs(self):
        """Test that static_configs field is required."""

        with pytest.raises(ValidationError) as exc_info:
            ScrapeConfig(job_name="test")
        errors = exc_info.value.errors()
        assert any(err["loc"] == ("static_configs",) for err in errors)

    def test_extra_field_forbidden(self):
        """Test that extra fields are forbidden."""

        with pytest.raises(ValidationError) as exc_info:
            ScrapeConfig(
                job_name="test",
                static_configs=[StaticConfig(targets=["*:8000"])],
                scrape_interval="30s",  # Not supported
            )
        errors = exc_info.value.errors()
        assert any("extra" in str(err["type"]) for err in errors)


class TestPrometheusConfig:
    """Tests for PrometheusConfig Pydantic model."""

    def test_valid_prometheus_config_empty(self):
        """Test valid prometheus config with no scrape configs."""

        prom_config = PrometheusConfig()
        assert prom_config.scrape_configs is None

    def test_valid_prometheus_config_with_scrape_configs(self):
        """Test valid prometheus config with scrape configs."""

        prom_config = PrometheusConfig(
            scrape_configs=[
                ScrapeConfig(job_name="job1", static_configs=[StaticConfig(targets=["*:8000"])])
            ]
        )
        assert prom_config.scrape_configs is not None
        assert len(prom_config.scrape_configs) == 1
        assert prom_config.scrape_configs[0].job_name == "job1"

    def test_valid_prometheus_config_multiple_jobs(self):
        """Test valid prometheus config with multiple jobs."""

        prom_config = PrometheusConfig(
            scrape_configs=[
                ScrapeConfig(
                    job_name="job1",
                    metrics_path="/metrics",
                    static_configs=[StaticConfig(targets=["*:8000"])],
                ),
                ScrapeConfig(
                    job_name="job2",
                    metrics_path="/other_metrics",
                    static_configs=[StaticConfig(targets=["localhost:9090"])],
                ),
            ]
        )
        assert len(prom_config.scrape_configs) == 2
        assert prom_config.scrape_configs[0].job_name == "job1"
        assert prom_config.scrape_configs[1].job_name == "job2"

    def test_extra_field_forbidden(self):
        """Test that extra fields are forbidden."""

        with pytest.raises(ValidationError) as exc_info:
            PrometheusConfig(global_config={"scrape_interval": "15s"})
        errors = exc_info.value.errors()
        assert any("extra" in str(err["type"]) for err in errors)

    def test_duplicate_job_names_rejected(self):
        """Test that duplicate job_names are rejected."""

        with pytest.raises(ValidationError) as exc_info:
            PrometheusConfig(
                scrape_configs=[
                    ScrapeConfig(
                        job_name="app-metrics", static_configs=[StaticConfig(targets=["*:8000"])]
                    ),
                    ScrapeConfig(
                        job_name="app-metrics", static_configs=[StaticConfig(targets=["*:9000"])]
                    ),
                ]
            )
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "app-metrics" in str(errors[0]["ctx"]["error"])
        assert "Duplicate job_name" in str(errors[0]["ctx"]["error"])

    def test_multiple_duplicate_job_names(self):
        """Test that multiple duplicates are all reported."""

        with pytest.raises(ValidationError) as exc_info:
            PrometheusConfig(
                scrape_configs=[
                    ScrapeConfig(
                        job_name="job1", static_configs=[StaticConfig(targets=["*:8000"])]
                    ),
                    ScrapeConfig(
                        job_name="job2", static_configs=[StaticConfig(targets=["*:8001"])]
                    ),
                    ScrapeConfig(
                        job_name="job1", static_configs=[StaticConfig(targets=["*:8002"])]
                    ),
                    ScrapeConfig(
                        job_name="job2", static_configs=[StaticConfig(targets=["*:8003"])]
                    ),
                ]
            )
        errors = exc_info.value.errors()
        assert len(errors) == 1
        error_msg = str(errors[0]["ctx"]["error"])
        assert "job1" in error_msg
        assert "job2" in error_msg

    def test_unique_job_names_accepted(self):
        """Test that unique job_names are accepted."""

        prom_config = PrometheusConfig(
            scrape_configs=[
                ScrapeConfig(job_name="job1", static_configs=[StaticConfig(targets=["*:8000"])]),
                ScrapeConfig(job_name="job2", static_configs=[StaticConfig(targets=["*:8001"])]),
                ScrapeConfig(job_name="job3", static_configs=[StaticConfig(targets=["*:8002"])]),
            ]
        )
        assert len(prom_config.scrape_configs) == 3

    def test_single_job_no_duplicate(self):
        """Test that a single job cannot be a duplicate."""

        prom_config = PrometheusConfig(
            scrape_configs=[
                ScrapeConfig(
                    job_name="only-job", static_configs=[StaticConfig(targets=["*:8000"])]
                )
            ]
        )
        assert len(prom_config.scrape_configs) == 1

    def test_empty_scrape_configs_no_validation(self):
        """Test that empty scrape_configs doesn't trigger validation."""

        prom_config = PrometheusConfig(scrape_configs=[])
        assert prom_config.scrape_configs == []


class TestPaasConfigWithPrometheus:
    """Tests for PaasConfig with Prometheus configuration."""

    def test_paas_config_with_complete_prometheus_section(self):
        """Test PaasConfig with complete prometheus section."""

        config = PaasConfig(
            prometheus=PrometheusConfig(
                scrape_configs=[
                    ScrapeConfig(
                        job_name="app-metrics",
                        metrics_path="/metrics",
                        static_configs=[
                            StaticConfig(
                                targets=["*:8000", "*:8001"], labels={"env": "production"}
                            )
                        ],
                    )
                ]
            ),
        )
        assert config.prometheus is not None
        assert config.prometheus.scrape_configs is not None
        assert len(config.prometheus.scrape_configs) == 1
        assert config.prometheus.scrape_configs[0].job_name == "app-metrics"
        assert config.prometheus.scrape_configs[0].static_configs[0].labels == {
            "env": "production"
        }

    def test_paas_config_prometheus_from_dict(self):
        """Test PaasConfig with prometheus section from dict (YAML-like)."""
        config_dict = {
            "prometheus": {
                "scrape_configs": [
                    {
                        "job_name": "job1",
                        "metrics_path": "/metrics",
                        "static_configs": [{"targets": ["*:8008"], "labels": {"key": "value"}}],
                    },
                    {"job_name": "job2", "static_configs": [{"targets": ["localhost:9090"]}]},
                ]
            },
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
        config_dict = {"prometheus": {}}
        config = PaasConfig(**config_dict)
        assert config.prometheus is not None
        assert config.prometheus.scrape_configs is None
