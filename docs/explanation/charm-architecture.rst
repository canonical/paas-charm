.. Copyright 2025 Canonical Ltd.
.. See LICENSE file for licensing details.
.. _charm-architecture:

Charm architecture
==================

PaaS charm is a framework to easily deploy and operate your Flask, Django, FastAPI or Go workloads and associated infrastructure, such
as databases and ingress, using open source tooling.

The resulting charm design leverages the `sidecar <https://kubernetes.io/blog/2015/06/the-distributed-system-toolkit-patterns/#example-1-sidecar-containers>`_ pattern to allow multiple containers in each pod with `Pebble <https://juju.is/docs/sdk/pebble>`_ running as the workload container’s entrypoint.

Charm architecture diagram
--------------------------

.. mermaid::

   C4Container
   System_Boundary(paas_charm, "PaaS Charm") {
      Container_Boundary(charm_container, "Charm Container") {
         Component(charm_logic, "Charm Logic", "Juju Operator Framework", "Controls application deployment & config")
      }
      Container_Boundary(paas_container, "Workload Container") {
         Component(workload, "Workload", "Web Application", "Observes events; serves web requests")
      }
   }
   Rel(charm_logic, workload, "Supervises<br>process")

Pebble is a lightweight, API-driven process supervisor that is responsible for configuring processes to run in a container and controlling those processes throughout the workload lifecycle.

Pebble `services` are configured through `layers <https://github.com/canonical/pebble#layer-specification>`_, and the following containers represent each one a layer forming the effective Pebble configuration, or `plan`:

1. An :code:`app` container, which contains the workload to run in any of the supported web frameworks.


As a result, if you run a :code:`kubectl get pods` on a namespace named for the Juju model you've deployed the PaaS charm into, you'll see something like the following:

.. code-block:: text

   NAME                          READY   STATUS    RESTARTS   AGE
   paas-0                        2/2     Running   0          6h4m

This shows there are 2 containers - the named above, as well as a container for the charm code itself.

And if you run :code:`kubectl describe pod paas-0`, all the containers will have as Command :code:`/charm/bin/pebble`. That's because Pebble is responsible for the processes startup as explained above.

OCI images
----------

We use `Rockcraft <https://canonical-rockcraft.readthedocs-hosted.com/en/latest/>`_ to build OCI Images for the PaaS charm. 

.. seealso::

   `How to publish your charm on Charmhub <https://juju.is/docs/sdk/publishing>`_
   
   `Build a 12-factor app rock <https://documentation.ubuntu.com/rockcraft/en/latest/how-to/build-a-12-factor-app-rock/>`_


Metrics
-------
Depending on the workload framework, PaaS provides support for metrics and tracing.

Integrations
------------

Juju events
------------

Charm code overview
--------------------
