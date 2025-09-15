.. Copyright 2025 Canonical Ltd.
.. See LICENSE file for licensing details.

.. _explanation_why_use_12_factor:

Why use the 12-factor support?
==============================

The native support for web applications in Rockcraft and Charmcraft provides
a streamlined approach for deploying and integrating your application into the
Juju ecosystem. It's possible to build a rock and charm from scratch for your
web application, but this approach comes with a high learning curve.

The main advantages of the support are as follows:

* You're not locked into a closed-source or paid system -- Rockcraft, Charmcraft,
  and Juju are all open-source.
* You don't need a lot of product expertise to get started -- with only a few
  commands, you can fully set up a Kubernetes environment for your web application without
  needing to build the rock or charm from scratch.
* By using the native support, your application comes out of the box with built-in integrations
  with observability, ingress, databases, and much more, saving you time and effort to
  set them up yourself.
* Portability: You can use the rock for your web application with Docker, meaning you're not
  locked into the Juju ecosystem.
* Scalability: Juju comes with the ability to add or modify the amount of resources for
  your deployment, meaning that you can achieve high availability (HA) for your app.