# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for paas_config module."""

import pathlib
import tempfile
from unittest.mock import patch

import pytest
import yaml
from ops import testing
from pydantic import ValidationError

from examples.django.charm.src.charm import DjangoCharm
from examples.expressjs.charm.src.charm import ExpressJSCharm
from examples.fastapi.charm.src.charm import FastAPICharm
from examples.flask.charm.src.charm import FlaskCharm
from examples.go.charm.src.charm import GoCharm
from examples.springboot.charm.src.charm import SpringBootCharm
from paas_charm.exceptions import PaasConfigError
from paas_charm.paas_config import (
    CONFIG_FILE_NAME,
    LoggingFormat,
    PaasConfig,
    PrometheusConfig,
    ScrapeConfig,
    StaticConfig,
    read_paas_config,
)

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent.parent


class TestPaasConfig:
    """Tests for PaasConfig Pydantic model."""

    def test_valid_config_minimal(self):
        """Test valid minimal configuration (empty)."""
        config = PaasConfig()
        assert config.model_fields_set == set()
        assert config.prometheus is None
        assert config.framework_logging_format is LoggingFormat.NONE
        assert config.port == 8080

    def test_valid_config_with_prometheus(self):
        """Test valid configuration with prometheus section."""
        config = PaasConfig(
            prometheus={
                "scrape_configs": [
                    {"job_name": "test", "static_configs": [{"targets": ["*:8000"]}]}
                ]
            },
            port=9090,
        )
        assert config.prometheus is not None
        assert config.prometheus.scrape_configs is not None
        assert len(config.prometheus.scrape_configs) == 1
        assert config.prometheus.scrape_configs[0].job_name == "test"
        assert config.port == 9090

    def test_metrics_endpoint_uses_framework_default_without_app_job(self):
        """Test that an omitted app job preserves framework metrics defaults."""
        config = PaasConfig()

        assert config.metrics_endpoint(default_port=8080, default_path="/metrics") == (
            8080,
            "/metrics",
            False,
        )

    def test_metrics_endpoint_uses_app_job(self):
        """Test that the app job overrides the framework metrics endpoint."""
        config = PaasConfig(
            prometheus={
                "scrape_configs": [
                    {
                        "job_name": "app",
                        "metrics_path": "/custom-metrics",
                        "static_configs": [{"targets": ["*:9090"]}],
                    }
                ]
            }
        )

        assert config.metrics_endpoint(default_port=8080, default_path="/metrics") == (
            9090,
            "/custom-metrics",
            True,
        )

    def test_valid_logging_format_json(self):
        """Test that framework_logging_format='json' is accepted and coerced to LoggingFormat."""
        config = PaasConfig(framework_logging_format="json")
        assert config.framework_logging_format == LoggingFormat.JSON

    def test_invalid_logging_format_rejected(self):
        """Test that an unsupported logging format value is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            PaasConfig(framework_logging_format="xml")
        assert exc_info.value.errors()

    def test_frameworks_supporting_json_logging(self):
        """Test that flask, django, and fastapi are in FRAMEWORKS_SUPPORTING_LOGGING_FORMAT."""
        from paas_charm.paas_config import FRAMEWORKS_SUPPORTING_LOGGING_FORMAT

        supported = FRAMEWORKS_SUPPORTING_LOGGING_FORMAT[LoggingFormat.JSON]
        assert "fastapi" in supported
        assert "flask" in supported
        assert "django" in supported

    def test_extra_fields_forbidden(self):
        """Test that extra fields are not allowed."""
        with pytest.raises(ValidationError) as exc_info:
            PaasConfig(unknown_field="value")
        errors = exc_info.value.errors()
        assert any("extra" in str(error["type"]).lower() for error in errors)

    @pytest.mark.parametrize("value", [None, 0, 65536])
    def test_invalid_port_rejected(self, value):
        """Test that ports must be valid TCP port numbers."""
        with pytest.raises(ValidationError):
            PaasConfig(port=value)


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
        config_path.touch(mode=0o000)

        try:
            with pytest.raises(PaasConfigError) as exc_info:
                read_paas_config(tmp_path)
            assert "Failed to read" in str(exc_info.value)
        finally:
            config_path.chmod(0o644)

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

    def test_partial_config_uses_defaults_for_missing_keys(self, tmp_path):
        """Test that omitted keys retain sane generic defaults."""
        config_path = tmp_path / CONFIG_FILE_NAME
        config_path.write_text("port: 9090\n", encoding="utf-8")

        config = read_paas_config(tmp_path)

        assert config.model_fields_set == {"port"}
        assert config.port == 9090


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

    def test_valid_scheduler_placeholder(self):
        """Test valid @scheduler placeholder with port."""
        static_config = StaticConfig(targets=["@scheduler:8081"])
        assert static_config.targets == ["@scheduler:8081"]

    def test_valid_scheduler_placeholder_mixed(self):
        """Test @scheduler placeholder mixed with other targets."""
        static_config = StaticConfig(targets=["*:8000", "@scheduler:8081", "localhost:9090"])
        assert static_config.targets == ["*:8000", "@scheduler:8081", "localhost:9090"]

    def test_invalid_scheduler_no_port(self):
        """Test @scheduler without port is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            StaticConfig(targets=["@scheduler"])
        errors = exc_info.value.errors()
        assert any("must include port" in str(err["msg"]) for err in errors)

    def test_invalid_scheduler_non_numeric_port(self):
        """Test @scheduler with non-numeric port is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            StaticConfig(targets=["@scheduler:abc"])
        errors = exc_info.value.errors()
        assert any("numeric" in str(err["msg"]) for err in errors)

    def test_invalid_scheduler_empty_port(self):
        """Test @scheduler with empty port is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            StaticConfig(targets=["@scheduler:"])
        errors = exc_info.value.errors()
        assert any("numeric" in str(err["msg"]) for err in errors)


