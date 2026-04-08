.. meta::
   :description: Familiarize yourself with contributing to the 12-factor app support project.

.. _how_to_contribute:

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
`contributor agreement <https://canonical.com/legal/contributors>`_ if you're interested in contributing to the solution.

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
:ref:`development setup <juju:set-things-up>`.

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

- If you are adding a feature that interacts with the filesystem, please include an integration test for it,
  ensuring that it runs as a non-root user. You can add the test in the 'tests/integration/general' folder.

- Submit the changes as a `pull request (PR)
  <https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/creating-a-pull-request-from-a-fork>`_.


Your changes will be reviewed in due time;
if approved, they will be eventually merged.


Describing pull requests
~~~~~~~~~~~~~~~~~~~~~~~~

To be properly considered, reviewed and merged,
your pull request must provide the following details:

- **Title**: Summarize the change in a short, descriptive title.

- **What this PR does**: Describe the problem that your pull request solves.
  Mention any new features, bug fixes or refactoring.

- **Why we need it**: Explain why the change is needed.

- **Checklist**: Complete the items in the checklist relevant to your pull request.

Signing commits
~~~~~~~~~~~~~~~

To improve contribution tracking, we use the
`Canonical contributor license agreement <https://assets.ubuntu.com/v1/ff2478d1-Canonical-HA-CLA-ANY-I_v1.2.pdf>`_
(CLA) as a legal sign-off, and we require all commits to have verified signatures.

Canonical contributor agreement
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The CLA sign-off is simple line at the
end of the commit message certifying that you wrote it
or have the right to commit it as an open-source contribution.

Verified signatures on commits
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

All commits in a pull request must have cryptographic (verified) signatures.
To add signatures on your commits, follow the
`GitHub documentation <https://docs.github.com/en/authentication/managing-commit-signature-verification/signing-commits>`_.


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
<https://canonical-starter-pack.readthedocs-hosted.com/dev/>`_
and hosted on `Read the Docs <https://about.readthedocs.com/>`_.

For syntax help and guidelines,
refer to the `Canonical style guides
<https://canonical-documentation-with-sphinx-and-readthedocscom.readthedocs-hosted.com/style-guide/>`_.

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

How to refer to the project
~~~~~~~~~~~~~~~~~~~~~~~~~~~

When you contribute documentation to the project, refer to the tooling as
"12-factor app support" or "12-factor framework support". If you contribute
to the documentation on `Charmcraft <https://github.com/canonical/charmcraft/>`_
or `Rockcraft <https://github.com/canonical/rockcraft/>`_, specify that the
tooling is natively supported in Charmcraft or Rockcraft respectively.

Optionally, if you are contributing documentation that's specific to a single
framework (such as Flask), you can refer to the tooling as
"Flask app support" or "Flask framework support". 

AI usage
~~~~~~~~

You are free to use any tools you want while preparing your contribution, including
AI, provided that you do so lawfully and ethically. 

Avoid using AI to complete
`Canonical Open Documentation Academy issues <https://github.com/canonical/open-documentation-academy/issues>`_.
The purpose of these issues is to provide newcomers with opportunities to
contribute to our projects and gain documentation skills. Using AI to
complete these tasks undermines their purpose.

If you use AI to help with your PRs, be mindful. Avoid submitting contributions
with entirely AI-generated documentation. The human aspect of documentation is
important to us, and that includes tone, syntax, perspectives, and the
occasional typo. 

Some examples of valid AI assistance includes:

* Checking for spelling or grammar errors
* Drafting plans or outlines
* Checking that your contribution aligns with the Canonical style guide

We have created instructions and tools that you can provide AI while preparing
your contribution in `copilot-collections <https://github.com/canonical/copilot-collections>`_: 

* `Documentation instructions <https://github.com/canonical/copilot-collections/tree/main/assets/instructions/documentation>`_
* `Documentation skills <https://github.com/canonical/copilot-collections/tree/main/assets/skills>`_

While it isn't necessary to use ``copilot-collections`` while preparing your
contribution, these files contain details about our documentation standards and
practices that will help the AI avoid common pitfalls when interacting with our
projects. By using these tools, you can avoid longer review times and nitpicks.

If you choose to use AI, please disclose this information to us by indicating
AI usage in the PR description (for instance, marking the checklist item about
AI usage). You don't need to go into explicit details about how and where you used AI.

Avoid submitting contributions that you don't fully understand.
You are responsible for the entire contribution, including the AI-assisted portions.
You must be willing to engage in discussion and respond to any questions, comments,
or suggestions we may have. 
