# Copyright 2024 Canonical Ltd.
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

from ops import CharmBase, HookEvent
from ops.framework import EventBase, EventSource, Object, ObjectEvents
from ops.model import Relation

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
        if self.rabbitmq_uri():
            self.on.ready.emit()

    def _on_rabbitmq_relation_departed(self, _: HookEvent) -> None:
        """Handle RabbitMQ departed."""
        if self.rabbitmq_uri():
            self.on.ready.emit()

    def _on_rabbitmq_relation_broken(self, _: HookEvent) -> None:
        """Handle RabbitMQ broken."""
        self.on.departed.emit()

    @property
    def _rabbitmq_rel(self) -> Relation | None:
        """The RabbitMQ relation."""
        return self.framework.model.get_relation(self.relation_name)

    def rabbitmq_uri(self) -> str | None:
        """Return RabbitMQ urs with the data in the relation.

        It will try to use the format in rabbitmq-k8s or rabbitmq-server.
        If there is no relation or the data is not complete, it returns None.

        Returns:
            The parameters for RabbitMQ or None.
        """
        rabbitmq_k8s_params = self._rabbitmq_k8s_uri()
        if rabbitmq_k8s_params:
            return rabbitmq_k8s_params

        # rabbitmq-server parameters or None.
        return self._rabbitmq_server_uri()

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

    def _rabbitmq_server_uri(self) -> str | None:
        """Return uri for rabbitmq-server.

        Returns:
            Returns uri for rabbitmq-server or None if the relation data is not valid/complete.
        """
        if not self._rabbitmq_rel:
            return None

        password = None
        hostnames = []
        for unit in self._rabbitmq_rel.units:
            unit_data = self._rabbitmq_rel.data[unit]
            # All of the passwords should be equal. If it is
            # in the unit data, get it and override the password
            password = unit_data.get("password", password)
            unit_hostname = unit_data.get("hostname")
            if unit_hostname:
                hostnames.append(unit_hostname)

        if not password or len(hostnames) == 0:
            return None

        hostname = hostnames[0]
        return self._build_amqp_uri(password=password, hostname=hostname)

    def _rabbitmq_k8s_uri(self) -> str | None:
        """Return URI for rabbitmq-k8s.

        Returns:
            Returns uri for rabbitmq-k8s or None if the relation data is not valid/complete.
        """
        if not self._rabbitmq_rel:
            return None

        # A password in the _rabbitmq_rel data differentiates rabbitmq-k8s from rabbitmq-server
        password = self._rabbitmq_rel.data[self._rabbitmq_rel.app].get("password")
        hostname = self._rabbitmq_rel.data[self._rabbitmq_rel.app].get("hostname")

        if not password or not hostname:
            return None

        return self._build_amqp_uri(password=password, hostname=hostname)

    def _build_amqp_uri(self, password: str, hostname: str) -> str:
        """Return amqp URI for rabbitmq from parameters.

        Args:
           password: password for amqp uri
           hostname: hostname for amqp uri

        Returns:
            Returns amqp uri for rabbitmq from parameters
        """
        # following https://www.rabbitmq.com/docs/uri-spec#the-amqp-uri-scheme,
        # vhost component of a uri should be url encoded
        vhost = urllib.parse.quote(self.vhost, safe="")
        return f"amqp://{self.username}:{password}@{hostname}:{self.port}/{vhost}"
