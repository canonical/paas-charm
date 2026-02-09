# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for observability module."""

from paas_charm.observability import _resolve_scheduler_placeholder, build_prometheus_jobs
from paas_charm.paas_config import PrometheusConfig, ScrapeConfig, StaticConfig


class TestResolveSchedulerPlaceholder:
    """Tests for _resolve_scheduler_placeholder function."""

    def test_resolve_scheduler_placeholder(self):
        """Test @scheduler placeholder is resolved to FQDN."""
        result = _resolve_scheduler_placeholder("flask-app", "my-model", "@scheduler:8081")
        assert result == "flask-app-0.flask-app-endpoints.my-model.svc.cluster.local:8081"

    def test_passthrough_wildcard_target(self):
        """Test wildcard target is not modified."""
        result = _resolve_scheduler_placeholder("flask-app", "my-model", "*:8000")
        assert result == "*:8000"

    def test_passthrough_regular_target(self):
        """Test regular target is not modified."""
        result = _resolve_scheduler_placeholder("flask-app", "my-model", "localhost:9090")
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
        """Test when no metrics are configured."""
        jobs = build_prometheus_jobs(None, None, None, "app", "model")
        assert jobs == []

    def test_only_framework_default_job(self):
        """Test with only framework default metrics."""
        jobs = build_prometheus_jobs("*:8000", "/metrics", None, "app", "model")
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
        jobs = build_prometheus_jobs(None, None, prom_config, "app", "model")
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
        jobs = build_prometheus_jobs("*:8000", "/metrics", prom_config, "app", "model")
        assert len(jobs) == 2
        assert jobs[0] == {
            "metrics_path": "/metrics",
            "static_configs": [{"targets": ["*:8000"]}],
        }
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
        jobs = build_prometheus_jobs(None, None, prom_config, "app", "model")
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
        jobs = build_prometheus_jobs("*:8000", "/metrics", prom_config, "app", "model")
        assert len(jobs) == 3
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
        jobs = build_prometheus_jobs(None, None, prom_config, "app", "model")
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
        jobs = build_prometheus_jobs("*:8000", "/metrics", prom_config, "app", "model")
        assert len(jobs) == 1
        assert jobs[0]["metrics_path"] == "/metrics"

    def test_partial_framework_config(self):
        """Test when framework has only path or only target."""
        jobs = build_prometheus_jobs("*:8000", None, None, "app", "model")
        assert jobs == []

        jobs = build_prometheus_jobs(None, "/metrics", None, "app", "model")
        assert jobs == []

    def test_scheduler_placeholder_in_framework_default(self):
        """Test @scheduler placeholder in framework default job."""
        jobs = build_prometheus_jobs("@scheduler:8081", "/metrics", None, "flask-app", "my-model")
        assert len(jobs) == 1
        expected_target = "flask-app-0.flask-app-endpoints.my-model.svc.cluster.local:8081"
        assert jobs[0]["static_configs"][0]["targets"] == [expected_target]

    def test_scheduler_placeholder_in_custom_job(self):
        """Test @scheduler placeholder in custom job."""
        prom_config = PrometheusConfig(
            scrape_configs=[
                ScrapeConfig(
                    job_name="scheduler-metrics",
                    static_configs=[StaticConfig(targets=["@scheduler:8081"])],
                )
            ]
        )
        jobs = build_prometheus_jobs(None, None, prom_config, "django", "production")
        assert len(jobs) == 1
        expected_target = "django-0.django-endpoints.production.svc.cluster.local:8081"
        assert jobs[0]["static_configs"][0]["targets"] == [expected_target]

    def test_scheduler_placeholder_mixed_with_other_targets(self):
        """Test @scheduler mixed with wildcard and regular targets."""
        prom_config = PrometheusConfig(
            scrape_configs=[
                ScrapeConfig(
                    job_name="mixed",
                    static_configs=[
                        StaticConfig(targets=["*:8000", "@scheduler:8081", "localhost:9090"])
                    ],
                )
            ]
        )
        jobs = build_prometheus_jobs(None, None, prom_config, "app", "model")
        assert len(jobs) == 1
        assert jobs[0]["static_configs"][0]["targets"] == [
            "*:8000",
            "app-0.app-endpoints.model.svc.cluster.local:8081",
            "localhost:9090",
        ]

    def test_scheduler_placeholder_with_labels(self):
        """Test @scheduler placeholder with labels."""
        prom_config = PrometheusConfig(
            scrape_configs=[
                ScrapeConfig(
                    job_name="scheduler-with-labels",
                    static_configs=[
                        StaticConfig(targets=["@scheduler:8081"], labels={"role": "scheduler"})
                    ],
                )
            ]
        )
        jobs = build_prometheus_jobs(None, None, prom_config, "app", "model")
        assert len(jobs) == 1
        assert jobs[0]["static_configs"][0]["labels"] == {"role": "scheduler"}
        expected_target = "app-0.app-endpoints.model.svc.cluster.local:8081"
        assert jobs[0]["static_configs"][0]["targets"] == [expected_target]
