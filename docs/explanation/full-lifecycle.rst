.. _explanation_full_lifecycle:

How everything connects (source to production)
==============================================

The 12-Factor app support in Charmcraft and Rockcraft is an opinionated
framework based on the 12-Factor methodology. If you web app uses one of the
supported framework and follows the conventions of the tool, you can
easily charm it.

We recommend to put the Rockcraft project file (``rockcraft.yaml``) in the same
repository as your code, created with the
`Rockcraft extension <https://documentation.ubuntu.com/rockcraft/stable/reference/extensions/>`_
for your specific framework. The rock generated with this project file
is a fully compliant OCI-image that can be used outside of the Juju ecosystem.

Your web app containerized in a rock will be managed by a charm, a software
operator orchestrated by Juju. You can create the charm using the
`init profile <https://canonical-charmcraft.readthedocs-hosted.com/latest/reference/commands/init/>`_,
that will use the appropriate
`Charmcraft extension <https://canonical-charmcraft.readthedocs-hosted.com/latest/reference/extensions/>`_.
We recommend to place the charm code inside the ``charm`` directory in the same repository
as your code.

The 12-Factor app support in Charmcraft and Rockcraft does not enforce any
specific CI/CD pipeline. Some recommendations and useful tools are:

- For the build stage, the ``rockcraft`` and ``charmcraft`` tools are used to create the rock and charm artifacts.
- For integration tests involving charms, use the `Jubilant <https://github.com/canonical/jubilant>`_ library.
- `concierge <https://github.com/canonical/concierge>`_ is an opinionated utility to provision testing machines.
- Charmcraft's `test command <https://canonical-charmcraft.readthedocs-hosted.com/latest/reference/commands/test/>`_, based
  on `Spread <https://github.com/canonical/spread>`_ is a convenient full-system test (task) distribution.
- Once your artifacts are ready, they can be
  `uploaded to Charmhub <https://canonical-charmcraft.readthedocs-hosted.com/3.4.5/reference/commands/upload/>`_ and
  `promoted <https://canonical-charmcraft.readthedocs-hosted.com/3.4.5/reference/commands/release/>`_ to the
  desired `channel <https://canonical-charmcraft.readthedocs-hosted.com/stable/howto/manage-channels/>`_. 
  This is not a mandatory step, as you can deploy charms locally without Charmhub.
- For the deployment, the current recommendation is to use the
  `Juju Terraform Provider <https://registry.terraform.io/providers/juju/juju/latest/docs>`_.

Juju is the engine that will orchestrate the software operators. The web app will be able
to integrate seamlessly with other charms, that can be running in Kubernetes or in Machines,
and on-premises or in the cloud.

For the operation of your applications, it is strongly recommended to use the 
`Canonical Observability Stack <https://charmhub.io/cos-lite>`_, an
out-of-the-box solution for improved day-2 operational insight.
