# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Connection fields shared by workload environments and relation templates."""

from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING
from urllib.parse import quote, urlparse

if TYPE_CHECKING:
    from paas_charm.rabbitmq import PaaSRabbitMQRelationData


def url_userinfo(username: str | None, password: str | None) -> str:
    """Encode raw credentials for the authority of a connection URL.

    Args:
        username: User name, if supplied.
        password: Password, if supplied (distinct from an empty password).

    Returns:
        Encoded userinfo with a trailing at-sign, or an empty string without credentials.
    """
    if username is None and password is None:
        return ""
    user = quote(username or "", safe="")
    return f"{user}@" if password is None else f"{user}:{quote(password, safe='')}@"


@dataclass(kw_only=True)
class URLFields:  # pylint: disable=too-many-instance-attributes
    """A connection string and its parsed URL components.

    Attrs:
        connect_string: Original URL.
        scheme: URL scheme.
        netloc: Network location.
        path: URL path.
        params: Path parameters.
        query: Query string.
        fragment: URL fragment.
        username: User name.
        password: Password.
        hostname: Host name.
        port: Port number as text.
    """

    connect_string: str
    scheme: str
    netloc: str
    path: str
    params: str
    query: str
    fragment: str
    username: str | None
    password: str | None
    hostname: str | None
    port: str | None

    def available(self) -> dict[str, str]:
        """Return the populated fields.

        Returns:
            Field names mapped to values.
        """
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass(kw_only=True)
class DatabaseURLFields(URLFields):
    """URL components for a database.

    Attrs:
        name: Database name from the URL path.
    """

    name: str | None


@dataclass(kw_only=True)
class RabbitURLFields(URLFields):
    """URL components for a RabbitMQ connection.

    Attrs:
        connect_strings: Comma-separated broker URLs, if supplied.
    """

    connect_strings: str | None


def url_fields(url: str) -> URLFields:
    """Parse a connection string.

    Args:
        url: Connection URL.

    Returns:
        Components in workload string format.
    """
    parsed = urlparse(url)
    return URLFields(
        connect_string=url,
        **parsed._asdict(),
        username=parsed.username,
        password=parsed.password,
        hostname=parsed.hostname,
        port=None if parsed.port is None else str(parsed.port),
    )


def database_fields(url: str) -> dict[str, str]:
    """Extract the populated database URL fields.

    Args:
        url: Database connection string.

    Returns:
        URL components and database name.
    """
    if not url:
        return {}
    parts = url_fields(url)
    return DatabaseURLFields(
        **asdict(parts), name=parts.path.removeprefix("/") if parts.path else None
    ).available()


def rabbit_fields(data: "PaaSRabbitMQRelationData") -> dict[str, str]:
    """Get RabbitMQ connection fields for both templates and workload variables.

    Args:
        data: Broker connection information.

    Returns:
        Populated URL components and virtual host.
    """
    fields = RabbitURLFields(
        **asdict(url_fields(data.amqp_uri)), connect_strings=",".join(data.amqp_uris) or None
    ).available()
    fields.update(username=data.username, password=data.password)
    if data.vhost:
        fields["vhost"] = data.vhost
    return fields