class TestScrapeConfig:
    """Tests for ScrapeConfig Pydantic model."""

    def test_valid_scrape_config_minimal(self):
        """Test valid minimal scrape config with defaults."""
        scrape_config = ScrapeConfig(
            job_name="my-job", static_configs=[StaticConfig(targets=["*:8000"])]
        )
        assert scrape_config.job_name == "my-job"
        assert scrape_config.metrics_path == "/metrics"
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

    def test_app_scrape_config(self):
        """Test retrieving a valid reserved application scrape job."""
        app_job = ScrapeConfig(
            job_name="app",
            metrics_path="/custom-metrics",
            static_configs=[StaticConfig(targets=["*:9090"])],
        )

        prom_config = PrometheusConfig(scrape_configs=[app_job])

        assert prom_config.app_scrape_config == app_job

    @pytest.mark.parametrize(
        "static_configs",
        [
            [],
            [StaticConfig(targets=["*:9090"]), StaticConfig(targets=["*:9091"])],
            [StaticConfig(targets=["*:9090", "*:9091"])],
            [StaticConfig(targets=["@scheduler:9090"])],
            [StaticConfig(targets=["localhost:9090"])],
            [StaticConfig(targets=["*:0"])],
            [StaticConfig(targets=["*:65536"])],
        ],
    )
    def test_invalid_app_scrape_config_rejected(self, static_configs):
        """Test that the reserved app job has one valid wildcard target."""
        with pytest.raises(ValidationError):
            PrometheusConfig(
                scrape_configs=[ScrapeConfig(job_name="app", static_configs=static_configs)]
            )

    def test_app_scrape_config_root_path_rejected(self):
        """Test that the reserved app job identifies a metrics endpoint path."""
        with pytest.raises(ValidationError):
            PrometheusConfig(
                scrape_configs=[
                    ScrapeConfig(
                        job_name="app",
                        metrics_path="/",
                        static_configs=[StaticConfig(targets=["*:9090"])],
                    )
                ]
            )

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


