# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for observability module."""

from paas_charm.observability import build_prometheus_jobs
from paas_charm.paas_config import PrometheusConfig, ScrapeConfig, StaticConfig


class TestBuildPrometheusJobs:
    """Tests for build_prometheus_jobs function."""

    def test_no_jobs_configured(self):
        """Test when no metrics are configured."""
        jobs = build_prometheus_jobs(None, None, None)
        assert jobs is None

    def test_only_framework_default_job(self):
        """Test with only framework default metrics."""
        jobs = build_prometheus_jobs("*:8000", "/metrics", None)
        assert jobs is not None
        assert len(jobs) == 1
        assert jobs[0] == {
            "metrics_path": "/metrics",
            "static_configs": [{"targets": ["*:8000"]}],
        }

    def test_only_custom_jobs(self):
        """Test with only custom Prometheus config, no framework defaults."""
        prom_config = PrometheusConfig(
            scrape_configs=[
                ScrapeConfig(
                    job_name="custom-job",
                    metrics_path="/custom/metrics",
                    static_configs=[StaticConfig(targets=["*:9090"])],
                )
            ]
        )
        jobs = build_prometheus_jobs(None, None, prom_config)
        assert jobs is not None
        assert len(jobs) == 1
        assert jobs[0]["job_name"] == "custom-job"
        assert jobs[0]["metrics_path"] == "/custom/metrics"
        assert jobs[0]["static_configs"] == [{"targets": ["*:9090"]}]

    def test_framework_default_plus_custom_jobs(self):
        """Test merging framework default with custom jobs."""
        prom_config = PrometheusConfig(
            scrape_configs=[
                ScrapeConfig(
                    job_name="app-metrics",
                    metrics_path="/app/metrics",
                    static_configs=[StaticConfig(targets=["*:8001", "localhost:9090"])],
                )
            ]
        )
        jobs = build_prometheus_jobs("*:8000", "/metrics", prom_config)
        assert jobs is not None
        assert len(jobs) == 2
        # First job is framework default
        assert jobs[0] == {
            "metrics_path": "/metrics",
            "static_configs": [{"targets": ["*:8000"]}],
        }
        # Second job is custom
        assert jobs[1]["job_name"] == "app-metrics"
        assert jobs[1]["metrics_path"] == "/app/metrics"
        assert jobs[1]["static_configs"] == [
            {"targets": ["*:8001", "localhost:9090"]},
        ]

    def test_custom_job_with_labels(self):
        """Test custom job with labels."""
        prom_config = PrometheusConfig(
            scrape_configs=[
                ScrapeConfig(
                    job_name="labeled-job",
                    static_configs=[
                        StaticConfig(
                            targets=["*:8080"],
                            labels={"env": "production", "team": "platform"},
                        )
                    ],
                )
            ]
        )
        jobs = build_prometheus_jobs(None, None, prom_config)
        assert jobs is not None
        assert len(jobs) == 1
        assert jobs[0]["static_configs"][0]["labels"] == {
            "env": "production",
            "team": "platform",
        }

    def test_multiple_custom_jobs(self):
        """Test multiple custom scrape configs."""
        prom_config = PrometheusConfig(
            scrape_configs=[
                ScrapeConfig(
                    job_name="job1",
                    metrics_path="/metrics1",
                    static_configs=[StaticConfig(targets=["*:8001"])],
                ),
                ScrapeConfig(
                    job_name="job2",
                    metrics_path="/metrics2",
                    static_configs=[StaticConfig(targets=["*:8002"])],
                ),
            ]
        )
        jobs = build_prometheus_jobs("*:8000", "/metrics", prom_config)
        assert jobs is not None
        assert len(jobs) == 3  # 1 default + 2 custom
        assert jobs[1]["job_name"] == "job1"
        assert jobs[2]["job_name"] == "job2"

    def test_custom_job_with_multiple_static_configs(self):
        """Test custom job with multiple static_configs."""
        prom_config = PrometheusConfig(
            scrape_configs=[
                ScrapeConfig(
                    job_name="multi-target",
                    static_configs=[
                        StaticConfig(targets=["*:8001"], labels={"type": "app"}),
                        StaticConfig(targets=["localhost:9090"], labels={"type": "exporter"}),
                    ],
                )
            ]
        )
        jobs = build_prometheus_jobs(None, None, prom_config)
        assert jobs is not None
        assert len(jobs) == 1
        assert len(jobs[0]["static_configs"]) == 2
        assert jobs[0]["static_configs"][0] == {
            "targets": ["*:8001"],
            "labels": {"type": "app"},
        }
        assert jobs[0]["static_configs"][1] == {
            "targets": ["localhost:9090"],
            "labels": {"type": "exporter"},
        }

    def test_empty_prometheus_config(self):
        """Test with empty PrometheusConfig (no scrape_configs)."""
        prom_config = PrometheusConfig()
        jobs = build_prometheus_jobs("*:8000", "/metrics", prom_config)
        assert jobs is not None
        assert len(jobs) == 1  # Only framework default
        assert jobs[0]["metrics_path"] == "/metrics"

    def test_partial_framework_config(self):
        """Test when framework has only path or only target."""
        # Only target, no path
        jobs = build_prometheus_jobs("*:8000", None, None)
        assert jobs is None

        # Only path, no target
        jobs = build_prometheus_jobs(None, "/metrics", None)
        assert jobs is None
