# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Test deprecated Charm entrypoints."""

import paas_app_charmer.django
import paas_app_charmer.fastapi
import paas_app_charmer.flask
import paas_app_charmer.go
import paas_charm.django
import paas_charm.fastapi
import paas_charm.flask
import paas_charm.go


def test_deprecated_paths():
    """
    Test that the deprecated classes are subclasses of the correct new entrypoints.
    """
    assert issubclass(paas_app_charmer.django.Charm, paas_charm.django.Charm)
    assert issubclass(paas_app_charmer.fastapi.Charm, paas_charm.fastapi.Charm)
    assert issubclass(paas_app_charmer.flask.Charm, paas_charm.flask.Charm)
    assert issubclass(paas_app_charmer.go.Charm, paas_charm.go.Charm)
