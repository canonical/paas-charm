# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for Django charm integrations."""

import jubilant
import requests

from tests.integration.types import App


def test_optional_database_integration(juju: jubilant.Juju, django_db_app: App):
    """
    arrange: Charm is deployed with postgresql integration.
    act: Remove the integration.
    assert: The charm stays active (the database is optional) but database-backed
        endpoints are no longer usable.
    act: Integrate again with postgresql.
    assert: The database-backed endpoint is working again.
    """
    # the service is initially running with a working database
    status = juju.status()
    unit = list(status.apps[django_db_app.name].units.values())[0]
    unit_ip = unit.address
    response = requests.get(f"http://{unit_ip}:8000/len/users", timeout=5)
    assert response.status_code == 200

    # remove integration: the charm remains active without a database
    juju.remove_relation(django_db_app.name, "postgresql-k8s:database")
    juju.wait(lambda status: jubilant.all_active(status, django_db_app.name))

    status = juju.status()
    unit = list(status.apps[django_db_app.name].units.values())[0]
    unit_ip = unit.address
    # the database-backed endpoint is no longer usable without a database
    assert requests.get(f"http://{unit_ip}:8000/len/users", timeout=5).status_code != 200

    # add integration again and check that the service is running
    juju.integrate(django_db_app.name, "postgresql-k8s:database")
    juju.wait(lambda status: jubilant.all_active(status, django_db_app.name, "postgresql-k8s"))

    status = juju.status()
    unit = list(status.apps[django_db_app.name].units.values())[0]
    unit_ip = unit.address
    response = requests.get(f"http://{unit_ip}:8000/len/users", timeout=5)
    assert response.status_code == 200
