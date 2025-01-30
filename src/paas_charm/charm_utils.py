# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""This module defines utility functions to use by the Charm."""
import logging
import typing
from functools import wraps

import ops

from paas_charm.charm_state import CharmState
from paas_charm.exceptions import CharmConfigInvalidError

logger = logging.getLogger(__name__)


class PaasCharmBaseProtocol(typing.Protocol):  # pylint: disable=too-few-public-methods
    """Protocol to use for the decorator to block if invalid."""

    def _create_charm_state(self) -> CharmState:
        """Create charm state."""

    def update_app_and_unit_status(self, status: ops.StatusBase) -> None:
        """Update the application and unit status.

        Args:
            status: the desired application and unit status.
        """


C = typing.TypeVar("C", bound=PaasCharmBaseProtocol)
E = typing.TypeVar("E", bound=ops.EventBase)


def block_if_invalid_config(
    method: typing.Callable[[C, E], None],
) -> typing.Callable[[C, E], None]:
    """Create a decorator that puts the charm in blocked state if the config is wrong.

    Args:
        method: observer method to wrap.

    Returns:
        the function wrapper
    """

    @wraps(method)
    def wrapper(instance: C, event: E) -> None:
        """Block the charm if the config is wrong.

        Args:
            instance: the instance of the class with the hook method.
            event: the event for the observer

        Returns:
            The value returned from the original function. That is, None.
        """
        try:
            instance._create_charm_state()  # pylint: disable=protected-access
            return method(instance, event)
        except CharmConfigInvalidError as exc:
            logger.exception("Wrong Charm Configuration")
            instance.update_app_and_unit_status(ops.BlockedStatus(exc.msg))
            return None

    return wrapper
