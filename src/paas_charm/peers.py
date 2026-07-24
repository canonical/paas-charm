# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Provide the Peers helper for peer coordination (peer unit FQDNs)."""

import typing

import ops

from paas_charm.utils import build_k8s_unit_fqdn


class Peers(ops.Object):
    """Expose peer coordination data such as peer unit FQDNs.

    Attrs:
        is_related: True if the peer relation exists.
    """

    def __init__(self, charm: ops.CharmBase, peer_relation_name: str = "peers"):
        """Initialize the Peers helper.

        Args:
            charm: The charm object that uses the peer relation.
            peer_relation_name: The name of the peer relation.
        """
        super().__init__(parent=charm, key=peer_relation_name)
        self._charm = charm
        self._peer_relation_name = peer_relation_name

    @property
    def is_related(self) -> bool:
        """Return whether the peer relation exists.

        Returns:
            True if the peer relation exists, False otherwise.
        """
        return self._charm.model.get_relation(self._peer_relation_name) is not None

    def get_peer_unit_fqdns(self) -> list | None:
        """Get the FQDNs of the units in the peer relation.

        Returns:
            Sorted list of peer unit FQDNs, or None if there are none.
        """
        if not self.is_related:
            return None
        peer_relation = typing.cast(
            ops.Relation, self._charm.model.get_relation(self._peer_relation_name)
        )
        unit_names = [unit.name for unit in peer_relation.units]
        unit_fqdns = []
        for unit_name in sorted(unit_names):
            unit_fqdn = build_k8s_unit_fqdn(
                self._charm.model.app.name, unit_name, self._charm.model.name
            )
            unit_fqdns.append(unit_fqdn)
        if not unit_fqdns:
            return None
        return unit_fqdns
