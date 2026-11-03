.. _ref_juju_events:

Juju events
===========

For a web app charm, the following events are observed:

.. list-table::
  :header-rows: 1
  :widths: 1 1 1

  * - Hook
    - Description
    - Action
  * - :ref:`\<container name\>_pebble_ready <juju:hook-container-pebble-ready>`
    - Fired on Kubernetes charms when the requested container is ready.
    - Validate the charm configuration, run pending migrations and restart the workload.
  * - ``config_changed``
    - Usually fired in response to a configuration change using the CLI.
    - Validate the charm configuration, run pending migrations and restart the workload.
  * - ``leader_elected``
    - Fired when a new leader unit is elected.
    - Validate the charm configuration and relations, initialize the application secret key if
      needed, and restart the workload without explicitly re-running migrations.
  * - ``peers_relation_created``
    - Fired when the peer relation is first created.
    - Validate the charm configuration, run pending migrations and restart the workload.
  * - ``peers_relation_changed``
    - Fired when a new unit joins in an existing relation and whenever the related unit changes its settings.
    - Validate the charm configuration, run pending migrations and restart the workload.
  * - ``peers_relation_departed``
    - Fired when a unit departs from an existing relation.
    - Validate the charm configuration, run pending migrations and restart the workload.
  * - ``update_status``
    - Fired at regular intervals.
    - Restart the workload if the last database migration failed, and refresh the ingress
      relation data.
  * - ``secret_changed``
    - Fired when the secret owner publishes a new secret revision.
    - Validate the configuration, run pending migrations and restart the workload.
  * - ``database_created``
    - Fired when a new database is created.
    - Validate the configuration, re-run migrations and restart the workload.
  * - ``endpoints_changed``
    - Fired when the database endpoints change.
    - Validate the configuration, re-run migrations and restart the workload.
  * - ``<database relation name>_relation_broken``
    - Fired when a database relation is removed.
    - Validate the configuration, run pending migrations and restart the workload.
  * - ``ingress_ready``
    - Fired when the ingress for the web app is ready.
    - Validate the configuration, run pending migrations and restart the workload.
  * - ``ingress_revoked``
    - Fired when the ingress for the web app is not ready anymore.
    - Validate the configuration, run pending migrations and restart the workload.
  * - ``valkey_resource_created``
    - Fired when the Valkey relation data is available.
    - Validate the configuration, re-run migrations and restart the workload.
  * - `s3_credentials_changed <https://github.com/canonical/data-platform-libs>`_
    - Fired when the S3 credentials are changed.
    - Validate the configuration, re-run migrations and restart the workload.
  * - `s3_credentials_gone <https://github.com/canonical/data-platform-libs>`_
    - Fired when the S3 credentials are removed.
    - Validate the configuration, run pending migrations and restart the workload.
  * - ``saml_data_available``
    - Fired when new SAML data is present in the relation.
    - Validate the configuration, re-run migrations and restart the workload.
  * - ``rabbitmq_ready``
    - Emitted by the RabbitMQ requirer on relation changed or departed, when relation data is available.
    - Validate the configuration, re-run migrations and restart the workload.
  * - ``rabbitmq_connected``
    - Emitted by the RabbitMQ requirer when the relation is joined.
    - Validate the configuration, re-run migrations and restart the workload.
  * - ``rabbitmq_joined``
    - Fired when a new unit joins in an existing relation.
    - Emit a connected event and request access to the RabbitMQ server.
  * - ``rabbitmq_changed``
    - Fired when a new unit joins in an existing relation and whenever the related unit changes its settings.
    - Emit a ready event if the RabbitMQ relation data is available.
  * - ``rabbitmq_broken``
    - Fired when the RabbitMQ relation is removed.
    - Emit a departed event.
  * - ``rabbitmq_departed``
    - Emitted by the RabbitMQ requirer when the relation is broken.
    - Validate the charm configuration, run pending migrations and restart the workload.
  * - ``tracing_endpoint_changed``
    - Fired when one of the receiver endpoints changes.
    - Validate the charm configuration, run pending migrations and restart the workload.
  * - ``tracing_endpoint_removed``
    - Fired when one of the receiver endpoints is removed.
    - Validate the charm configuration, run pending migrations and restart the workload.
  * - ``smtp_data_available``
    - Fired when new SMTP data is present in the relation.
    - Validate the charm configuration, run pending migrations and restart the workload.
  * - ``oauth_info_changed``
    - Fired when the OAuth provider information changes.
    - Validate the configuration, run pending migrations and restart the workload.
  * - ``oauth_info_removed``
    - Fired when the OAuth provider information is removed.
    - Validate the configuration, run pending migrations and restart the workload.
  * - ``http_proxy_relation_changed``
    - Fired when a new unit joins in an existing relation and whenever the related unit changes its settings.
    - Validate the configuration, run pending migrations and restart the workload.
  * - ``openfga_store_created``
    - Fired when the OpenFGA store is created.
    - Validate the configuration, run pending migrations and restart the workload.
  * - ``create_superuser_action``
    - Fired when the ``create-superuser`` action is run. Django charms only.
    - Create a Django superuser in the workload container. The workload isn't restarted.
  * - ``rotate_secret_key_action``
    - Fired when the ``rotate-secret-key`` action is run. The action fails on non-leader units.
    - Generate a new secret token for the application and restart the workload. The action
      also fails if the charm is still initializing.

.. seealso::

    :ref:`Hook | Juju documentation <juju:hook>`
