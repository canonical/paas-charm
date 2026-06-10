# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

import jubilant
import requests

from tests.integration.ingress.conftest import HOSTNAME
from tests.integration.types import App


def test_ingress_go(
    juju: jubilant.Juju,
    go_app: App,
    ingress_provider: tuple[str, str],
    gateway_lb_ip: str,
):
    gateway_app, configurator_app = ingress_provider
    try:
        juju.integrate(go_app.name, configurator_app)
    except jubilant.CLIError as err:
        if "already exists" not in err.stderr:
            raise err
    juju.wait(
        lambda status: jubilant.all_active(status, go_app.name, gateway_app, configurator_app),
        timeout=10 * 60,
        delay=5,
    )
    response = requests.get(
        f"http://{gateway_lb_ip}",
        headers={"Host": HOSTNAME},
        timeout=30,
    )
    assert response.status_code == 200
