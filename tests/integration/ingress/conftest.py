# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.
import jubilant
import pytest
from lightkube import Client
from lightkube.resources.core_v1 import Service
from tenacity import retry, stop_after_attempt, wait_fixed

HOSTNAME = "example.com"


@pytest.fixture(scope="module", name="ingress_provider")
def ingress_provider_fixture(
    juju: jubilant.Juju,
):
    juju.deploy(
        charm="gateway-api-integrator",
        app="gateway",
        channel="latest/edge",
    )
    juju.deploy(
        charm="gateway-route-configurator",
        app="configurator",
        channel="latest/edge",
        config={"hostname": HOSTNAME},
    )
    juju.deploy(
        charm="self-signed-certificates",
        app="cert",
        channel="1/edge",
    )
    juju.integrate("cert:certificates", "gateway:certificates")
    juju.integrate("configurator:gateway-route", "gateway:gateway-route")

    juju.wait(
        lambda status: jubilant.all_active(status, "gateway", "configurator", "cert"),
        timeout=10 * 60,
    )
    return ("gateway", "configurator")


@pytest.fixture(scope="module", name="gateway_lb_ip")
def gateway_lb_ip_fixture(juju: jubilant.Juju, ingress_provider: tuple[str, str]) -> str:
    @retry(stop=stop_after_attempt(12), wait=wait_fixed(5))
    def _gateway_lb_ip() -> str:
        gateway_app, _ = ingress_provider
        model_name = juju.status().model.name
        service = Client().get(Service, name=gateway_app, namespace=model_name)
        if not service.status or not service.status.loadBalancer:
            raise ValueError(f"LoadBalancer status not ready for service {gateway_app!r}")
        if not service.status.loadBalancer.ingress:
            raise ValueError(f"No ingress entries in LoadBalancer status for service {gateway_app!r}")
        ingress_ip = service.status.loadBalancer.ingress[0].ip
        if not ingress_ip:
            raise ValueError(f"No LoadBalancer IP assigned for service {gateway_app!r}")
        return ingress_ip

    return _gateway_lb_ip()
