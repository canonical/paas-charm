# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for observability module."""

from paas_charm.observability import _resolve_scheduler_placeholder, build_prometheus_jobs
from paas_charm.paas_config import PrometheusConfig, ScrapeConfig, StaticConfig


class TestResolveSchedulerPlaceholder:
    """Tests for _resolve_scheduler_placeholder function."""

    def test_resolve_scheduler_placeholder(self):
        """Test @scheduler placeholder is resolved to FQDN."""
        result = _resolve_scheduler_placeholder("app", "my-model", "@scheduler:8081")
        assert result == "app-0.app-endpoints.my-model.svc.cluster.local:8081"

    def test_passthrough_wildcard_target(self):
        """Test wildcard target is not modified."""
        result = _resolve_scheduler_placeholder("app", "my-model", "*:8000")
        assert result == "*:8000"

    def test_passthrough_regular_target(self):
        """Test regular target is not modified."""
        result = _resolve_scheduler_placeholder("app", "my-model", "localhost:9090")
        assert result == "localhost:9090"

    def test_different_port_numbers(self):
        """Test @scheduler with different port numbers."""
        result = _resolve_scheduler_placeholder("app", "model", "@scheduler:9999")
        assert result == "app-0.app-endpoints.model.svc.cluster.local:9999"

    def test_different_app_and_model_names(self):
        """Test with various app and model names."""
        result = _resolve_scheduler_placeholder("django-k8s", "production", "@scheduler:8000")
        assert result == "django-k8s-0.django-k8s-endpoints.production.svc.cluster.local:8000"


class TestBuildPrometheusJobs:
    """Tests for build_prometheus_jobs function."""

    def test_no_jobs_configured(self):
        """Test that no implicit scrape job is generated."""
        assert build_prometheus_jobs(None, "app", "model") == []
        assert build_prometheus_jobs(PrometheusConfig(), "app", "model") == []

    def test_explicit_job(self):
        """Test that an explicit scrape job is published."""
        prom_config = PrometheusConfig(
            scrape_configs=[
                ScrapeConfig(
                    job_name="custom-job",
                    metrics_path="/custom/metrics",
                    static_configs=[StaticConfig(targets=["*:9090"])],
                )
            ]
        )

        assert build_prometheus_jobs(prom_config, "app", "model") == [
            {
                "job_name": "custom-job",
                "metrics_path": "/custom/metrics",
                "static_configs": [{"targets": ["*:9090"]}],
            }
        ]

    def test_app_is_an_ordinary_job_name(self):
        """Test that app has no reserved scrape-job behavior."""
        prom_config = PrometheusConfig(
            scrape_configs=[
                ScrapeConfig(
                    job_name="app",
                    metrics_path="/custom-metrics",
                    static_configs=[
                        StaticConfig(targets=["*:9090", "localhost:9090"]),
                        StaticConfig(targets=["*:9091"]),
                    ],
                )
            ]
        )

        assert build_prometheus_jobs(prom_config, "app", "model") == [
            {
                "job_name": "app",
                "metrics_path": "/custom-metrics",
                "static_configs": [
                    {"targets": ["*:9090", "localhost:9090"]},
                    {"targets": ["*:9091"]},
                ],
            }
        ]

    def test_job_with_labels(self):
        """Test explicit labels are preserved."""
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

        jobs = build_prometheus_jobs(prom_config, "app", "model")

        assert jobs[0]["static_configs"][0]["labels"] == {
            "env": "production",
            "team": "platform",
        }

    def test_multiple_jobs(self):
        """Test all explicit scrape jobs are published."""
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

        jobs = build_prometheus_jobs(prom_config, "app", "model")

        assert [job["job_name"] for job in jobs] == ["job1", "job2"]

    def test_scheduler_placeholder_in_explicit_job(self):
        """Test @scheduler resolution in an explicit job."""
        prom_config = PrometheusConfig(
            scrape_configs=[
                ScrapeConfig(
                    job_name="scheduler-metrics",
                    static_configs=[
                        StaticConfig(
                            targets=["*:8000", "@scheduler:8081", "localhost:9090"],
                            labels={"role": "scheduler"},
                        )
                    ],
                )
            ]
        )

        jobs = build_prometheus_jobs(prom_config, "django", "production")

        assert jobs[0]["static_configs"][0] == {
            "targets": [
                "*:8000",
                "django-0.django-endpoints.production.svc.cluster.local:8081",
                "localhost:9090",
            ],
            "labels": {"role": "scheduler"},
        }
