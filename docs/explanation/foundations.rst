.. _explanation_foundations:

The foundations: Juju, charms and rocks
=======================================

The 12-factor web application solution uses and combines capabilities from the
following Canonical products:

- `Juju <https://juju.is>`_ is an open source orchestration engine for software
  operators that enables the deployment, integration and lifecycle management
  of applications at any scale and on any infrastructure.
- A :ref:`charm <juju:charm>` is an operator -
  business logic encapsulated in reusable software packages that automate every
  aspect of an application's life.
- :doc:`Charmcraft <charmcraft:index>`
  is a CLI tool that makes it easy and quick to initialize, package, and publish
  charms.
- :doc:`Rockcraft <rockcraft:index>` is a
  tool to create rocks – a new generation of secure, stable and OCI-compliant
  container images, based on Ubuntu.
- A :ref:`rock <rockcraft:explanation-rocks>`
  is an Ubuntu LTS-based container image. The official entrypoint for the
  image is :ref:`Pebble <rockcraft:explanation-pebble>`,
  a service manager that enhances container experience.

A Rockcraft framework is initially used to facilitate the creation of a well
structured, minimal and hardened container image, called a rock. A Charmcraft
profile can then be leveraged to add a software operator (charm) around the
aforementioned container image.

Encapsulating the original 12-factor application in a charm allows your
application to benefit from the entire
`charm ecosystem <https://charmhub.io/>`_, meaning that the app
can be connected to a database, e.g. an HA Postgres, observed through a Grafana
based observability stack, add ingress and much more.
