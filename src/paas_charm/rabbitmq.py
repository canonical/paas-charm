# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""RabbitMQ library for handling the rabbitmq interface.

The project https://github.com/openstack-charmers/charm-rabbitmq-k8s provides
a library for the requires part of the rabbitmq interface.

However, there are two charms that provide the rabbitmq interface, being incompatible:
 - https://github.com/openstack-charmers/charm-rabbitmq-ks8 (https://charmhub.io/rabbitmq-k8s)
 - https://github.com/openstack/charm-rabbitmq-server/ (https://charmhub.io/rabbitmq-server)

The main difference is that rabbitmq-server does not publish the information in the app
part in the relation bag. This python library unifies both charms, using a similar
approach to the rabbitmq-k8s library.

For rabbitmq-k8s, the password and hostname are required in the app databag. The full
list of hostnames can be obtained from the ingress-address in each unit.

For rabbitmq-server, the app databag is empty. The password and hostname are in the units databags,
being the password equal in all units. Each hostname may point to different addresses. One
of them will chosen as the in the rabbitmq parameters.

rabbitmq-server support ssl client certificates, but are not implemented in this library.

This library is very similar and uses the same events as
 the library charms.rabbitmq_k8s.v0.rabbitmq.
See https://github.com/openstack-charmers/charm-rabbitmq-k8s/blob/main/lib/charms/rabbitmq_k8s/v0/rabbitmq.py  # pylint: disable=line-too-long # noqa: W505
"""


import logging
import urllib.parse
from typing import NamedTuple

from ops import CharmBase, HookEvent
from ops.framework import EventBase, EventSource, Object, ObjectEvents
from ops.model import Relation
from pydantic import BaseModel, ValidationError

from paas_charm.exceptions import InvalidRelationDataError
from paas_charm.utils import build_validation_error_message

logger = logging.getLogger(__name__)


class RabbitMQConnectedEvent(EventBase):
    """RabbitMQ connected Event."""


class RabbitMQReadyEvent(EventBase):
    """RabbitMQ ready for use Event."""


class RabbitMQDepartedEvent(EventBase):
    """RabbitMQ relation departed Event."""


class RabbitMQServerEvents(ObjectEvents):
    """Events class for `on`.

    Attributes:
        connected: rabbitmq relation is connected
        ready: rabbitmq relation is ready
        departed: rabbitmq relation has been removed
    """

    connected = EventSource(RabbitMQConnectedEvent)
    ready = EventSource(RabbitMQReadyEvent)
    departed = EventSource(RabbitMQDepartedEvent)


class InvalidRabbitMQRelationDataError(InvalidRelationDataError):
    """Represents an error with invalid RabbitMQ relation data.

    Attributes:
        relation: The RabbitMQ relation name.
    """

    relation = "rabbitmq"


class PaaSRabbitMQRelationData(BaseModel):
    """Rabbit MQ relation data.

    Attributes:
        vhost: virtual host to use for RabbitMQ.
        port: RabbitMQ port.
        hostname: hostname of the RabbitMQ server.
        username: username to use for RabbitMQ.
        password: password to use for RabbitMQ.
        amqp_uri: amqp uri for connecting to RabbitMQ server.
    """

    vhost: str
    port: int
    hostname: str
    username: str
    password: str

    @property
    def amqp_uri(self) -> str:
        """AMQP URI for rabbitmq from parameters."""
        # following https://www.rabbitmq.com/docs/uri-spec#the-amqp-uri-scheme,
        # vhost component of a uri should be url encoded
        vhost = urllib.parse.quote(self.vhost, safe="")
        return f"amqp://{self.username}:{self.password}@{self.hostname}:{self.port}/{vhost}"


class Credentials(NamedTuple):
    """Credentials wrapper.

    Attributes:
        hostname: The connection hostname.
        password: The connection password.
    """

    hostname: str
    password: str


class RabbitMQRequires(Object):
    """RabbitMQRequires class.

    Attributes:
        on: ObjectEvents for RabbitMQRequires
        port: amqp port
    """

    on = RabbitMQServerEvents()
    port = 5672

    def __init__(self, charm: CharmBase, relation_name: str, username: str, vhost: str):
        """Initialize the instance.

        Args:
           charm: charm that uses the library
           relation_name: name of the RabbitMQ relation
           username: username to use for RabbitMQ
           vhost: virtual host to use for RabbitMQ
        """
        super().__init__(charm, relation_name)
        self.charm = charm
        self.relation_name = relation_name
        self.username = username
        self.vhost = vhost
        self.framework.observe(
            self.charm.on[relation_name].relation_joined,
            self._on_rabbitmq_relation_joined,
        )
        self.framework.observe(
            self.charm.on[relation_name].relation_changed,
            self._on_rabbitmq_relation_changed,
        )
        self.framework.observe(
            self.charm.on[relation_name].relation_departed,
            self._on_rabbitmq_relation_departed,
        )
        self.framework.observe(
            self.charm.on[relation_name].relation_broken,
            self._on_rabbitmq_relation_broken,
        )

    def _on_rabbitmq_relation_joined(self, _: HookEvent) -> None:
        """Handle RabbitMQ joined."""
        self.on.connected.emit()
        self.request_access(self.username, self.vhost)

    def _on_rabbitmq_relation_changed(self, _: HookEvent) -> None:
        """Handle RabbitMQ changed."""
        if self.get_relation_data():
            self.on.ready.emit()

    def _on_rabbitmq_relation_departed(self, _: HookEvent) -> None:
        """Handle RabbitMQ departed."""
        if self.get_relation_data():
            self.on.ready.emit()

    def _on_rabbitmq_relation_broken(self, _: HookEvent) -> None:
        """Handle RabbitMQ broken."""
        self.on.departed.emit()

    @property
    def _rabbitmq_rel(self) -> Relation | None:
        """The RabbitMQ relation."""
        return self.framework.model.get_relation(self.relation_name)

    @property
    def _rabbitmq_server_connection_params(self) -> Credentials | None:
        """The RabbitMQ hostname, password."""
        if not self._rabbitmq_rel:
            return None
        for unit in self._rabbitmq_rel.units:
            unit_data = self._rabbitmq_rel.data[unit]
            # All of the passwords should be equal. If it is
            # in the unit data, get it and override the password
            hostname = unit_data.get("hostname", None)
            password = unit_data.get("password", None)
            if hostname and password:
                return Credentials(hostname, password)
        return None

    @property
    def _rabbitmq_k8s_connection_params(self) -> Credentials | None:
        """The RabbitMQ hostname, password."""
        if not self._rabbitmq_rel:
            return None
        hostname = self._rabbitmq_rel.data[self._rabbitmq_rel.app].get("hostname", None)
        password = self._rabbitmq_rel.data[self._rabbitmq_rel.app].get("password", None)
        if hostname and password:
            return Credentials(hostname, password)
        return None

    def request_access(self, username: str, vhost: str) -> None:
        """Request access to the RabbitMQ server.

        Args:
           username: username requested for RabbitMQ
           vhost: virtual host requested for RabbitMQ
        """
        if self.model.unit.is_leader():
            if not self._rabbitmq_rel:
                logger.warning("request_access but no rabbitmq relation")
                return
            self._rabbitmq_rel.data[self.charm.app]["username"] = username
            self._rabbitmq_rel.data[self.charm.app]["vhost"] = vhost

    def get_relation_data(self) -> PaaSRabbitMQRelationData | None:
        """Return RabbitMQ relation data.

        Raises:
            InvalidRabbitMQRelationDataError: If any invalid data was found over the relation data.

        Returns:
            RabbitMQ relation data if it is valid. None otherwise.
        """
        password = None
        hostname = None
        if self._rabbitmq_k8s_connection_params:
            hostname = self._rabbitmq_k8s_connection_params.hostname
            password = self._rabbitmq_k8s_connection_params.password
        elif self._rabbitmq_server_connection_params:
            hostname = self._rabbitmq_server_connection_params.hostname
            password = self._rabbitmq_server_connection_params.password
        if not password or not hostname:
            return None
        try:
            return PaaSRabbitMQRelationData(
                username=self.username,
                password=password,
                hostname=hostname,
                port=self.port,
                vhost=self.vhost,
            )
        # Validation error cannot happen unless there's an issue in code as only hostname and
        # password values come from the relation data.
        except ValidationError as exc:  # pragma: nocover
            error_messages = build_validation_error_message(exc, underscore_to_dash=True)
            logger.error(error_messages.long)
            raise InvalidRabbitMQRelationDataError(
                f"Invalid {PaaSRabbitMQRelationData.__name__}: {error_messages.short}"
            ) from exc
