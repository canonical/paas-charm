.. _explanation_full_lifecycle:

How everything connects (source to production)
==============================================

The 12-Factor app support in Charmcraft and Rockcraft is an opinionated
framework based on the 12-Factor methodology. If you web app uses one of the
supported framework and follows the conventions of the tool, you can
easily charm it.

We recommend to put the Rockcraft project file (``rockcraft.yaml``) in the same
repository as your code, created with the
:ref:`Rockcraft extension <rockcraft:reference-extensions>`
for your specific framework. The rock generated with this project file
is a fully compliant OCI-image that can be used outside of the Juju ecosystem.

Your web app containerized in a rock will be managed by a charm, a software
operator orchestrated by Juju. You can create the charm using the
:doc:`init profile <charmcraft:reference/commands/init>`,
that will use the appropriate
:ref:`Charmcraft extension <charmcraft:extensions>`.
We recommend to place the charm code inside the ``charm`` directory in the same repository
as your code.

The 12-Factor app support in Charmcraft and Rockcraft does not enforce any
specific CI/CD pipeline. Some recommendations and useful tools are:

- For the build stage, the ``rockcraft`` and ``charmcraft`` tools are used to create the rock and charm artifacts.
- For integration tests involving charms, use the `Jubilant <https://github.com/canonical/jubilant>`_ library.
- `concierge <https://github.com/canonical/concierge>`_ is an opinionated utility to provision testing machines.
- Charmcraft's :doc:`test command <charmcraft:reference/commands/test>`, based
  on `Spread <https://github.com/canonical/spread>`_ is a convenient full-system test (task) distribution.
- Once your artifacts are ready, they can be
  :doc:`uploaded to Charmhub <charmcraft:reference/commands/upload>` and
  :doc:`promoted <charmcraft:reference/commands/release>` to the
  desired :ref:`channel <charmcraft:manage-channels>`. 
  This is not a mandatory step, as you can deploy charms locally without Charmhub.
- For the deployment, the current recommendation is to use the
  `Juju Terraform Provider <https://registry.terraform.io/providers/juju/juju/latest/docs>`_.

Juju is the engine that will orchestrate the software operators. The web app will be able
to integrate seamlessly with other charms, that can be running in Kubernetes or in Machines,
and on-premises or in the cloud.

For the operation of your applications, it is strongly recommended to use the 
`Canonical Observability Stack <https://charmhub.io/cos-lite>`_, an
out-of-the-box solution for improved day-2 operational insight.
