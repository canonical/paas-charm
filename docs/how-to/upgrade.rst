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

   Extension-generated Rockcraft part names use ``/`` as their separator on
   lower bases and ``.`` when the effective build base is Ubuntu 26.04 LTS.
   For a bare rock, ``build-base`` determines the separator. Preserve the newly
   generated names and update custom ``parts`` overrides, ``after`` references,
   selectors, scripts, patches, CI assertions, and other configuration that
   names generated extension parts. For example,
   ``flask-framework/dependencies`` becomes
   ``flask-framework.dependencies``, and
   ``django-framework/dependencies`` becomes
   ``django-framework.dependencies``. Not every generated part exists for
   every framework, so compare overrides with the expanded Ubuntu 26.04 LTS
   project rather than changing names blindly.

   Flask and Django rocks have an additional layout change: the application
   root is now ``/app`` and ``gunicorn.conf.py`` is under
   ``/var/lib/gunicorn``. Access and error logs continue to use stdout and
   stderr. All Ubuntu 26.04 LTS framework rocks also provide ``/app-data`` as a
   writable directory owned by the ``_daemon_`` workload user.

2. **Generate the migrated Ubuntu 26.04 LTS charm project.** Choose the
   framework profile that matches the existing charm. In the commands below,
   replace ``<FRAMEWORK>`` with ``django``, ``expressjs``, ``fastapi``,
   ``flask``, ``go``, or ``spring-boot``.

   From the directory that contains the existing charm project, create a new
   ``charm-26-04`` directory and initialize the Ubuntu 26.04 LTS profile there:

   .. code-block:: bash

      mkdir charm-26-04
      cd charm-26-04
      CHARMCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS=1 \
        charmcraft init --profile <FRAMEWORK>-framework --base ubuntu@26.04

   Do not run this command in the existing charm directory. ``charmcraft init``
   does not overwrite existing files, so it cannot safely update an initialized
   project in place.

3. **Move application-specific work into the generated project.** Use
   ``charm-26-04`` as the migration destination. Copy the existing charm's
   application and charm source code and tests into the corresponding generated
   locations. Carry only the manual customizations from old generated or
   initialized files into their new counterparts; do not replace generated
   files wholesale with the old versions.

   Preserve relevant application-specific metadata, configuration, actions,
   relations, resources, charm libraries, dependencies, and custom parts.
   Preserve the charm-owned ``paas-config.yaml`` when present.

   Keep the generated Ubuntu 26.04 LTS contract, including:

   * ``base: ubuntu@26.04`` and the generated platform definitions;
   * the ``uv`` charm part and generated ``pyproject.toml`` project structure;
   * the ``app`` workload container and ``app-image`` OCI resource;
   * the ``peers`` peer relation with the ``peers`` interface;
   * one ``app-secret-key`` option of type ``secret``, with no
     ``app-secret-key-id`` option;
   * the generated ``paas-charm>=2.0.dev1,<3`` dependency and generated
     ``charmlibs`` interface dependencies for OAuth, OpenFGA, and tracing,
     which replace the corresponding Charmhub-fetched libraries;
   * a Valkey relation instead of the obsolete Redis relation; and
   * the generated ``uv.lock`` file.

   For Flask, the lower-base ``flask-app`` workload container and
   ``flask-app-image`` resource become ``app`` and ``app-image``. For Django,
   ``django-app`` and ``django-app-image`` likewise become ``app`` and
   ``app-image``. The resource-name change is separate from the workload
   container rename. Keep the generated declarations and update
   ``juju deploy --resource``, ``juju refresh --resource``, CI/CD, Terraform,
   scripts, bundles, overlays, and other automation that refers to the old
   names. When refreshing an existing deployment, supply the image using
   ``--resource app-image=<image>`` if Juju requires the renamed resource.

   Charmcraft generates the charm part as ``parts.charm`` on both contracts,
   so the Rockcraft ``/``-to-``.`` extension-part separator change does not
   apply to that generated charm part. Keep the new profile's ``parts.charm``
   definition instead of copying a lower-base override unchanged.

   Add the existing charm's application-specific Python dependencies to the
   generated ``pyproject.toml``. Retain the generated ``uv.lock`` unchanged
   when dependencies are unchanged. After any dependency change, regenerate
   and commit the lock file from ``charm-26-04``:

   .. code-block:: bash

      uv lock

   When carrying over custom relation handling or application code, replace
   obsolete Redis integration with the generated ``valkey`` relation and
   ``/valkey/*`` endpoints.

   For more details about the generated contract and dependency migration, see
   the :ref:`Charmcraft framework extension reference <charmcraft:extensions>`
   and :ref:`Migrate your 12-factor charm to use the uv plugin <uv_migration>`.

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

6. **Build and refresh all artifacts.** Ubuntu 26.04 LTS framework support
   currently requires the tooling enablement variables when packing:

   .. code-block:: bash

      ROCKCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS=1 rockcraft pack
      CHARMCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS=1 charmcraft pack
      juju refresh myapp --path ./myapp_amd64.charm \
        --resource app-image=<registry>/<rock name>:<version>

After the refresh completes, verify the application with ``juju status`` and
confirm that the workload is active and the ingress and observability relations
are healthy.
