# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Connection fields shared by workload environments and relation templates."""

from dataclasses import asdict, dataclass
from urllib.parse import urlparse


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
