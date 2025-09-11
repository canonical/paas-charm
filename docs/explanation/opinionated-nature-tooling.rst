.. _explanation_opinionated_nature:

Opinionated nature of the 12-factor tooling
===========================================

The native 12-factor framework support in Rockcraft and Charmcraft provides
a streamlined approach to setting up a rock and charm for a web app, but this
support contains strong and weak opinions about the project structure, the
Ubuntu base, framework versions, and configurations. This document describes
the various ways in which the 12-factor tooling is opinionated.

.. note::

    There are several components of 12-factor app rocks and charms that can
    be configured or customized by the user. See :ref:`ref_supported_customization`
    for a complete list.

Project structure
-----------------

For Rockcraft to successfully initialize the rock for a web app, it inspects the
directory where ``rockcraft init`` is run to search for specific files and global
variables depending upon the selected framework. The following sub-sections
detail the requirements for each of the supported frameworks.

Django
~~~~~~

The project must be set up with the structure
``project-name/project_name/project_name``, where ``project-name`` specifies the name
of the Django project. The rock must be initialized in the ``project-name`` directory.

There must be a ``project-name/requirements.txt`` file where Django is declared as
a dependency. There must also be a ``project-name/project_name/project_name/wsgi.py`` file
in the project.

When ``rockcraft init`` is run, Rockcraft searches for these two files
and expects to find a global variable named ``application`` in the ``wsgi.py`` file. 

The initialization will fail if Rockcraft does not find the ``requirements.txt`` file,
the ``wsgi.py`` file, or the global variable ``application``.

Express
~~~~~~~

The Express app must reside in a dedicated ``app`` directory containing a ``package.json`` file.
The ``package.json`` file must contain a ``scripts`` key, and this key must contain a ``start``
script which defines how the server is run. Furthermore, the ``name`` key in the file must be
defined and set to the app name.

The rock must be initialized outside of the ``app`` directory.
When ``rockcraft init`` is run, Rockcraft searches for the ``app/package.json`` file
and expects to find both the ``scripts: start`` and ``name`` keys. 

The initialization will fail if Rockcraft does not find the file and both keys.

FastAPI
~~~~~~~

The FastAPI project must contain a ``requirements.txt`` file where ``fastapi`` is
listed as a dependency. 
The rock must be initialized in the same directory as the ``requirements.txt`` file.

There must also be an ASGI app in the FastAPI project with the global variable ``app``.
Rockcraft will search for different names and locations for this file:

.. list-table::
  :header-rows: 1
  :widths: 5 10

  * - Possible project file name
    - Possible project file locations
  * - ``app.py``
    - Same directory as ``requirements.txt`` file, ``/app``, or ``/src``
  * - ``main.py``
    - Same directory as ``requirements.txt`` file, ``/app``, or ``/src``
  * - ``__init__.py``
    - ``/app`` or ``/src`` directories


When ``rockcraft init`` is run, Rockcraft searches for the project file in the root
directory, in the ``app`` directory, or in the ``src`` directory. Rockcraft expects
to find the global variable ``app`` defined in the project file.

The initialization will fail if Rockcraft does not find a project file or the global
variable ``app``.

Flask
~~~~~

The Flask project must contain a ``requirements.txt`` file where Flask is
listed as a dependency. In the same directory, there must also be an WSGI app
declared in an ``app.py`` file with the path ``app:app``. The name of the
Flask object must be set to ``app``.

The rock must be initialized in the same directory as the ``requirements.txt``
and ``app.py`` files.

When ``rockcraft init`` is run, Rockcraft searches for these files in the root
directory. Rockcraft expects to find the ``app:app`` path in ``app.py`` and to
find the name of the Flask object to be ``app``.

The initialization will fail if Rockcraft does not find both files, if the ``app:app``
path is missing, or if the name of the Flask object is not ``app``.

Go
~~

The Go project must contain a ``go.mod`` file. The rock must be initialized in the
same directory as this file.

