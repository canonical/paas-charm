.. Copyright 2025 Canonical Ltd.
.. See LICENSE file for licensing details.

How-to guides
=============

The following guides provide comprehensive, step-by-step instructions for the common
tasks related to the 12-factor tooling, from working with the relevant products to
contributing.

Manage a 12-factor app rock
---------------------------

The Rockcraft documentation contains a set of how-to guides for managing
a 12-factor app container image.

* `Manage a 12-Factor app rock <https://documentation.ubuntu.com/rockcraft/en/latest/how-to/build-a-12-factor-app-rock/>`_
   * `Set up a 12-Factor app rock <https://documentation.ubuntu.com/rockcraft/en/latest/how-to/web-app-rocks/set-up-web-app-rock/>`_:
     Initialize and configure a rock using the 12-factor extensions.
   * `Use a 12-Factor app rock <https://documentation.ubuntu.com/rockcraft/en/latest/how-to/web-app-rocks/use-web-app-rock/>`_:
     Learn about the various ways you can use and update your rock.

Manage a 12-factor app charm
----------------------------

The Charmcraft documentation contains a set of how-to guides for initializing,
configuring, integrating, and using a 12-factor app charm.

* `Manage a 12-factor app charm <https://canonical-charmcraft.readthedocs-hosted.com/en/latest/howto/manage-web-app-charms/>`_:
   * `Initialization <https://canonical-charmcraft.readthedocs-hosted.com/latest/howto/manage-web-app-charms/#initialization>`_
   * `Configuration <https://canonical-charmcraft.readthedocs-hosted.com/latest/howto/manage-web-app-charms/configure-web-app-charm/>`_:
     The 12-factor tooling includes different ways you can customize to fit your use case.
     These guides provide instructions on tasks like adding configurations, actions, and
     managing secrets.
   * `Relations <https://canonical-charmcraft.readthedocs-hosted.com/latest/howto/manage-web-app-charms/integrate-web-app-charm/>`_:
     The tooling provides you the ability to integrate with preexisting charms in the
     Juju ecosystem. These guides get you started with three commonly used relations:
     databases, ingress, and observability.
   * `Usage <https://canonical-charmcraft.readthedocs-hosted.com/latest/howto/manage-web-app-charms/use-web-app-charm/>`_:
     Learn more about tasks such as migrations and troubleshooting.

Contribute to the project
-------------------------

Below are step-by-step instructions for developing and contributing to the 12-factor app project.

* :ref:`Add a new framework <how_to_add_new_framework>`: A guide that details the process for
  contributing to the 12-factor project, Rockcraft, and Charmcraft.
* :ref:`Contribute <how_to_contribute>`: Recommended processes and practices for contributing
  enhancements to the 12-factor project
* :ref:`Upgrade <how_to_upgrade>`: Information for upgrading your 12-factor app rock, deployed
  charm, or ``paas-charm`` version. 

.. toctree::
   :hidden:
   :maxdepth: 1

   Add a new framework <add-new-framework>
   Contribute <contributing>
   Upgrade <upgrade>
