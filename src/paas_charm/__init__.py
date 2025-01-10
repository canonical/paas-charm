#!/usr/bin/env python3

# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Module __init__."""

from paas_charm import exceptions

# Try the charm library imports to check whether they are present
try:
    import charms.traefik_k8s.v2.ingress  # noqa: F401
except ImportError as import_error:
    raise exceptions.MissingCharmLibraryError(
        "Missing charm library, please run `charmcraft fetch-lib charms.traefik_k8s.v2.ingress`"
    ) from import_error
try:
    import charms.observability_libs.v0.juju_topology  # noqa: F401
except ImportError as import_error:
    raise exceptions.MissingCharmLibraryError(
        "Missing charm library, please run "
        "`charmcraft fetch-lib charms.observability_libs.v0.juju_topology`"
    ) from import_error
try:
    import charms.grafana_k8s.v0.grafana_dashboard  # noqa: F401
except ImportError as import_error:
    raise exceptions.MissingCharmLibraryError(
        "Missing charm library, please run "
        "`charmcraft fetch-lib charms.grafana_k8s.v0.grafana_dashboard`"
    ) from import_error
try:
    import charms.loki_k8s.v1.loki_push_api  # noqa: F401
except ImportError as import_error:
    try:
        import charms.loki_k8s.v0.loki_push_api  # noqa: F401
    except ImportError:
        raise exceptions.MissingCharmLibraryError(
            "Missing charm library, please run "
            "`charmcraft fetch-lib charms.loki_k8s.v1.loki_push_api`"
        ) from import_error
try:
    import charms.prometheus_k8s.v0.prometheus_scrape  # noqa: F401
except ImportError as import_error:
    raise exceptions.MissingCharmLibraryError(
        "Missing charm library, please run "
        "`charmcraft fetch-lib charms.prometheus_k8s.v0.prometheus_scrape`"
    ) from import_error
try:
    import charms.data_platform_libs.v0.data_interfaces  # noqa: F401
except ImportError as import_error:
    raise exceptions.MissingCharmLibraryError(
        "Missing charm library, please run "
        "`charmcraft fetch-lib charms.data_platform_libs.v0.data_interfaces`"
    ) from import_error
try:
    import charms.redis_k8s.v0.redis  # noqa: F401
except ImportError as import_error:
    raise exceptions.MissingCharmLibraryError(
        "Missing charm library, please run `charmcraft fetch-lib charms.redis_k8s.v0.redis`"
    ) from import_error
