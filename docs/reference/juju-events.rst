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
  * - `\<container name\>_pebble_ready <https://documentation.ubuntu.com/juju/3.6/reference/hook/index.html#container-pebble-ready>`_
    - Fired on Kubernetes charms when the requested container is ready.
    - Validate the charm configuration, run pending migrations and restart the workload.
  * - `config_changed <https://documentation.ubuntu.com/juju/3.6/reference/hook/index.html#config-changed>`_
    - Usually fired in response to a configuration change using the CLI.
    - Validate the charm configuration, run pending migrations and restart the workload.
  * - `secret_storage_relation_created <https://documentation.ubuntu.com/juju/3.6/reference/hook/index.html#endpoint-relation-created>`_
    - Fired when the relation is first created.
    - Generate a new secret and store it in the relation data.
  * - `secret_storage_relation_changed <https://documentation.ubuntu.com/juju/3.6/reference/hook/index.html#endpoint-relation-changed>`_
    - Fired when a new unit joins in an existing relation and whenever the related unit changes its settings.
    - Validate the charm configuration, run pending migrations and restart the workload.
  * - `secret_storage_relation_departed <https://documentation.ubuntu.com/juju/3.6/reference/hook/index.html#endpoint-relation-departed>`_
    - Fired when a unit departs from an existing relation.
    - Validate the charm configuration, run pending migrations and restart the workload.
  * - `update_status <https://documentation.ubuntu.com/juju/3.6/reference/hook/index.html#update-status>`_
    - Fired at regular intervals.
    - Validate the configuration, run pending migrations and restart the workload.
  * - `secret_changed <https://documentation.ubuntu.com/juju/3.6/reference/hook/index.html#secret-changed>`_
    - Fired when the secret owner publishes a new secret revision.
    - Validate the configuration, run pending migrations and restart the workload.
  * - `database_created <https://github.com/canonical/data-platform-libs>`_
    - Fired when a new database is created.
    - Validate the configuration, run pending migrations and restart the workload.
  * - `endpoints_changed <https://github.com/canonical/data-platform-libs>`_
    - Fired when the database endpoints change.
    - Validate the configuration, run pending migrations and restart the workload.
  * - `database_relation_broken <https://github.com/canonical/data-platform-libs>`_
    - Fired when a unit participating in a non-peer relation is removed.
    - Validate the configuration, run pending migrations and restart the workload.
  * - `ingress_ready <https://github.com/canonical/traefik-k8s-operator>`_
    - Fired when the ingress for the web app is ready.
    - Validate the configuration, run pending migrations and restart the workload.
  * - `ingress_revoked <https://github.com/canonical/traefik-k8s-operator>`_
    - Fired when the ingress for the web app is not ready anymore.
    - Validate the configuration, run pending migrations and restart the workload.
  * - `redis_relation_updated <https://github.com/canonical/redis-k8s-operator>`_
    - Fired when a new unit joins in an existing relation and whenever the related unit changes its settings.
    - Validate the configuration, run pending migrations and restart the workload.
  * - `s3_credentials_changed <https://github.com/canonical/data-platform-libs>`_
    - Fired when the S3 credentials are changed.
    - Validate the configuration, run pending migrations and restart the workload.
  * - `s3_credentials_gone <https://github.com/canonical/data-platform-libs>`_
    - Fired when the S3 credentials are removed.
    - Validate the configuration, run pending migrations and restart the workload.
  * - `saml_data_available <https://github.com/canonical/saml-integrator-operator>`_
    - Fired when new SAML data is present in the relation.
    - Validate the configuration, run pending migrations and restart the workload.
  * - `rabbitmq_ready <https://github.com/openstack-charmers/charm-rabbitmq-k8s>`_
    - Fired after a ``rabbitmq_cjoined`` event.
    - Validate the configuration, run pending migrations and restart the workload.
  * - `rabbitmq_connected <https://github.com/openstack-charmers/charm-rabbitmq-k8s>`_
    - Fired after a ``rabbitmq_changed`` or ``rabbitmq_broken`` event.
    - Validate the configuration, run pending migrations and restart the workload.
  * - `rabbitmq_joined <https://documentation.ubuntu.com/juju/3.6/reference/hook/index.html#endpoint-relation-joined>`_
    - Fired when a new unit joins in an existing relation.
    - Request access to the RabbitMQ server and emit a connected event.
  * - `rabbitmq_changed <https://documentation.ubuntu.com/juju/3.6/reference/hook/index.html#endpoint-relation-changed>`_
    - Fired when a new unit joins in an existing relation and whenever the related unit changes its settings.
    - Request access to the RabbitMQ server and emit a ready event.
  * - `rabbitmq_broken <https://documentation.ubuntu.com/juju/3.6/reference/hook/index.html#endpoint-relation-broken>`_
    - Fired when a unit participating in a non-peer relation is removed. 
    - Emit a ready event.
  * - `rabbitmq_departed <https://documentation.ubuntu.com/juju/3.6/reference/hook/index.html#endpoint-relation-departed>`_
    - Fired when a related unit is no longer related.
    - Validate the charm configuration, run pending migrations and restart the workload.
  * - `tracing_endpoint_changed <https://github.com/canonical/tempo-coordinator-k8s-operator>`_
    - Fired when one of the receiver endpoints changes.
    - Validate the charm configuration, run pending migrations and restart the workload.
  * - `tracing_endpoint_removed <https://github.com/canonical/tempo-coordinator-k8s-operator>`_
    - Fired when one of the receiver endpoints is removed.
    - Validate the charm configuration, run pending migrations and restart the workload.
  * - `smtp_data_available <https://github.com/canonical/smtp-integrator-operator>`_
    - Fired when new SMTP data is present in the relation.
    - Validate the charm configuration, run pending migrations and restart the workload.
  * - `rotate_secret_key <https://documentation.ubuntu.com/juju/3.6/user/reference/action/>`_
    - Fired when ``secret-rotate`` is executed.
    - Generate a new secret token for the application.

.. seealso::

    `Hook | Juju documentation <https://documentation.ubuntu.com/juju/3.6/reference/hook/>`_
