# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""ExpressJS Charm service."""
import logging
import pathlib
import typing

import ops
from charms.certificate_transfer_interface.v0.certificate_transfer import (
    CertificateAvailableEvent,
    CertificateRemovedEvent,
    CertificateTransferRequires,
)
from charms.hydra.v0.oauth import OauthProviderConfig
from pydantic import ConfigDict, Field

from paas_charm.app import App, WorkloadConfig
from paas_charm.charm import PaasCharm
from paas_charm.framework import FrameworkConfig

logger = logging.getLogger(__name__)

def generate_oauth_env(
    framework: str, relation_data: "OauthProviderConfig | None" = None
) -> dict[str, str]:
    """Generate environment variable from OauthProviderConfig.

    Args:
        relation_data: The charm Oauth integration relation data.

    Returns:
        Default Oauth environment mappings if OauthProviderConfig is available, empty
        dictionary otherwise.
    """
    if not relation_data:
        return {}
    return {
        k: v
        for k, v in (
            (f"CLIENT_ID", relation_data.client_id),
            (f"CLIENT_SECRET", relation_data.client_secret),
            (f"ISSUER_BASE_URL", relation_data.issuer_url),
            (f"APP_OIDC_AUTHORIZE_URL", relation_data.authorization_endpoint),
            (f"APP_OIDC_ACCESS_TOKEN_URL", relation_data.token_endpoint),
            (f"APP_OIDC_USER_URL", relation_data.userinfo_endpoint),
            (
                f"APP_OIDC_CLIENT_KWARGS",
                '{"scope": "openid profile email"}',
            ),  # FLASK_OIDC_CLIENT_KWARGS_SCOPE
            (f"APP_OIDC_JWKS_URL", relation_data.jwks_endpoint),
            ("REQUESTS_CA_BUNDLE", "/app/ca.crt"),
            ("SSL_CERT_FILE", "/app/ca.crt"),
            ("NODE_EXTRA_CA_CERTS", "/app/ca.crt"),
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
        oauth_env: environment variables for Oauth integration.
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
        self.trusted_cert_transfer = CertificateTransferRequires(self, "receive-ca-cert")
        self.framework.observe(
            self.trusted_cert_transfer.on.certificate_available, self._on_certificate_available
        )
        self.framework.observe(
            self.trusted_cert_transfer.on.certificate_removed, self._on_certificate_removed
        )
        rel_name = self.trusted_cert_transfer.relationship_name
        _cert_relation = self.model.get_relation(relation_name=rel_name)
        try:
            if self.trusted_cert_transfer.is_ready(_cert_relation):
                for relation in self.model.relations.get(rel_name, []):
                    # For some reason, relation.units includes our unit and app. Need to exclude them.
                    for unit in set(relation.units).difference([self.app, self.unit]):
                        # Note: this nested loop handles the case of multi-unit CA, each unit providing
                        # a different ca cert, but that is not currently supported by the lib itself.
                        if cert := relation.data[unit].get("ca"):
                            self._container.push("/app/ca.crt", cert)
        except:
            logger.warning("TLS RELATION EMPTY?")

    def _on_certificate_available(self, event: CertificateAvailableEvent):
        logger.warning(f"{event.certificate=}")
        logger.warning(f"{event.ca=}")
        self._container.push("/app/ca.crt", event.ca)

    def _on_certificate_removed(self, event: CertificateRemovedEvent):
        logger.warning(event.relation_id)

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
