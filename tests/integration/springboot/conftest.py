# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

import logging
import time

import jubilant
import kubernetes
import pytest

from tests.integration.types import App

logger = logging.getLogger(__name__)

WORKLOAD_PORT = 8080


@pytest.fixture(scope="module", name="spring_boot_unit_ip")
def spring_boot_unit_ip_fixture(juju: jubilant.Juju, spring_boot_app: App):
    """Spring boot unit IP."""
    status = juju.status()
    spring_boot_unit: jubilant.statustypes.UnitStatus = status.apps[spring_boot_app.name].units[
        f"{spring_boot_app.name}/0"
    ]
    return spring_boot_unit.address


@pytest.fixture(scope="module", name="simplesamlphp_ip")
def simplesamlphp_ip_fixture(
    pytestconfig: pytest.Config, juju: jubilant.Juju, spring_boot_unit_ip: str
) -> str:
    """Deploy test Simple SAML IDP service.

    Returns the pod IP of the deployed application.
    """
    kube_config = pytestconfig.getoption("--kube-config")
    kubernetes.config.load_kube_config(config_file=kube_config)
    namespace = juju.status().model.name
    v1 = kubernetes.client.CoreV1Api()
    pod = kubernetes.client.V1Pod(
        api_version="v1",
        kind="Pod",
        metadata=kubernetes.client.V1ObjectMeta(
            name="simplesamlphp",
            namespace=namespace,
            labels={"app.kubernetes.io/name": "simplesamlphp"},
        ),
        spec=kubernetes.client.V1PodSpec(
            containers=[
                kubernetes.client.V1Container(
                    name="saml",
                    image="kenchan0130/simplesamlphp",
                    ports=[
                        kubernetes.client.V1ContainerPort(container_port=8080),
                    ],
                    env=[
                        kubernetes.client.V1EnvVar(
                            name="SIMPLESAMLPHP_SP_ENTITY_ID",
                            # Spring boot application address as entity ID
                            value=f"{spring_boot_unit_ip}:8080",
                        ),
                        kubernetes.client.V1EnvVar(
                            name="SIMPLESAMLPHP_SP_ASSERTION_CONSUMER_SERVICE",
                            value=f"http://{spring_boot_unit_ip}:8080/login/saml2/sso/"
                            "testentity",
                        ),
                        kubernetes.client.V1EnvVar(
                            name="SIMPLESAMLPHP_SP_SINGLE_LOGOUT_SERVICE",
                            value=f"http://{spring_boot_unit_ip}:8080/simplesaml/module.php/"
                            "saml/sp/saml2-logout.php/testentity",
                        ),
                    ],
                )
            ],
        ),
    )
    v1.create_namespaced_pod(namespace=namespace, body=pod)
    service = kubernetes.client.V1Service(
        api_version="v1",
        kind="Service",
        metadata=kubernetes.client.V1ObjectMeta(name="simplesamlphp-service", namespace=namespace),
        spec=kubernetes.client.V1ServiceSpec(
            type="ClusterIP",
            ports=[
                kubernetes.client.V1ServicePort(port=8080, target_port=8080, name="tcp-8080"),
            ],
            selector={"app.kubernetes.io/name": "simplesamlphp"},
        ),
    )
    v1.create_namespaced_service(namespace=namespace, body=service)
    deadline = time.time() + 300
    pod_ip = None
    while True:
        if time.time() > deadline:
            raise TimeoutError("timeout while waiting for simplesamlphp pod")
        try:
            pod = v1.read_namespaced_pod(name="simplesamlphp", namespace=namespace)
            if pod.status.phase == "Running":
                logger.info("simplesamlphp running at %s", pod.status.pod_ip)
                pod_ip = pod.status.pod_ip
                break
        except kubernetes.client.ApiException:
            pass
        logger.info("waiting for simplesamlphp pod")
        time.sleep(1)
    return pod_ip


@pytest.fixture(scope="module", name="saml_integrator")
def saml_integrator_fixture(juju: jubilant.Juju, simplesamlphp_ip: str):
    """SAML integrator charm."""
    saml_config = {
        "entity_id": f"http://{simplesamlphp_ip}:8080/simplesaml/saml2/idp/metadata.php",
        "metadata_url": f"http://{simplesamlphp_ip}:8080/simplesaml/saml2/idp/metadata.php",
    }
    juju.deploy("saml-integrator", channel="latest/stable", config=saml_config, trust=True)
    yield App("saml-integrator")