CHARM_STATE_PAAS_CONFIG_TEST_PARAMS = [
    pytest.param(
        FlaskCharm,
        "flask",
        "flask",
        "flask",
        {
            "FLASK_BASE_URL": "http://flask-k8s.test-model:8081",
            "FLASK_METRICS_PATH": "/alternative_metrics",
            "FLASK_METRICS_PORT": "8082",
        },
        id="flask",
    ),
    pytest.param(
        DjangoCharm,
        "django",
        "django",
        "django",
        {
            "DJANGO_BASE_URL": "http://django-k8s.test-model:8081",
            "DJANGO_METRICS_PATH": "/alternative_metrics",
            "DJANGO_METRICS_PORT": "8082",
        },
        id="django",
    ),
    pytest.param(
        FastAPICharm,
        "fastapi",
        "fastapi",
        "fastapi",
        {
            "UVICORN_PORT": "8081",
            "METRICS_PATH": "/alternative_metrics",
            "METRICS_PORT": "8082",
        },
        id="fastapi",
    ),
    pytest.param(
        ExpressJSCharm,
        "expressjs",
        "expressjs",
        "expressjs",
        {"PORT": "8081", "METRICS_PATH": "/alternative_metrics", "METRICS_PORT": "8082"},
        id="expressjs",
    ),
    pytest.param(
        GoCharm,
        "go",
        "go",
        "go",
        {"PORT": "8081", "METRICS_PATH": "/alternative_metrics", "METRICS_PORT": "8082"},
        id="go",
    ),
    pytest.param(
        SpringBootCharm,
        "springboot",
        "spring_boot",
        "spring-boot",
        {
            "SERVER_PORT": "8081",
            "management.server.port": "8082",
            "management.endpoints.web.base-path": "/",
            "management.endpoints.web.path-mapping.prometheus": "alternative_metrics",
        },
        id="springboot",
    ),
]


@pytest.mark.parametrize(
    "charm, example, framework, service, expected_env",
    CHARM_STATE_PAAS_CONFIG_TEST_PARAMS,
)
def test_charm_state_paas_config(
    request, modify_paas_config, charm: type, example: str, framework: str, service: str, expected_env: dict
) -> None:
    """
    arrange: none
    act: set charm configurations.
    assert: charm_config in the charm state should reflect changes in charm configurations.
    """

    modify_paas_config(example, 8081, 8082, "/alternative_metrics")
    base_state = request.getfixturevalue(f"{framework}_base_state")
    ctx = testing.Context(charm)
    state = testing.State(**base_state)

    out = ctx.run(ctx.on.config_changed(), state)

    plan = list(out.containers)[0].plan
    service = plan.services[service]
    for key, value in expected_env.items():
        assert service.environment.get(key) == value
    if framework == "spring_boot":
        assert "APP_METRICS_PORT" not in service.environment


@pytest.mark.parametrize(
    "paas_config, expected_port",
    [
        pytest.param(PaasConfig(), "8080", id="missing-file"),
        pytest.param(PaasConfig(port=9090), "9090", id="partial-file"),
    ],
)
def test_springboot_uses_framework_defaults_for_missing_paas_config_keys(
    request, paas_config: PaasConfig, expected_port: str
) -> None:
    """Test that omitted paas-config keys preserve Spring Boot defaults."""
    base_state = request.getfixturevalue("spring_boot_base_state")
    with patch("paas_charm.charm.read_paas_config", return_value=paas_config):
        ctx = testing.Context(SpringBootCharm)
        out = ctx.run(ctx.on.config_changed(), testing.State(**base_state))

    environment = list(out.containers)[0].plan.services["spring-boot"].environment
    assert environment["SERVER_PORT"] == expected_port
    assert environment["management.endpoints.web.exposure.include"] == "prometheus"
    assert "management.server.port" not in environment
    assert "management.endpoints.web.base-path" not in environment
    assert "management.endpoints.web.path-mapping.prometheus" not in environment



@pytest.fixture(name="modify_paas_config")
def modify_paas_config_fixture():
    """Temporarily modify paas-config.yaml for a given framework and revert after the test."""
    originals: dict[pathlib.Path, str] = {}

    def _modify(framework: str, port: int, metrics_port: int, metrics_path: str) -> None:
        paas_config_path = PROJECT_ROOT / f"examples/{framework}/charm/paas-config.yaml"
        if paas_config_path not in originals:
            originals[paas_config_path] = paas_config_path.read_text()
        config = yaml.safe_load(originals[paas_config_path])
        config["port"] = port
        prometheus = config.setdefault("prometheus", {})
        scrape_configs = prometheus.setdefault("scrape_configs", [])
        scrape_configs[:] = [job for job in scrape_configs if job.get("job_name") != "app"]
        scrape_configs.append(
            {
                "job_name": "app",
                "metrics_path": metrics_path,
                "static_configs": [{"targets": [f"*:{metrics_port}"]}],
            }
        )
        paas_config_path.write_text(yaml.dump(config))

    try:
        yield _modify
    finally:
        for path, content in originals.items():
            path.write_text(content)
