#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
"""Discourse integration tests."""

import logging
from typing import Dict

import jubilant
import pytest
import requests

from tests.integration.types import App

logger = logging.getLogger(__name__)


@pytest.mark.abort_on_fail
def test_active(app: App, juju: jubilant.Juju):
    """Check that the charm is active.
    Assume that the charm has already been built and is running.
    """
    status = juju.status()
    assert status.apps[app.name].units[app.name + "/0"].is_active

@pytest.mark.abort_on_fail
@pytest.mark.usefixtures("app")
def test_setup_discourse(
    app_config: Dict[str, str],
    requests_timeout: float,
    discourse_address: str,
):
    """Check discourse servers the registration page."""
    session = requests.session()
    logger.info("Getting registration page")
    # Send request to bootstrap page and set Host header to app name (which the application
    # expects)
    response = session.get(
        f"{discourse_address}/finish-installation/register",
        headers={"Host": f"{app_config['external_hostname']}"},
        timeout=requests_timeout,
        allow_redirects=True,
    )

    assert response.status_code == 200
