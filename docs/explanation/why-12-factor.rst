.. Copyright 2025 Canonical Ltd.
.. See LICENSE file for licensing details.

.. _explanation_why_use_12_factor:

Why use the 12-factor support?
==============================

The native support for web applications in Rockcraft and Charmcraft provides
a streamlined approach for deploying and integrating your application into the
Juju ecosystem. It's possible to build a rock and charm from scratch for your
web application, but this approach comes with a high learning curve.

The main advantages of the using the native support are as follows:

* You're not locked into a closed-source or paid system -- ``paas-charm``, Rockcraft,
  Charmcraft, and Juju are all open-source software, providing you with a multicloud
  solution for your development and production needs.
* Using the tooling doesn't require significant product expertise -- with only a few
  commands, you can set up a Kubernetes environment for your web application without
  building the rock or charm from scratch.
* Your application comes out of the box with built-in integrations for observability,
  ingress, databases, and much more, saving you time and effort from setting up the
  integrations yourself.
* The 12-factor tooling is updated with the latest Juju and Rockcraft features and
  best practices. By using the tooling, you're guaranteed to follow best practices while
  taking advantage of all the latest available features.

