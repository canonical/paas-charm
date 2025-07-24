.. _how_to_upgrade:

How to upgrade
==============

If you update any files in your project (for instance, ``requirements.txt``),
you must repack the rock using ``rockcraft pack``. Update the ``version`` in
your ``rockcraft.yaml`` to avoid issues with pulling the updated rock version
from the Kubernetes registry.

After repacking, upload the new rock using an updated `tag <https://docs.docker.com/reference/cli/docker/image/tag/>`_
in the registry, and refresh your deployed app using ``juju refresh``, specifying the
new rock with the ``--resource`` flag.

We pin major versions of ``paas-charm`` and do not introduce breaking changes in
minor or patch releases. To upgrade to a new version of the ``paas-charm``
library, repack the charm using ``charmcraft pack``.

