.. Copyright 2025 Canonical Ltd.
.. See LICENSE file for licensing details.

.. _explanation:

Explanation
===========

The following explanations provide context and clarification on key topics related to the use and
configuration of web app frameworks.

12-factor app principles
------------------------

The glue point of the 12-factor framework support in Rockcraft and Charmcraft is
the `12-factor methodology <https://12factor.net/>`_. The 12-Factor methodology
is a set of best practices for building modern, scalable, and maintainable web
applications. 

Learn more about the components involved and how the principles are applied in
the following pages:

* :ref:`Juju, charms and rocks <explanation_foundations>`: Descriptions of
  the Canonical products involved. 
* :ref:`How the 12-factor principles are applied in rocks and charms <explanation_12_factor_principles_applied>`: 
  An overview on how the 12-factor methodology is applied to rocks and charms.

12-factor ecosystem
-------------------

The native 12-factor framework support in Rockcraft and Charmcraft provides an
opinionated way to easily integrate your web application into the Juju ecosystem.
The following pages provides more information on the ecosystem and how the 12-factor
framework support fits in:

* :ref:`How everything connects <explanation_full_lifecycle>`: An overview of how the
  various components come together to form the 12-factor ecosystem.
* :ref:`Web app framework <explanation_web_app_frameworks>`: More details about the
  supported web app frameworks.
* :ref:`Why use the 12-factor support <explanation_why_use_12_factor>`: A summary of the
  advantages of using the native support in Charmcraft and Rockcraft.
* :ref:`Opinionated nature of the 12-factor tooling <explanation_opinionated_nature>`:
  Description of how the 12-factor tooling is opinionated and when those opinions can be
  overridden by users.

.. toctree::
   :maxdepth: 1
   :numbered:
   :hidden:

   Juju, charms and rocks <foundations>
   How the 12-factor principles are applied in rocks and charms <how-are-12-factor-principles-applied>
   The 12-factor ecosystem <full-lifecycle>
   Web app framework <web-app-framework>
   Why use 12-factor? <why-12-factor>
   Opinionated nature of the tooling <opinionated-nature-tooling>
