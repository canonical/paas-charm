.. _uv_migration:

Migrate your 12-factor charm to use the uv plugin
=================================================

In the upcoming V2 release of the ``paas-charm`` library and charms
using the ``26.04`` base, the `uv <https://documentation.ubuntu.com/charmcraft/stable/reference/plugins/uv_plugin/#craft-parts-uv-plugin>`_ plugin will be the default.
V1 charms use the ``charm`` plugin by default, and
converting your V1 charm is considered a breaking change.
This guide walks you
through manually converting a V1 12-factor charm that uses
the legacy ``charm`` plugin to the modern
``uv`` plugin backed by uv.

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

.. code-block:: bash
   :caption: requirements.txt

   cosl
   dpcharmlibs-interfaces==1.0.2
   jsonschema >=4.19,&lt;4.20
   ops >= 2.6
   pydantic==2.13.3
   paas-charm==1.11.3

Then replace the file with its equivalent ``pyproject.toml``:

.. code-block:: bash
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

.. code-block:: bash
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

.. code-block:: bash
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

If your charm ships a ``paas-config.yaml`` file, you need a dedicated
``dump`` part to stage it into the packed charm. Without this part,
the file will not be included in your charm because the ``uv`` plugin
only stages Python artifacts.

.. code:: bash

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

        .. code-block:: bash

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

        .. code-block:: bash

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