When ``rockcraft init`` is run, Rockcraft searches for this file. The initialization will
fail if Rockcraft does not find the file.

When ``rockcraft pack`` is run, Rockcraft builds a binary with the same name as the Go project. 
You can override the binary name by updating the ``services`` parameter of the app's
``rockcraft.yaml`` file to pass a different name.

Spring Boot
~~~~~~~~~~~

The Spring Boot project must contain either a ``pom.xml`` or ``build.gradle`` file.
The rock must be initialized in the same directory as this file. The project must not
contain both files, otherwise the rock initialization will fail.

If you define the Spring Boot project using a ``pom.xml`` file, Rockcraft will install
the Maven plugin and check whether an ``mvnw`` executable file exists in the same directory.
If the executable file doesn't exist, Rockcraft will create the file. 

If you use a ``build.gradle`` file, Rockcraft will install the Gradle plugin and check
whether an ``gradlew`` executable file exists in the same directory. If the executable
file doesn't exist, Rockcraft will create the file.

The ``mvnw`` or ``gradlew`` file must be executable, or the rock initialization will fail.
The project must not contain both executable files, otherwise the rock initialization
will fail.

When ``rockcraft init`` is run, Rockcraft searches for either of these files and their
corresponding executable files.
The initialization will fail if Rockcraft does not find either file and its corresponding
executable file, or if it finds both files or both executable files.

Minimum supported versions of the frameworks
--------------------------------------------

Not all versions of the web app frameworks are supported. Check with us on the
`Matrix channel <https://matrix.to/#/#12-factor-charms:ubuntu.com>`_ if you have
questions about supported web app framework versions for the 12-factor tooling.

Opinions related to the base
----------------------------

Depending on the Ubuntu base specified in the ``rockcraft.yaml`` file, opinions are imposed
about the Python version used:

* Specifying ``base: ubuntu@22.04`` (or ``base: bare`` and ``build-base: ubuntu@22.04``) will use Python 3.10 
* Specifying ``base: ubuntu@24.04`` (or ``base: bare`` and ``build-base: ubuntu@24.04``) will use Python 3.12 

For the Spring Boot framework, the base determines the default JDK version. This is a weak
opinion that can be overriden by specifying the preferred version in the ``rockcraft.yaml``
file under ``extensions > spring-boot-framework/install-app: > build-packages``.

The JDK version has forward-compatibility but not backward-compatibility. For instance,
a Spring Boot app using Java 8 will also work with Java 11, but not vice versa.

Opinions related to the charm
-----------------------------

The charm for a 12-factor app can be initialized anywhere. We recommend that you create a
dedicated ``charm`` directory in the project to hold the charm code, but the charm
initialization and packing will not fail based on the location.

You must specify the appropriate rock when deploying the charm.

Configurations
~~~~~~~~~~~~~~

It is a strong opinion of the tooling in Charmcraft that the web app framework will read
configurations from environment variables. Any configuration (either out of the box or
user-defined) will correspond to an environment variable generated by ``paas-charm`` that
exposes the configuration to the web app workload.

.. seealso::

    `How to add a configuration to a 12-factor app charm <https://documentation.ubuntu.com/charmcraft/latest/howto/manage-web-app-charms/configure-web-app-charm/#add-a-new-configuration>`_

Relations
~~~~~~~~~

Adding custom relations is currently not supported by the tooling in Charmcraft.

Available charm features
~~~~~~~~~~~~~~~~~~~~~~~~

Some features of the charm are forbidden to add or modify, meaning that ``charmcraft pack``
will fail if those features were changed. 

For instance, while Juju supports storage management
(see `How to manage storage <https://documentation.ubuntu.com/juju/3.6/howto/manage-storage/>`_),
the 12-factor tooling does not offer this support. If your app requires additional
storage or volumes, you will not be able to use the 12-factor support in Charmcraft.

12-factor app charms are "stateless" by design and have no persistent storage. Their Juju units
are ephermeral, meaning that the container files are not persistent in case of the unit's
restart or deletion.

