.. _how_to_upgrade:

How to upgrade
==============

If you update the ``requirements.txt`` file for your project,
you must repack the rock using ``rockcraft pack``. Update the ``version`` in
your ``rockcraft.yaml`` to avoid issues with pulling the updated rock version
from the Kubernetes registry.

After repacking, upload the new rock using the updated ``version`` as a tag in the
registry, and refresh your deployed app using ``juju refresh``, specifying the
new rock with the ``--resource`` flag.

We pin major versions of ``paas-charm`` and do not introduce breaking changes in
minor or patch releases. To upgrade to a new version of the ``paas-charm``
library, repack the charm using ``charmcraft pack``.

