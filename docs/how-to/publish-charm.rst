.. meta::
   :description: Learn about the process to publish your 12-factor app charm to Charmhub. 

.. _how_to_publish_charm:

How to publish a 12-factor app charm to Charmhub
=================================================

This guide explains how to upload and release a 12-factor app charm and its
OCI image resource to `Charmhub <https://charmhub.io>`_.

Prerequisites
-------------

- A Charmhub account. Register at https://charmhub.io.
- ``charmcraft`` installed (``snap install charmcraft --classic``).
- A built charm (``.charm`` file) and an OCI image (as a ``.rock`` file, a local Docker image, or a remote registry reference).

Log in to Charmhub
------------------

.. code-block:: bash

   charmcraft login

Register your charm name
------------------------

If you haven't already, reserve your charm's name on Charmhub:

.. code-block:: bash

   charmcraft register <charm-name>

Upload the charm
----------------

Pack the charm, then upload it:

.. code-block:: bash

   charmcraft pack
   charmcraft upload <charm-file>.charm

On success, ``charmcraft upload`` prints the revision number assigned to the
charm. Note this number — you'll need it when releasing the charm publicly.

Identify the OCI image resource name
-------------------------------------

Each 12-factor app charm exposes exactly one OCI image resource. The name of
that resource depends on the framework:

.. list-table::
   :header-rows: 1

   * - Framework
     - Resource name
   * - Django
     - ``django-app-image``
   * - Flask
     - ``flask-app-image``
   * - FastAPI
     - ``app-image``
   * - Express.js
     - ``app-image``
   * - Go
     - ``app-image``
   * - Spring Boot
     - ``app-image``

You can always confirm the resource name for your specific charm by inspecting
the ``resources`` section of your expanded ``charmcraft.yaml``:

.. code-block:: bash

   charmcraft expand-extensions | grep -A3 'resources:'

Upload the OCI image resource
------------------------------

You can upload the OCI image from a local ``.rock`` file, from a local
Docker daemon, or from a remote image registry.

**From a local .rock file**

If you have a ``.rock`` file, upload it directly:

.. code-block:: bash

   charmcraft upload-resource <charm-name> <resource-name> \
       --image <rock-file>.rock

**From a local Docker daemon**

If the image is already loaded in your local Docker daemon, reference it by
tag or image ID:

.. code-block:: bash

   charmcraft upload-resource <charm-name> <resource-name> \
       --image <image-tag-or-id>

**From a remote registry**

Pass the full registry reference with the ``docker://`` scheme:

.. code-block:: bash

   charmcraft upload-resource <charm-name> <resource-name> \
       --image docker://<registry-host>/<image-name>:<image-tag>

For example, if your OCI image is uploaded to the ``ghcr.io`` registry:

.. code-block:: bash

   charmcraft upload-resource <charm-name> <resource-name> \
       --image docker://ghcr.io/<org>/<image-name>:<image-tag>

On success, ``charmcraft upload-resource`` prints the resource revision
number. Note this number — you'll need it when releasing the charm publicly.

Release the charm
-----------------

Release the charm revision together with the resource revision to a channel:

.. code-block:: bash

   charmcraft release <charm-name> \
       --revision=<charm-revision> \
       --channel=<channel> \
       --resource=<resource-name>:<resource-revision>

For example:

.. code-block:: bash

   charmcraft release my-flask-app \
       --revision=1 \
       --channel=latest/edge \
       --resource=flask-app-image:1

.. seealso::

   - `Charmcraft upload <https://documentation.ubuntu.com/charmcraft/en/latest/reference/commands/upload/>`_
   - `Charmcraft upload-resource <https://documentation.ubuntu.com/charmcraft/en/latest/reference/commands/upload-resource/>`_
   - `Charmcraft release <https://documentation.ubuntu.com/charmcraft/en/latest/reference/commands/release/>`_
