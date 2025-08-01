# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""ExpressJS Charm service."""

import pathlib
import typing
from typing import TYPE_CHECKING

import ops
from pydantic import ConfigDict, Field

from paas_charm.app import App, WorkloadConfig
from paas_charm.charm import PaasCharm
from paas_charm.framework import FrameworkConfig

if TYPE_CHECKING:
    from paas_charm.oauth import PaaSOAuthRelationData


# The abstract function has the `framework` so
# pylint: disable=unused-argument
def generate_oauth_env(
    framework: str,
    relation_data: "PaaSOAuthRelationData | None" = None,
) -> dict[str, str]:
    """Generate environment variable from PaaSOAuthRelationData.

    Args:
        framework: The charm framework name.
        relation_data: The charm Oauth integration relation data.

    Returns:
        Default Oauth environment mappings if PaaSOAuthRelationData is available, empty
        dictionary otherwise.
    """
    if not relation_data:
        return {}
    return {
        k: v
        for k, v in (
            ("CLIENT_ID", relation_data.client_id),
            ("CLIENT_SECRET", relation_data.client_secret),
            ("ISSUER_BASE_URL", relation_data.issuer_url),
            ("APP_OIDC_AUTHORIZE_URL", relation_data.authorization_endpoint),
            ("APP_OIDC_ACCESS_TOKEN_URL", relation_data.token_endpoint),
            ("APP_OIDC_USER_URL", relation_data.userinfo_endpoint),
            ("SCOPE", relation_data.scopes),
            ("APP_OIDC_JWKS_URL", relation_data.jwks_endpoint),
        )
        if v is not None
    }


class ExpressJSConfig(FrameworkConfig):
    """Represent ExpressJS builtin configuration values.

    Attrs:
        node_env: environment where the application is running.
            It can be "production" or "development".
        port: port where the application is listening
        metrics_port: port where the metrics are collected
        metrics_path: path where the metrics are collected
        app_secret_key: a secret key that will be used for securely signing the session cookie
            and can be used for any other security related needs by your ExpressJS application.
        model_config: Pydantic model configuration.
    """

    node_env: str = Field(alias="node-env", default="production", min_length=1)
    port: int = Field(alias="port", default=8080, gt=0)
    metrics_port: int | None = Field(alias="metrics-port", default=None, gt=0)
    metrics_path: str | None = Field(alias="metrics-path", default=None, min_length=1)
    app_secret_key: str | None = Field(alias="app-secret-key", default=None, min_length=1)

    model_config = ConfigDict(extra="ignore")


class ExpressJSApp(App):
    """ExpressJS App service.

    Attrs:
        generate_oauth_env: Maps OAuth connection information to environment variables.
    """

    generate_oauth_env = staticmethod(generate_oauth_env)


class Charm(PaasCharm):
    """ExpressJS Charm service.

    Attrs:
        framework_config_class: Base class for framework configuration.
    """

    framework_config_class = ExpressJSConfig

    def __init__(self, framework: ops.Framework) -> None:
        """Initialize the ExpressJS charm.

        Args:
            framework: operator framework.
        """
        super().__init__(framework=framework, framework_name="expressjs")

    @property
    def _workload_config(self) -> WorkloadConfig:
        """Return an WorkloadConfig instance."""
        base_dir = pathlib.Path("/app")
        framework_config = typing.cast(ExpressJSConfig, self.get_framework_config())
        return WorkloadConfig(
            framework=self._framework_name,
            port=framework_config.port,
            base_dir=base_dir,
            app_dir=base_dir,
            state_dir=base_dir / "state",
            log_files=[],
            service_name=self._framework_name,
            metrics_target=f"*:{framework_config.metrics_port}",
            metrics_path=framework_config.metrics_path,
            unit_name=self.unit.name,
        )

    def _create_app(self) -> App:
        """Build a App instance.

        Returns:
            A new App instance.
        """
        charm_state = self._create_charm_state()
        return ExpressJSApp(
            container=self._container,
            charm_state=charm_state,
            workload_config=self._workload_config,
            database_migration=self._database_migration,
            framework_config_prefix="",
        )
