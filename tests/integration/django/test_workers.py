#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for Django charm."""
import asyncio
import logging
import time
import typing

import pytest
import requests
from juju.application import Application
from juju.model import Model
from juju.utils import block_until
from pytest_operator.plugin import OpsTest

logger = logging.getLogger(__name__)


@pytest.mark.parametrize(
    "worker_class, expected_result",
    [
        ("eventlet", "blocked"),
        ("gevent", "active"),
        ("sync", "active"),
    ],
)
@pytest.mark.usefixtures("django_async_app")
async def test_async_workers_config(
    ops_test: OpsTest,
    model: Model,
    django_async_app: Application,
    get_unit_ips,
    worker_class: str,
    expected_result: bool,
):
    """
    arrange: Django is deployed with async enabled rock.
    act: Change gunicorn worker class.
    assert: Charm should only let the class to be 'sync' or 'gevent'.
    If it is something other than these, then the unit should be blocked.
    """
    await django_async_app.set_config({"webserver-worker-class": worker_class})
    await model.wait_for_idle(apps=[django_async_app.name], status=expected_result, timeout=60)


@pytest.mark.parametrize(
    "worker_class, expected_result",
    [
        ("gevent", "blocked"),
        ("eventlet", "blocked"),
        ("sync", "active"),
    ],
)
@pytest.mark.usefixtures("django_app")
async def test_async_workers_config_fail(
    ops_test: OpsTest,
    model: Model,
    django_app: Application,
    get_unit_ips,
    worker_class: str,
    expected_result: str,
):
    """
    arrange: Django is deployed with async not enabled rock.
    act: Change gunicorn worker class.
    assert: Charm should only let the class to be 'sync'.
    If it is 'gevent' or something else, then the unit should be blocked.
    """
    await django_app.set_config({"webserver-worker-class": worker_class})
    await model.wait_for_idle(apps=[django_app.name], status=expected_result, timeout=60)
