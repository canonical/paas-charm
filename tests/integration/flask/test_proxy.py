#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for Flask charm proxy setting."""

import requests
import jubilant
import pytest

from tests.integration.conftest import build_charm_file


def test_proxy(
    juju: jubilant.Juju,
    pytestconfig: pytest.Config,
    test_flask_image: str,
    tmp_path_factory,
):
    """Build and deploy the flask charm with proxy settings."""
    app_name = "flask-k8s"
    http_proxy = "http://proxy.test"
    https_proxy = "http://https.proxy.test"
    no_proxy = "127.0.0.1,10.0.0.1"
    
    # Set model config for proxy
    juju.cli(
        "model-config",
        f"juju-http-proxy={http_proxy}",
        f"juju-https-proxy={https_proxy}",
        f"juju-no-proxy={no_proxy}",
    )
    
    # Build charm
    charm_file = build_charm_file(pytestconfig, "flask", tmp_path_factory)
    resources = {"flask-app-image": test_flask_image}
    
    # Deploy
    try:
        juju.deploy(charm=str(charm_file), app=app_name, resources=resources)
    except jubilant.CLIError as err:
        if "application already exists" not in err.stderr:
            raise err
    
    juju.wait(lambda status: jubilant.all_active(status, app_name), timeout=10 * 60)
    
    # Verify proxy settings
    status = juju.status()
    for unit in status.apps[app_name].units.values():
        response = requests.get(f"http://{unit.address}:8000/env", timeout=5)
        assert response.status_code == 200
        env = response.json()
        assert env["http_proxy"] == http_proxy
        assert env["HTTP_PROXY"] == http_proxy
        assert env["https_proxy"] == https_proxy
        assert env["HTTPS_PROXY"] == https_proxy
        assert env["no_proxy"] == no_proxy
        assert env["NO_PROXY"] == no_proxy
