.. Copyright 2025 Canonical Ltd.
.. See LICENSE file for licensing details.
.. _explanation_charm_architecture:

Charm architecture
==================

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

Web app support in Charmcraft and Rockcraft is a framework to easily deploy and
operate your web app workloads and associated infrastructure, such
as databases and ingress, using open source tooling. 

The charm design leverages the
`sidecar <https://kubernetes.io/blog/2015/06/the-distributed-system-toolkit-patterns/#example-1-sidecar-containers>`_
pattern to allow multiple containers in each pod with `Pebble <https://juju.is/docs/sdk/pebble>`_
running as the containers' entrypoint.
Pebble is a lightweight, API-driven process supervisor that is responsible for
configuring processes to run in a container and controlling those processes
throughout the workload lifecycle.

The charm consists of an ``app`` container which contains the workload
to run in any of the supported web frameworks.
As a result, if you run a :code:`kubectl get pods` on a namespace named for the Juju model
you've deployed the web app charm into, you'll see something like the following:

.. code-block:: text

   NAME                          READY   STATUS    RESTARTS   AGE
   web-app-0                     2/2     Running   0          6h4m

This shows there are two containers - the named above, as well as a container for the charm code itself.
The charm container logic is determined by the ``paas-charm`` library.

And if you run :code:`kubectl describe pod web-app-0`, all the containers will have
the command :code:`/charm/bin/pebble`. That's because Pebble is responsible for the
processes startup.

OCI images
----------

We use `Rockcraft <https://canonical-rockcraft.readthedocs-hosted.com/en/latest/>`_ to build OCI Images for the web app charm. 

.. seealso::

   `How to publish your charm on Charmhub <https://juju.is/docs/sdk/publishing>`_
   
   `Build a 12-factor app rock <https://documentation.ubuntu.com/rockcraft/en/latest/how-to/build-a-12-factor-app-rock/>`_

Juju events
-----------

Juju handles updates or changes to the charm and system through hooks, or events.
These notifications provides the charm information that the system has changed
and thus prompts a reaction from the charm to respond to the change, taking
into account the charm's configuration.

For more information on the events observed by 12-factor app charms, see
:ref:`ref_juju_events`.

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
