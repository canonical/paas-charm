# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Provide a wrapper around http-proxy integration lib."""

from charms.squid_forward_proxy.v0.http_proxy import (
    HttpProxyRequirer,
    HTTPProxyUnavailableError,
    ProxyConfig,
)

from paas_charm.exceptions import RelationDataError


class HttpProxyRelationDataError(RelationDataError):
    """Raised when http-proxy relation data is either unavailable, invalid or not ready.

    Attributes:
        relation: The http-proxy relation name.
    """

    relation = "http-proxy"


class PaaSHttpProxyRequirer(HttpProxyRequirer):
    """Wrapper around HttpProxyRequirer."""

    def fetch_proxies(self) -> ProxyConfig:
        """Get HTTP proxy values returned by the provider.

        Returns:
            HTTP proxy values.

        Raises:
            HttpProxyRelationDataError: If http-proxy relation data is either unavailable,
            invalid or not usable.
        """
        try:
            return super().fetch_proxies()
        except HTTPProxyUnavailableError as exc:
            raise HttpProxyRelationDataError(
                f"HTTP proxy relation data is unavailable: {exc}"
            ) from exc
