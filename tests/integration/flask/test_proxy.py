#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for Flask charm proxy setting."""

import requests
from juju.model import Model


async def test_proxy(build_charm: str, model: Model, test_flask_image: str, get_unit_ips):
    """Build and deploy the flask charm."""
    app_name = "flask-k8s"
    http_proxy = "http://proxy.test"
    https_proxy = "http://https.proxy.test"
    no_proxy = "127.0.0.1,10.0.0.1"
    await model.set_config(
        {
            "juju-http-proxy": http_proxy,
            "juju-https-proxy": https_proxy,
            "juju-no-proxy": no_proxy,
        }
    )
    # not using the build_charm_fixture since we need to set model configs before deploy the charm
    resources = {
        "flask-app-image": test_flask_image,
    }
    await model.deploy(build_charm, resources=resources, application_name=app_name, series="jammy")
    await model.wait_for_idle(raise_on_blocked=True)
    unit_ips = await get_unit_ips(app_name)
    for unit_ip in unit_ips:
        response = requests.get(f"http://{unit_ip}:8000/env", timeout=5)
        assert response.status_code == 200
        env = response.json()
        assert env["http_proxy"] == http_proxy
        assert env["HTTP_PROXY"] == http_proxy
        assert env["https_proxy"] == https_proxy
        assert env["HTTPS_PROXY"] == https_proxy
        assert env["no_proxy"] == no_proxy
        assert env["NO_PROXY"] == no_proxy
