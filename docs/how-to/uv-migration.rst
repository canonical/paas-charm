.. _uv_migration:

Migrating your 12-factor charm from the charm plugin to the uv plugin
=====================================================================

In the upcoming V2 release of the ``paas-charm`` library and charms
using the ``26.04`` base, the ``uv`` plugin will be the default.
Converting the V1 charms would be a breaking change so we decided to
make ``uv`` default only for the V2 charms. But since manual conversion
is straightforward we would like to share this guide that walks you
through manually converting a 12-factor / paas-charm charm that uses
the legacy ``charm`` plugin in converting a 12-factor / paas-charm charm
that uses the legacy charm plugin in ``charmcraft.yaml`` to the modern
uv plugin backed by uv.

Why migrate?
------------

The ``uv`` plugin provides fast, reproducible Python dependency
resolution via a lock file (``uv.lock``), replaces the loose
``requirements.txt`` approach with a proper ``pyproject.toml``,
and removes the need for the ``charm-strict-dependencies`` workaround.

Step 1 – Replace requirements.txt with pyproject.toml
-----------------------------------------------------

Delete ``requirements.txt`` from your charm directory and create a
``pyproject.toml`` in its place, declaring your charm’s Python
dependencies with pinned versions.

**Before (``requirements.txt``):**

.. code-block:: bash

   cosl
   dpcharmlibs-interfaces==1.0.2
   jsonschema >=4.19,&lt;4.20
   ops >= 2.6
   pydantic==2.13.3
   paas-charm==1.11.3

**After (``pyproject.toml``):**

.. code-block:: bash

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
       "ops==3.7.1",
       "pydantic==2.13.3",
       "paas-charm==1.11.3",
   ]

*Tip: Pin every dependency to an exact version so that the generated
uv.lock is fully reproducible across machines and CI environments.*

Step 2 – Generate uv.lock
-------------------------

With ``pyproject.toml`` in place, run ``uv sync`` inside the charm
directory to resolve dependencies and generate the lock file:

.. code:: bash

   cd path/to/your/charm
   uv sync

This creates (or refreshes) ``uv.lock``.
The lock file must be present before you run ``charmcraft pack``.

Step 3 – Update charmcraft.yaml
-------------------------------

3a. Change the plugin key
~~~~~~~~~~~~~~~~~~~~~~~~~

Replace the ``plugin: charm`` block with ``plugin: uv``.

The key differences are:
  - Add ``source: .``
  - Change ``plugin: charm`` → ``plugin: uv``
  - Remove ``charm-strict-dependencies: false``
  - Add ``astral-uv`` to ``build-snaps``

Before:

.. code:: bash

   parts:
     charm:
       charm-strict-dependencies: false
       plugin: charm
       build-snaps:
       - rustup
       override-build: |-
         rustup default stable
         craftctl default

After:

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

3b. (If applicable) Add a config part for paas-config.yaml
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If your charm ships a ``paas-config.yaml`` file, you need a dedicated
``dump`` part to stage it into the packed charm. Without this part,
the file will not be included in your charm, because the ``uv`` plugin
only stages Python artefacts.

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

Step 4 – Pack the charm
-----------------------

Always run ``uv sync`` before packing to ensure the lock file is
up-to-date, then pack as usual:

.. code:: bash

   cd path/to/your/charm
   uv sync
   charmcraft pack

Summary of file changes
-----------------------

================ ====================================
File             Action
================ ====================================
requirements.txt Delete
pyproject.toml   Create – declare pinned dependencies
uv.lock          Generate via uv sync and commit
charmcraft.yaml  Update parts.charm (see Step 3)
================ ====================================

Complete ``parts`` example (no ``paas-config.yaml``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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

Complete ``parts`` example (with ``paas-config.yaml``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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
