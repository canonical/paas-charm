# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Global fixtures and utilities for integration and unit tests."""


def pytest_addoption(parser):
    """Define command line options for integration and unit tests."""
    parser.addoption("--kube-config", action="store")
    parser.addoption("--keep-models", action="store_true", default=False)
    parser.addoption("--model", action="store", default=None)
    parser.addoption("--use-existing", action="store_true", default=False)
    parser.addoption("--controller", action="store", default="concierge-k8s")
