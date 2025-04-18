# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Useful types for integration tests."""

from typing import NamedTuple


class App(NamedTuple):
    """Holds deployed application information for app_fixture."""

    name: str


class Credentials(NamedTuple):
    """Credentials to login to an application.
    Attrs:
        email: The contact information to use to login.
        username: The identification to use to login.
        password: The secret to use to login.
    """

    email: str
    username: str
    password: str
