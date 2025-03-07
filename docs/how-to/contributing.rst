.. Copyright 2025 Canonical Ltd.
.. See LICENSE file for licensing details.
.. _how-to-contribute:

.. TODO: Update all sections containing TODOs; make sure no TODOs are left

How to contribute
=================

We believe that everyone has something valuable to contribute,
whether you're a coder, a writer or a tester.
Here's how and why you can get involved:

- **Why join us?** Work with like-minded people, develop your skills,
  connect with diverse professionals, and make a difference.

- **What do you get?** Personal growth, recognition for your contributions,
  early access to new features and the joy of seeing your work appreciated.

- **Start early, start easy**: Dive into code contributions,
  improve documentation, or be among the first testers.
  Your presence matters,
  regardless of experience or the size of your contribution.


The guidelines below will help keep your contributions effective and meaningful.


Code of conduct
---------------

When contributing, you must abide by the
`Ubuntu Code of Conduct <https://ubuntu.com/community/ethos/code-of-conduct>`_.

.. TODO: Do we link the `IS Charms contributing guide <https://github.com/canonical/is-charms-contributing-guide>`_?

Canonical contributor agreement
-------------------------------

Canonical welcomes contributions to the 12-Factor app support project. Please check out our
`contributor agreement <https://ubuntu.com/legal/contributors>`_ if you're interested in contributing to the solution.

Releases and versions
---------------------

The 12-factor app support project uses `semantic versioning <https://semver.org/>`_;
major releases occur once or twice a year.

Please ensure that any new feature, fix, or significant change is documented by
adding an entry to the `CHANGELOG.md <https://github.com/canonical/paas-charm/blob/main/CHANGELOG.md>`_ file.

To learn more about changelog best practices, visit `Keep a Changelog <https://keepachangelog.com/>`_.


Environment setup
-----------------

To make contributions to this charm, you'll need a working
`development setup <https://canonical-juju.readthedocs-hosted.com/en/latest/user/howto/manage-your-deployment/manage-your-deployment-environment/>`_.

The code for this charm can be downloaded as follows:

.. code::

    git clone https://github.com/canonical/paas-charm

You can use the environments created by ``tox`` for development:

.. code-block::

    tox --notest -e unit
    source .tox/unit/bin/activate

You can create an environment for development with ``python3-venv``:

.. code-block::
  
    sudo apt install python3-venv
    python3 -m venv venv

Install ``tox`` inside the virtual environment for testing.

Submissions
-----------

.. TODO: Suggest your own PR process or drop if excessive

If you want to address an issue or a bug in the 12-factor project,
notify in advance the people involved to avoid confusion;
also, reference the issue or bug number when you submit the changes.

- `Fork
  <https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/about-forks>`_
  our `GitHub repository <https://github.com/canonical/paas-charm>`_
  and add the changes to your fork,
  properly structuring your commits,
  providing detailed commit messages
  and signing your commits.

- Make sure the updated project builds and runs without warnings or errors;
  this includes linting, documentation, code and tests.

- Submit the changes as a `pull request (PR)
  <https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/creating-a-pull-request-from-a-fork>`_.


Your changes will be reviewed in due time;
if approved, they will be eventually merged.


Describing pull requests
~~~~~~~~~~~~~~~~~~~~~~~~

To be properly considered, reviewed and merged,
your pull request must provide the following details:

- **Title**: Summarize the change in a short, descriptive title.

- **Overview**: Describe the problem that your pull request solves.
  Mention any new features, bug fixes or refactoring.

- **Rationale**: Explain why the change is needed.

- **Juju Events Changes**: Describe any changes made to Juju events, or
  "None" if the pull request does not change any Juju events.

- **Module Changes**: Describe any changes made to the module, or "None"
  if your pull request does not change the module.

- **Library Changes**: Describe any changes made to the ``paas-charm`` library,
  or "None" is the library is not affected.

- **Checklist**: Complete the following items:

  - The `charm style guide <https://juju.is/docs/sdk/styleguide>`_ was applied
  - The `contributing guide <https://github.com/canonical/is-charms-contributing-guide>`_ was applied
  - The changes are compliant with `ISD054 - Managing Charm Complexity <https://discourse.charmhub.io/t/specification-isd014-managing-charm-complexity/11619>`_
  - The documentation for RTD is updated
  - The PR is tagged with appropriate label (trivial, senior-review-required)
  - The changelog has been updated

Signing commits
~~~~~~~~~~~~~~~

.. TODO: Update with your suggestions or drop if excessive

To improve contribution tracking,
we use the developer certificate of origin
(`DCO 1.1 <https://developercertificate.org/>`_)
and require a "sign-off" for any changes going into each branch.

The sign-off is a simple line at the end of the commit message
certifying that you wrote it
or have the right to commit it as an open-source contribution.

To sign off on a commit, use the ``--signoff`` option in ``git commit``.


Code
----

Formatting and linting
~~~~~~~~~~~~~~~~~~~~~~

This project uses ``tox`` for managing test environments. There are some pre-configured environments
that can be used for linting and formatting code when you're preparing contributions to the charm:

* ``tox``: Executes all of the basic checks and tests (``lint``, ``unit``, ``static``, and ``coverage-report``).
* ``tox -e fmt``: Runs formatting using ``black`` and ``isort``.
* ``tox -e lint``: Runs a range of static code analysis to check the code.
* ``tox -e static``: Runs other checks such as ``bandit`` for security issues.

Structure
~~~~~~~~~

- **Check linked code elements**:
  Check that coupled code elements, files and directories are adjacent.
  For instance, store test data close to the corresponding test code.

- **Group variable declaration and initialization**:
  Declare and initialize variables together
  to improve code organization and readability.

- **Split large expressions**:
  Break down large expressions
  into smaller self-explanatory parts.
  Use multiple variables where appropriate
  to make the code more understandable
  and choose names that reflect their purpose.

- **Use blank lines for logical separation**:
  Insert a blank line between two logically separate sections of code.
  This improves its structure and makes it easier to understand.

- **Avoid nested conditions**:
  Avoid nesting conditions to improve readability and maintainability.

- **Remove dead code and redundant comments**:
  Drop unused or obsolete code and comments.
  This promotes a cleaner code base and reduces confusion.

- **Normalize symmetries**:
  Treat identical operations consistently, using a uniform approach.
  This also improves consistency and readability.


Documentation
-------------

The documentation is stored in the ``docs`` directory of the repository.
It is based on the `Canonical starter pack
<https://canonical-starter-pack.readthedocs-hosted.com/latest/>`_
and hosted on `Read the Docs <https://about.readthedocs.com/>`_.

For syntax help and guidelines,
refer to the `Canonical style guides
<https://canonical-documentation-with-sphinx-and-readthedocscom.readthedocs-hosted.com/#style-guides>`_.

In structuring,
the documentation employs the `Diátaxis <https://diataxis.fr/>`_ approach.

To run the documentation locally before submitting your changes:

.. code-block:: bash

   make run


Automatic checks
~~~~~~~~~~~~~~~~

GitHub runs automatic checks on the documentation
to verify spelling, validate links and suggest inclusive language.

You can (and should) run the same checks locally:

.. code-block:: bash

   make spelling
   make linkcheck
   make woke
