.. Copyright 2025 Canonical Ltd.
.. See LICENSE file for licensing details.
.. _charm-architecture:

Charm architecture
==================

Web app support in Charmcraft and Rockcraft is a framework to easily deploy and operate your Flask, Django, FastAPI or Go workloads and associated infrastructure, such
as databases and ingress, using open source tooling.

The resulting charm design leverages the `sidecar <https://kubernetes.io/blog/2015/06/the-distributed-system-toolkit-patterns/#example-1-sidecar-containers>`_ pattern to allow multiple containers in each pod with `Pebble <https://juju.is/docs/sdk/pebble>`_ running as the workload container’s entrypoint.

Pebble is a lightweight, API-driven process supervisor that is responsible for configuring processes to run in a container and controlling those processes throughout the workload lifecycle.

Pebble `services` are configured through `layers <https://github.com/canonical/pebble#layer-specification>`_, and the following containers represent each one a layer forming the effective Pebble configuration, or `plan`:

1. An :code:`app` container, which contains the workload to run in any of the supported web frameworks.


As a result, if you run a :code:`kubectl get pods` on a namespace named for the Juju model you've deployed the web app charm into, you'll see something like the following:

.. code-block:: text

   NAME                          READY   STATUS    RESTARTS   AGE
   web-app-0                     2/2     Running   0          6h4m

This shows there are 2 containers - the named above, as well as a container for the charm code itself.

And if you run :code:`kubectl describe pod web-app-0`, all the containers will have as Command :code:`/charm/bin/pebble`. That's because Pebble is responsible for the processes startup as explained above.

Charm architecture diagram
--------------------------

.. mermaid::

   C4Container
   System_Boundary(web_app_charm, "Web app charm") {
      Container_Boundary(charm_container, "Charm Container") {
         Component(charm_logic, "Charm Logic", "Juju Operator Framework", "Controls application deployment & config")
      }
      Container_Boundary(web_app_container, "Workload Container") {
         Component(workload, "Workload", "Web Application", "Serves web requests")
      }
   }
   Rel(charm_logic, workload, "Supervises<br>process")

OCI images
----------

We use `Rockcraft <https://canonical-rockcraft.readthedocs-hosted.com/en/latest/>`_ to build OCI Images for the web app charm. 

.. seealso::

   `How to publish your charm on Charmhub <https://juju.is/docs/sdk/publishing>`_
   
   `Build a 12-factor app rock <https://documentation.ubuntu.com/rockcraft/en/latest/how-to/build-a-12-factor-app-rock/>`_


Metrics
-------
The provided support for metrics and tracing depends on the enabled extension.

.. seealso:: 

   `Charmcraft reference | Extensions <https://canonical-charmcraft.readthedocs-hosted.com/en/stable/reference/extensions/>`_.

Integrations
------------
The available integrations, including those that are already pre-populated, varies between extensions.

.. seealso::

   `Charmcraft reference | Extensions <https://canonical-charmcraft.readthedocs-hosted.com/en/stable/reference/extensions/>`_.

Juju events
-----------

For a web app charm, the following events are observed:

1. `\<container name\>_pebble_ready <https://canonical-juju.readthedocs-hosted.com/en/3.6/user/reference/hook/#container-pebble-ready>`_: fired on Kubernetes charms when the requested container is ready. **Action**: validate the charm configuration, run pending migrations and restart the workload.

2. `config_changed <https://canonical-juju.readthedocs-hosted.com/en/latest/user/reference/hook/#config-changed>`_: usually fired in response to a configuration change using the CLI. **Action**: validate the charm configuration, run pending migrations and restart the workload.

3. `secret_storage_relation_created <https://canonical-juju.readthedocs-hosted.com/en/latest/user/reference/hook/#endpoint-relation-created>`_: fired when the relation is first created. **Action**: generate a new secret and store it in the relation data.

4. `secret_storage_relation_changed <https://canonical-juju.readthedocs-hosted.com/en/latest/user/reference/hook/#endpoint-relation-changed>`_: fired when a new unit joins in an existing relation and whenever the related unit changes its settings. **Action**: validate the charm configuration, run pending migrations and restart the workload.

5. `secret_storage_relation_departed <https://canonical-juju.readthedocs-hosted.com/en/latest/user/reference/hook/#endpoint-relation-departed>`_: fired when a unit departs from an existing relation. **Action**: validate the charm configuration, run pending migrations and restart the workload.

6. `update_status <https://canonical-juju.readthedocs-hosted.com/en/latest/user/reference/hook/#update-status>`_: fired at regular intervals. **Action**: validate the configuration, run pending migrations and restart the workload.

7. `secret_changed <https://canonical-juju.readthedocs-hosted.com/en/latest/user/reference/hook/#secret-changed>`_: fired when the secret owner publishes a new secret revision. **Action**: validate the configuration, run pending migrations and restart the workload.

8. `database_created <https://github.com/canonical/data-platform-libs>`_: fired when a new database is created. **Action**: validate the charm configuration, run pending migrations and restart the workload.

