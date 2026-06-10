# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.
import jubilant
import pytest
from lightkube import Client
from lightkube.generic_resource import create_namespaced_resource
from lightkube.resources.core_v1 import Service
from tenacity import retry, stop_after_attempt, wait_fixed

HOSTNAME = "gateway.internal"


@pytest.fixture(scope="module", name="ingress_provider")
def ingress_provider_fixture(
    juju: jubilant.Juju,
):
    juju.deploy(
        charm="gateway-api-integrator",
        app="gateway",
        channel="latest/edge",
        trust=True,
        config={"gateway-class": "ck-gateway"},
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
        # gateway/configurator can be blocked before the app-ingress relation is created.
        lambda status: jubilant.all_active(status, "cert"),
        timeout=10 * 60,
    )
    return ("gateway", "configurator")


def gateway_lb_ip(juju: jubilant.Juju, ingress_provider: tuple[str, str]) -> str:
    gateway_resource = create_namespaced_resource(
        group="gateway.networking.k8s.io",
        version="v1",
        kind="Gateway",
        plural="gateways",
    )

    @retry(stop=stop_after_attempt(12), wait=wait_fixed(5))
    def _gateway_lb_ip() -> str:
        gateway_app, _ = ingress_provider
        model_name = juju.status().model.name
        client = Client()
        service = client.get(Service, name=gateway_app, namespace=model_name)
        if (
            service.status
            and service.status.loadBalancer
            and service.status.loadBalancer.ingress
            and service.status.loadBalancer.ingress[0].ip
        ):
            return service.status.loadBalancer.ingress[0].ip

        gateway = client.get(gateway_resource, name=gateway_app, namespace=model_name)
        gateway_status = getattr(gateway, "status", None)
        if isinstance(gateway_status, dict):
            addresses = gateway_status.get("addresses")
        else:
            addresses = getattr(gateway_status, "addresses", None)
        if not addresses:
            raise ValueError(f"No addresses in Gateway status for resource {gateway_app!r}")
        if isinstance(addresses[0], dict):
            address_value = addresses[0].get("value")
        else:
            address_value = getattr(addresses[0], "value", None)
        if not address_value:
            raise ValueError(f"No Gateway address value set for resource {gateway_app!r}")
        return address_value

    return _gateway_lb_ip()
