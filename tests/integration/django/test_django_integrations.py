# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for Django charm integrations."""

import jubilant
import pytest
import requests

from tests.integration.types import App


def test_blocking_and_restarting_on_required_integration(
    juju: jubilant.Juju, django_app: App
):
    """
    arrange: Charm is deployed with postgresql integration.
    act: Remove integration.
    assert: The service is down.
    act: Integrate again with postgresql.
    assert: The service is working again.
    """
    # the service is initially running
    status = juju.status()
    unit = list(status.apps[django_app.name].units.values())[0]
    unit_ip = unit.address
    response = requests.get(f"http://{unit_ip}:8000/len/users", timeout=5)
    assert response.status_code == 200

    # remove integration and check that the service is stopped
    juju.remove_relation(django_app.name, "postgresql-k8s:database")

    juju.wait(lambda status: jubilant.all_blocked(status, django_app.name))
    
    status = juju.status()
    unit = list(status.apps[django_app.name].units.values())[0]
    unit_ip = unit.address
    
    with pytest.raises(requests.exceptions.ConnectionError):
        requests.get(f"http://{unit_ip}:8000/len/users", timeout=5)
    
    assert unit.is_blocked
    assert "postgresql" in unit.workload_status_message

    # add integration again and check that the service is running
    juju.integrate(django_app.name, "postgresql-k8s:database")
    juju.wait(lambda status: jubilant.all_active(status, django_app.name, "postgresql-k8s"))

    status = juju.status()
    unit = list(status.apps[django_app.name].units.values())[0]
    unit_ip = unit.address
    response = requests.get(f"http://{unit_ip}:8000/len/users", timeout=5)
    assert response.status_code == 200
