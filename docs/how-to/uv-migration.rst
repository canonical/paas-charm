.. meta::
   :description: Learn how to migrate a 12-factor app charm from the charm plugin to the uv plugin.

.. _uv_migration:

Migrate your 12-factor charm to use the uv plugin
=================================================

In ``paas-charm`` 2.0 and charms using the Ubuntu 26.04 LTS base, the
`uv <https://canonical.com/juju/docs/charmcraft/4/reference/plugins/uv_plugin/#craft-parts-uv-plugin>`_
plugin is the default. Charms using ``paas-charm`` 1.x use the ``charm`` plugin
by default, and converting such a charm is considered a breaking change.
This guide walks you
through manually converting a 12-factor charm that uses
the legacy ``charm`` plugin to the modern
``uv`` plugin backed by uv.

.. important::

    On Ubuntu 26.04 LTS, the framework extension adds the ``charm`` part (using the ``uv``
    plugin and the ``charmlibs-pydeps`` dependency group) automatically. It also adds a
    ``config`` part when a ``paas-config.yaml`` file exists. On Ubuntu 24.04 LTS, the
    extension still uses the legacy ``charm`` plugin and adds no ``config`` part. Charmcraft rejects a
    ``charmcraft.yaml`` file that defines ``parts.charm`` together with a framework
    extension on any base ("incompatible with customized charm part"). For charms that use
    the extension, only the ``pyproject.toml`` and ``uv.lock`` steps apply, and you must
    not add the ``parts`` blocks below. The ``parts`` sections apply only to charms that
    don't use the framework extension.

.. admonition:: Why migrate?

    The ``uv`` plugin provides fast, reproducible Python dependency
    resolution via a lock file (``uv.lock``), replaces the loose
    ``requirements.txt`` approach with a proper ``pyproject.toml``,
    and removes the need for the ``charm-strict-dependencies`` workaround.

Replace ``requirements.txt`` with ``pyproject.toml``
----------------------------------------------------

Delete ``requirements.txt`` from your charm directory and create a
``pyproject.toml`` in its place, declaring your charm’s Python
dependencies with pinned versions.

For example, if your ``requirements.txt`` looks like:

.. code-block:: text
   :caption: requirements.txt

   cosl
   dpcharmlibs-interfaces==1.0.2
   jsonschema >=4.19,<4.20
   ops >= 2.6
   pydantic==2.13.3
   paas-charm==1.11.3

Then replace the file with its equivalent ``pyproject.toml``:

.. code-block:: toml
   :caption: pyproject.toml

   [project]
   name = "my-charm-k8s"          # use your charm's name
   version = "0.1.0"
   description = "Add your description here"
   readme = "README.md"
   requires-python = ">=3.10"
   dependencies = [
       "cosl==1.9.1",
       "dpcharmlibs-interfaces==1.0.2",
       "jinja2==3.1.6",
       "jsonschema==4.26",
       "ops==3.8.0",
       "pydantic==2.13.3",
       "paas-charm==1.11.3",
   ]

   [dependency-groups]
   charmlibs-pydeps = []

.. note::

    Keep the empty ``charmlibs-pydeps`` dependency group. The build fails without it.

    The pins above are for a ``paas-charm`` 1.x charm. ``paas-charm`` 2.0 requires
    Python 3.12 or greater and pins its own versions of ``ops``, ``pydantic``,
    ``jsonschema``, ``cosl`` and ``dpcharmlibs-interfaces``, so pinning older versions of
    these makes ``uv lock`` fail. For ``paas-charm`` 2.0, set ``requires-python = ">=3.12"``
    and list ``paas-charm>=2.0.dev1,<3`` with only the extra dependencies your own code needs.

.. tip::

    Pin every dependency to an exact version so that the generated
    ``uv.lock`` is fully reproducible across machines and CI environments.

Generate ``uv.lock``
--------------------

With ``pyproject.toml`` in place, run ``uv sync`` inside the charm
directory to resolve dependencies and generate the lock file:

.. code:: bash

   cd path/to/your/charm
   uv sync

This creates (or refreshes) ``uv.lock``.
The lock file must be present before you run ``charmcraft pack``.

Update ``charmcraft.yaml``
--------------------------

Change the plugin key
~~~~~~~~~~~~~~~~~~~~~

Replace the ``plugin: charm`` block with ``plugin: uv``.

The key differences are:
  - Add ``source: .``
  - Change ``plugin: charm`` → ``plugin: uv``
  - Remove ``charm-strict-dependencies: false``
  - Add ``astral-uv`` to ``build-snaps``

For example, if your ``charmcraft.yaml`` contains the following snippet:

.. code-block:: yaml
   :caption: charmcraft.yaml

   parts:
     charm:
       charm-strict-dependencies: false
       plugin: charm
       build-snaps:
       - rustup
       override-build: |-
         rustup default stable
         craftctl default

Then update your file to use:

.. code-block:: yaml
   :caption: charmcraft.yaml

   parts:
     charm:
       source: .
       plugin: uv
       build-snaps:
         - astral-uv
         - rustup
       override-build: |-
         rustup default stable
         craftctl default

(If applicable) Add a config part for ``paas-config.yaml``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This applies only to charms that don't use a framework extension. Extension
charms on Ubuntu 26.04 LTS don't need a ``config`` part: the extension stages
``paas-config.yaml`` automatically.

If your charm ships a ``paas-config.yaml`` file, you need a dedicated
``dump`` part to stage it into the packed charm. Without this part,
the file will not be included in your charm because the ``uv`` plugin
only stages Python artifacts.

.. code-block:: yaml

   parts:
     charm:
       source: .
       plugin: uv
       build-snaps:
         - astral-uv
         - rustup
       override-build: |-
         rustup default stable
         craftctl default
     config:
       plugin: dump
       source: .
       stage:
         - paas-config.yaml

Pack the charm
--------------

Always run ``uv sync`` before packing to ensure the lock file is
up-to-date, then pack as usual:

.. code:: bash

   cd path/to/your/charm
   uv sync
   charmcraft pack

Summary of file changes
-----------------------

==================== ====================================
File                 Action
==================== ====================================
``requirements.txt`` Delete
``pyproject.toml``   Create – declare pinned dependencies
``uv.lock``          Generate via ``uv sync`` and commit
``charmcraft.yaml``  Update ``parts.charm``
==================== ====================================

Complete ``parts`` example
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. tabs::

    .. group-tab:: without ``paas-config.yaml``

        .. code-block:: yaml

            parts:
              charm:
                source: .
                plugin: uv
                build-snaps:
                  - astral-uv
                  - rustup
                override-build: |-
                  rustup default stable
                  craftctl default

    .. group-tab:: with ``paas-config.yaml``

        .. code-block:: yaml

            parts:
              charm:
                source: .
                plugin: uv
                build-snaps:
                  - astral-uv
                  - rustup
                override-build: |-
                  rustup default stable
                  craftctl default
              config:
                plugin: dump
                source: .
                stage:
                  - paas-config.yaml
