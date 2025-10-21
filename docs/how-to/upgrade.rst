.. _how_to_upgrade:

How to upgrade
==============

When updating your project, you may need to rebuild and redeploy both rocks and charms. This guide 
explains how to safely upgrade your deployment.

Repack your rock
----------------

If you update any files in your project (for instance, ``requirements.txt``, ``rockcraft.yaml``, 
or application source code), you must repack the rock using ``rockcraft pack``. 

.. code-block:: bash

   rockcraft pack

This command creates a new ``.rock`` file in the current directory. Before packing, make sure
to bump the ``version`` field in your ``rockcraft.yaml`` to properly track versions of your rock
and help avoid Kubernetes caching an old version of the image.

Push the rock to the registry
-----------------------------

Once repacked, upload the new rock using an updated 
`tag <https://docs.docker.com/reference/cli/docker/image/tag/>`_ in your container registry:

.. code-block:: bash

   sudo rockcraft.skopeo copy \
   --insecure-policy \
   oci-archive:myapp_0.2_amd64.rock \
   docker-daemon:myapp:0.2

Refresh the deployed application
--------------------------------

Once your new rock is available in the registry, refresh your Juju application to use it.
Use the ``juju refresh`` command and specify the new rock as a resource:

.. code-block:: bash
    
    juju refresh myapp --resource app-image=localhost:32000/myapp:0.2

If your charm was deployed from a local path, you also need to provide the charm path when
refreshing the application:

.. code-block:: bash
    
    juju refresh myapp --resource app-image=localhost:32000/myapp:0.1 \
    --path ./myapp-22.04-amd64.charm

Upgrading the charm itself
--------------------------

If you've made changes to the charm source code, you need to repack the charm:

.. code-block:: bash

    charmcraft pack

This generates a ``.charm`` file in the current directory. You can then refresh it in Juju:

.. code-block:: bash

    juju refresh myapp --path ./myapp-22.04-amd64.charm

We pin major versions of ``paas-charm`` and do not introduce breaking changes in
minor or patch releases. To upgrade to a new version of the ``paas-charm``
library, repack the charm using ``charmcraft pack``.

