.. meta::
   :description: Technical details about how 12-factor app charms handle secrets.

.. _ref_secrets:

Secrets
=======

12-factor app charms use Juju secrets for application secret material. The
secret key used to sign sessions is generated and stored automatically, while
user-provided secrets can be passed as environment variables through config
options of type ``secret``.

Application secret key
-----------------------

Each 12-factor app charm maintains an application secret key used for session
signing, CSRF protection, or any other purpose that requires a random secret
shared by all units. The charm stores this key in a Juju application-owned
secret with the ``app-secret-key`` label instead of the peer relation databag.

The key is exposed to the workload through ``FLASK_SECRET_KEY`` for Flask,
``DJANGO_SECRET_KEY`` for Django, and ``APP_SECRET_KEY`` for FastAPI,
ExpressJS, Go, and Spring Boot. If no user-provided key is configured, a random
key is generated.

Because the key is stored in a Juju secret, it can be rotated without repacking
the charm. Identify the current leader with ``juju status`` and run the
``rotate-secret-key`` action on that unit to generate and store a new fallback
key:

.. code-block:: bash

   juju run <current leader unit> rotate-secret-key

This action rotates only the charm-managed key used when ``app-secret-key`` is
not configured. If ``app-secret-key`` refers to a Juju user secret, update or
rotate that user secret instead.

.. warning::

    Rotating the key, or upgrading from ``paas-charm`` 1.x to 2.0, invalidates
    any existing sessions signed with the previous key. On upgrade a fresh key
    is always generated because previous values are not migrated from the peer
    relation databag. Applications that use the key for session signing
    (including Flask, Django, FastAPI, ExpressJS, and Spring Boot) may sign out
    existing users.

User-provided secret key
------------------------

To use your own secret key instead of the generated one, configure the
``app-secret-key`` option of type ``secret`` in ``charmcraft.yaml`` and set it
to a Juju user secret ID:

.. code-block:: yaml
   :caption: charmcraft.yaml

   config:
     options:
       app-secret-key:
         type: secret
         description: Secret key used for session signing.

.. code-block:: bash

   juju add-secret my-app-secret-key value=<secret-string>
   juju grant-secret my-app-secret-key <app name>
   juju config <app name> app-secret-key=secret:<secret id>

The secret must contain a single key, ``value``, which holds the actual secret
key.

User secrets as environment variables
-------------------------------------

You can expose arbitrary Juju secret keys and values as environment variables by
adding a configuration option of type ``secret``. Each key inside the secret becomes an
environment variable named after the option and the secret key:

.. code-block:: yaml
   :caption: charmcraft.yaml

   config:
     options:
       api-token:
         type: secret
         description: Secret needed to access an API.

.. code-block:: bash

   juju add-secret my-api-token value=1234 othervalue=5678
   juju grant-secret my-api-token <app name>
   juju config <app name> api-token=secret:<secret id>

For a configuration option ``api-token`` and a secret key ``value``, Flask receives
``FLASK_API_TOKEN_VALUE``, Django receives ``DJANGO_API_TOKEN_VALUE``, and
FastAPI, ExpressJS, Go, and Spring Boot receive ``APP_API_TOKEN_VALUE``. In
general, the environment variable uses the framework prefix followed by the
option and key names, with hyphens replaced by underscores and all letters
in uppercase.

.. seealso::

    * :ref:`Manage secrets <charmcraft:configure-12-factor-charms-manage-secrets>`
    * :doc:`Juju events <juju-events>`
    * :external+juju:ref:`Juju | Secret <secret>`
