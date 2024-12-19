# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

from django.apps import AppConfig


class TestingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "testing"
