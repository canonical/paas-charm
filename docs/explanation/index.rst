.. Copyright 2025 Canonical Ltd.
.. See LICENSE file for licensing details.

Explanation
===========

The following explanations provide context and clarification on key topics related to the use and
configuration of web app frameworks.

12-factor app principles
------------------------

The native 12-factor framework support in Rockcraft and Charmcraft provides an
opinionated way to easily integrate your web application into the Juju ecosystem.
The Juju ecosystem provides a multitude of `curated software operators <https://charmhub.io/>`_
for your observability stack, database, SSO, and many more and allows their deployment and
lifecycle management on metal, on VMs, on K8s and on cloud providers
(see `substrates <https://documentation.ubuntu.com/juju/3.6/reference/cloud/>`_).

That way, the 12-factor framework support in Rockcraft and Charmcraft offers
a fully fledged Platform as a Service that streamlines managing the
infrastructure, whether on premises or on cloud, at any scale, and allows developers
to focus on their core competences instead of a complex software stack.

The glue point of the 12-factor framework support in Rockcraft and Charmcraft is
the `12-factor methodology <https://12factor.net/>`_. The 12-Factor methodology
is a set of best practices for building modern, scalable, and maintainable web
applications. By following these principles, you can easily create a rock
(OCI image) and a charm (software operator) for your web app that can take
advantage of the full Juju ecosystem.

12-Factor principles and its support in Charmcraft and Rockcraft
----------------------------------------------------------------

The 12-Factor app support in Charmcraft and Rockcraft is based on the principles
stated in the 12-Factor methodology. Learn more about the components
involved and how the principles are applied in the following links.

.. toctree::
   :maxdepth: 1
   :numbered:

   Juju, charms and rocks <foundations>
   How the 12-Factor principles are applied in rocks and charms <how-are-12-factor-principles-applied>
   How everything connects (source to production) <full-lifecycle>
   Web app framework <web-app-framework>
   Charm architecture <charm-architecture>