9. `endpoints_changed <https://github.com/canonical/data-platform-libs>`_: fired when the database endpoints change. **Action**: validate the charm configuration, run pending migrations and restart the workload.

10. `database_relation_broken <https://github.com/canonical/data-platform-libs>`_: fired when a unit participating in a non-peer relation is removed. **Action**: validate the charm configuration, run pending migrations and restart the workload.

11. `ingress_ready <https://github.com/canonical/traefik-k8s-operator>`_: fired when the ingress for the web app is ready. **Action**: validate the charm configuration, run pending migrations and restart the workload.

12. `ingress_revoked <https://github.com/canonical/traefik-k8s-operator>`_: fired when the ingress for the web app is not ready anymore. **Action**: validate the charm configuration, run pending migrations and restart the workload.

13. `redis_relation_updated <https://github.com/canonical/redis-k8s-operator>`_:  fired when a new unit joins in an existing relation and whenever the related unit changes its settings. **Action**: validate the charm configuration, run pending migrations and restart the workload.

14. `s3_credentials_changed <https://github.com/canonical/data-platform-libs>`_: fired when the S3 credentials are changed. **Action**: validate the charm configuration, run pending migrations and restart the workload.

15. `s3_credentials_gone <https://github.com/canonical/data-platform-libs>`_: fired when the S3 credentials are removed. **Action**: validate the charm configuration, run pending migrations and restart the workload.

16. `saml_data_available <https://github.com/canonical/saml-integrator-operator>`_: fired when new SAML data is present in the relation. **Action**: validate the charm configuration, run pending migrations and restart the workload.

17. `rabbitmq_ready <https://github.com/openstack-charmers/charm-rabbitmq-k8s>`_: fired after a ``rabbitmq_cjoined`` event. **Action**: validate the charm configuration, run pending migrations and restart the workload.

18. `rabbitmq_connected <https://github.com/openstack-charmers/charm-rabbitmq-k8s>`_: fired after a ``rabbitmq_changed`` or ``rabbitmq_broken`` event. **Action**: validate the charm configuration, run pending migrations and restart the workload.

19. `rabbitmq_joined <https://canonical-juju.readthedocs-hosted.com/en/latest/user/reference/hook/#endpoint-relation-joined>`_: fired when a new unit joins in an existing relation. **Action**: request access to the RabbitMQ server and emit a connected event.

20. `rabbitmq_changed <https://canonical-juju.readthedocs-hosted.com/en/latest/user/reference/hook/#endpoint-relation-changed>`_: fired when a new unit joins in an existing relation and whenever the related unit changes its settings. **Action**: request access to the RabbitMQ server and emit a ready event.

21. `rabbitmq_broken <https://canonical-juju.readthedocs-hosted.com/en/latest/user/reference/hook/#endpoint-relation-broken>`_: fired when a unit participating in a non-peer relation is removed. **Action**: emit a ready event.

22. `rabbitmq_departed <https://canonical-juju.readthedocs-hosted.com/en/latest/user/reference/hook/#endpoint-relation-departed>`_: fired when a related unit is no longer related. **Action**: validate the charm configuration, run pending migrations and restart the workload.

23. `tracing_endpoint_changed <https://github.com/canonical/tempo-coordinator-k8s-operator>`_: fired when one of the receiver endpoints changes. **Action**: validate the charm configuration, run pending migrations and restart the workload.

24. `tracing_endpoint_removed <https://github.com/canonical/tempo-coordinator-k8s-operator>`_: fired when one of the receiver endpoints is removed. **Action**: validate the charm configuration, run pending migrations and restart the workload.

25. `smtp_data_available <https://github.com/canonical/smtp-integrator-operator>`_: fired when new SMTP data is present in the relation. **Action**: validate the charm configuration, run pending migrations and restart the workload.

26. `rotate_secret_key <https://documentation.ubuntu.com/juju/latest/user/reference/action/>`_: fired when secret-rotate is executed.  **Action**: generate a new secret token for the application.

Charm code overview
-------------------

The :code:`src/paas_charm/charm.py` contains the charm logic that all supported frameworks will inherit and extend.
Each framework will define its entry point in its own :code:`charm.py` file, defining a class that will extend from :code:`PaasCharm`.

PaasCharm is the base class from which all Charms are formed, defined by `Ops  <https://juju.is/docs/sdk/ops>`_ (Python framework for developing charms).

.. seealso::

   `Charm <https://canonical-juju.readthedocs-hosted.com/en/3.6/user/reference/charm/>`_

The :code:`__init__` method guarantees that the charm observes all events relevant to its operation and handles them.

Take, for example, when a configuration is changed by using the CLI.

1. User runs the command

   .. code-block:: bash

      juju config sample_config=sample_value

2. A :code:`config-changed` event is emitted.
3. In the :code:`__init__` method is defined how to handle this event like this:

   .. code-block:: python

      self.framework.observe(self.on.config_changed, self._on_config_changed)
      
4. The method :code:`_on_config_changed`, for its turn,  will take the necessary actions such as waiting for all the relations to be ready and then configuring the container.
