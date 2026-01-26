#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for Flask charm proxy setting."""

import jubilant
import pytest
import requests

from tests.integration.types import App


def test_proxy(
    juju: jubilant.Juju,
    pytestconfig: pytest.Config,
    tmp_path_factory,
    http: requests.Session,
):
    """Build and deploy the flask charm."""
    from tests.integration.conftest import build_charm_file, inject_charm_config

    app_name = "flask-k8s"
    http_proxy = "http://proxy.test"
    https_proxy = "http://https.proxy.test"
    no_proxy = "127.0.0.1,10.0.0.1"

    # Set model config for proxy
    juju.model_config(
        {
            "juju-http-proxy": http_proxy,
            "juju-https-proxy": https_proxy,
            "juju-no-proxy": no_proxy,
        }
    )

    # Build charm
    framework = "flask"
    charm_file = build_charm_file(pytestconfig, framework, tmp_path_factory)
    charm_file = inject_charm_config(
        charm_file,
        {
            "config": {
                "options": {
                    "foo-str": {"type": "string"},
                    "foo-int": {"type": "int"},
                    "foo-bool": {"type": "boolean"},
                    "foo-dict": {"type": "string"},
                    "application-root": {"type": "string"},
                }
            }
        },
        tmp_path_factory.mktemp("flask"),
    )

    resources = {
        "flask-app-image": pytestconfig.getoption("--test-flask-image"),
    }

    # Deploy the charm
    try:
        juju.deploy(charm=charm_file, app=app_name, resources=resources)
    except jubilant.CLIError as err:
        if "application already exists" not in err.stderr:
            raise err

    juju.wait(lambda status: status.apps[app_name].is_active, timeout=10 * 60)

    status = juju.status()
    for unit in status.apps[app_name].units.values():
        response = http.get(f"http://{unit.address}:8000/env", timeout=5)
        assert response.status_code == 200
        env = response.json()
        assert env["http_proxy"] == http_proxy
        assert env["HTTP_PROXY"] == http_proxy
        assert env["https_proxy"] == https_proxy
        assert env["HTTPS_PROXY"] == https_proxy
        assert env["no_proxy"] == no_proxy
        assert env["NO_PROXY"] == no_proxy
