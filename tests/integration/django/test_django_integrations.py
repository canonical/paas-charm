# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for Django charm integrations."""

import typing

import jubilant
import pytest
import requests
from tenacity import retry, stop_after_attempt, wait_fixed

from tests.integration.types import App


def test_blocking_and_restarting_on_required_integration(
    juju: jubilant.Juju,
    django_app: App, 
    get_unit_ips: typing.Callable[[str], typing.Awaitable[tuple[str, ...]]],
):
    """
    arrange: Charm is deployed with postgresql integration.
    act: Remove integration.
    assert: The service is down.
    act: Integrate again with postgresql.
    assert: The service is working again.
    """
    # the service is initially running
    unit_ip = get_unit_ips(django_app.name)[0]
    response = requests.get(f"http://{unit_ip}:8000/len/users", timeout=5)
    assert response.status_code == 200

    # remove integration and check that the service is stopped
    juju.remove_relation(django_app.name, "postgresql-k8s:database")

    # juju.wait(lambda status: status.apps["postgresql-k8s"].relations.get(f"{django_app.name}:database") is None)
    juju.wait(lambda status: jubilant.all_blocked(status, [django_app.name]))
    unit_ip = get_unit_ips(django_app.name)[0]
    with pytest.raises(requests.exceptions.ConnectionError):
        requests.get(f"http://{unit_ip}:8000/len/users", timeout=5)
    status = juju.status()
    assert status.apps[django_app.name].units[f"{django_app.name}/0"].is_blocked
    assert "postgresql" in status.apps[django_app.name].units[f"{django_app.name}/0"].workload_status.message


    @retry(stop=stop_after_attempt(5), wait=wait_fixed(15))
    def re_integrate():
        # add integration again and check that the service is running
        juju.integrate(django_app.name, "postgresql-k8s")
        juju.wait(lambda status: jubilant.all_active(status, [django_app.name, "postgresql-k8s"]))

    re_integrate()
    unit_ip = get_unit_ips(django_app.name)[0]
    response = requests.get(f"http://{unit_ip}:8000/len/users", timeout=5)
    assert response.status_code == 200
