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

Upgrade to ``paas-charm`` 2.0
-----------------------------

``paas-charm`` 2.0 is a major release with backwards-incompatible changes.
See the :ref:`2.0 release notes <release_notes_2_0>` for the full list.

``paas-charm`` 2.0 requires charms and rocks built for Ubuntu 26.04 LTS. A
Charmcraft project that retains an Ubuntu 22.04 LTS or Ubuntu 24.04 LTS base
continues to use and pin ``paas-charm`` 1.x; repacking such a project is not a
supported upgrade path to ``paas-charm`` 2.0.

Before refreshing a deployment, manually migrate and rebuild **every** rock and
charm:

1. **Move every rock to the Ubuntu 26.04 LTS build base.** Set
   ``base: ubuntu@26.04``. For a chiselled rock, set ``base: bare`` and
   ``build-base: ubuntu@26.04`` instead. Follow the
   :ref:`Rockcraft Ubuntu 26.04 LTS migration guide <rockcraft:how-to-migrate-2604>`
   and the
   `Rockcraft extension reference <https://documentation.ubuntu.com/rockcraft/stable/reference/extensions/>`_,
   including any required part-name and package changes.

   Flask and Django rocks have an additional layout change: the application
   root is now ``/app`` and ``gunicorn.conf.py`` is under
   ``/var/lib/gunicorn``. Access and error logs continue to use stdout and
   stderr. All Ubuntu 26.04 LTS framework rocks also provide ``/app-data`` as a
   writable directory owned by the ``_daemon_`` workload user.

2. **Move every charm to Ubuntu 26.04 LTS.** In a new, empty temporary
   directory, generate the Ubuntu 26.04 LTS profile for your framework:

   .. code-block:: bash

      mkdir ../myapp-ubuntu-26.04
      cd ../myapp-ubuntu-26.04
      charmcraft init --profile <framework>-framework --base ubuntu@26.04

   Do not run ``charmcraft init`` over the existing charm project. Use the
   generated files as a migration reference: merge the generated
   ``charmcraft.yaml`` and ``pyproject.toml`` changes into the existing project
   rather than replacing its files wholesale. Preserve application-specific
   configuration, actions, relations, resources, charm libraries, dependencies,
   custom parts, and project metadata. Also preserve ``paas-config.yaml`` when
   present.

   The migrated charm must use ``base: ubuntu@26.04`` and the ``uv`` plugin.
   Replace ``requirements.txt`` with ``pyproject.toml``, including both the
   generated ``paas-charm>=2.0.dev1,<3`` dependency and the existing charm's
   dependencies. Then generate and commit ``uv.lock`` from the migrated project:

   .. code-block:: bash

      uv lock

   See the
   :ref:`Charmcraft Ubuntu 26.04 LTS migration guide <charmcraft:howto-change-to-ubuntu-26-04>`
   and :ref:`Migrate your 12-factor charm to use the uv plugin <uv_migration>`.

3. **Apply the Ubuntu 26.04 LTS charm contract.** Compare the project with the
   :ref:`Charmcraft framework extension reference <charmcraft:extensions>`.
   In particular, the project must have:

   * an ``app`` container backed by an ``app-image`` OCI resource;
   * a ``peers`` relation using the ``peers`` interface;
   * one ``app-secret-key`` option of type ``secret`` (and no
     ``app-secret-key-id`` option); and
   * if used, a charm-owned ``paas-config.yaml`` staged into the packed charm.

4. **Reconfigure the application secret key.** The application secret key is now
   stored in a Juju application-owned secret. On upgrade a fresh key is
   generated, so existing sessions signed with the previous key are invalidated.
   Applications that use this key for session signing may sign out existing
   users.

   To keep user-provided secret material, store it in a Juju secret and set the
   ``app-secret-key`` option to the secret ID:

   .. code-block:: bash

      juju add-secret my-app-secret-key value=<secret-string>
      juju grant-secret my-app-secret-key myapp
      juju config myapp app-secret-key=secret:<secret id>

5. **Update relation endpoints.** The ``secret-storage`` peer relation is renamed
   to ``peers``. Update any tooling that references the old endpoint or
   interface name.

6. **Migrate Redis to Valkey.** Redis support was removed; examples and tests now
   use the ``valkey`` relation and ``/valkey/*`` endpoints. Update your charm
   metadata and application code accordingly.

7. **Build and refresh all artifacts.** Ubuntu 26.04 LTS framework support
   currently requires the tooling enablement variables when packing:

   .. code-block:: bash

      ROCKCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS=1 rockcraft pack
      CHARMCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS=1 charmcraft pack
      juju refresh myapp --path ./myapp_amd64.charm \
        --resource app-image=<registry>/<rock name>:<version>

After the refresh completes, verify the application with ``juju status`` and
confirm that the workload is active and the ingress and observability relations
are healthy.
