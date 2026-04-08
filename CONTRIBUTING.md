# Contributing

This document explains the processes and practices recommended for contributing enhancements to the Paas Charm Operator.

## Overview

- Generally, before developing enhancements to this charm, you should consider [opening an issue
  ](https://github.com/canonical/paas-charm/issues) explaining your use case.
- If you would like to chat with us about your use-cases or proposed implementation, you can reach
  us at [Canonical Matrix public channel](https://matrix.to/#/#charmhub-charmdev:ubuntu.com)
  or [Discourse](https://discourse.charmhub.io/).
- Familiarizing yourself with the [Juju documentation](https://documentation.ubuntu.com/juju/3.6/howto/manage-charms/)
  will help you a lot when working on new features or bug fixes.
- All enhancements require review before being merged. Code review typically examines
  - code quality
  - test coverage
  - user experience for Juju operators of this charm.
- Once your pull request is approved, we squash and merge your pull request branch onto
  the `main` branch. This creates a linear Git commit history.
- For further information on contributing, please refer to our
  [Contributing Guide](https://github.com/canonical/is-charms-contributing-guide).

## Code of conduct

When contributing, you must abide by the
[Ubuntu Code of Conduct](https://ubuntu.com/community/ethos/code-of-conduct).

## Changelog

Please ensure that any new feature, fix, or significant change is documented by
adding an entry to the [CHANGELOG.md](docs/changelog.md) file. Use the date of the
contribution as the header for new entries.

To learn more about changelog best practices, visit [Keep a Changelog](https://keepachangelog.com/).

## Submissions

If you want to address an issue or a bug in this project,
notify in advance the people involved to avoid confusion;
also, reference the issue or bug number when you submit the changes.

- [Fork](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/about-forks)
  our [GitHub repository](https://github.com/canonical/paas-charm)
  and add the changes to your fork, properly structuring your commits,
  providing detailed commit messages and signing your commits.
- Make sure the updated project builds and runs without warnings or errors;
  this includes linting, documentation, code and tests.
- Submit the changes as a
  [pull request (PR)](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/creating-a-pull-request-from-a-fork).

Your changes will be reviewed in due time; if approved, they will be eventually merged.

### AI

You are free to use any tools you want while preparing your contribution, including
AI, provided that you do so lawfully and ethically.

Avoid using AI to complete issues tagged with the "good first issues" label. The
purpose of these issues is to provide newcomers with opportunities to contribute
to our projects and gain coding skills. Using AI to complete these tasks
undermines their purpose.

We have created instructions and tools that you can provide AI while preparing your contribution: [`copilot-collections`](https://github.com/canonical/copilot-collections)

While it isn't necessary to use `copilot-collections` while preparing your
contribution, these files contain details about our quality standards and
practices that will help the AI avoid common pitfalls when interacting with
our projects. By using these tools, you can avoid longer review times and nitpicks.

If you choose to use AI, please disclose this information to us by indicating
AI usage in the PR description (for instance, marking the checklist item about
AI usage). You don't need to go into explicit details about how and where you used AI.

Avoid submitting contributions that you don't fully understand.
You are responsible for the entire contribution, including the AI-assisted portions.
You must be willing to engage in discussion and respond to any questions, comments,
or suggestions we may have. 

### Signing commits

To improve contribution tracking,
we use the [Canonical contributor license agreement](https://assets.ubuntu.com/v1/ff2478d1-Canonical-HA-CLA-ANY-I_v1.2.pdf)
(CLA) as a legal sign-off, and we require all commits to have verified signatures.

#### Canonical contributor agreement

Canonical welcomes contributions to the 12-Factor app support project. Please check out our
[contributor agreement](https://ubuntu.com/legal/contributors) if you're interested in contributing to the solution.

The CLA sign-off is simple line at the
end of the commit message certifying that you wrote it
or have the right to commit it as an open-source contribution.

#### Verified signatures on commits

All commits in a pull request must have cryptographic (verified) signatures.
To add signatures on your commits, follow the
[GitHub documentation](https://docs.github.com/en/authentication/managing-commit-signature-verification/signing-commits).

## Develop

To make contributions to this charm, you'll need a working
[development setup](https://documentation.ubuntu.com/juju/latest/howto/manage-your-juju-deployment/set-up-your-juju-deployment-local-testing-and-development/).

The code for this charm can be downloaded as follows:

```
git clone https://github.com/canonical/paas-charm
```

You can use the environments created by `tox` for development:

```shell
tox --notest -e unit
source .tox/unit/bin/activate
```

You can create an environment for development with `tox`:

```shell
tox devenv -e integration
source venv/bin/activate
```

### Test

This project uses `tox` for managing test environments. There are some pre-configured environments
that can be used for linting and formatting code when you're preparing contributions to the charm:

* `tox`: Runs all of the basic checks (`lint`, `unit`, `static`, and `coverage-report`).
* `tox -e fmt`: Runs formatting using `black` and `isort`.
* `tox -e lint`: Runs a range of static code analysis to check the code.
* `tox -e static`: Runs other checks such as `bandit` for security issues.
* `tox -e unit`: Runs the unit tests.
* `tox -e integration`: Runs the integration tests.

## Add an integration

There are a few recommended steps to add a new integration which we'll go
through below.

1. Please write a proposal on the
  [charm topic on Discourse](https://discourse.charmhub.io/c/charm/41). This
  should cover things like:

  * The integration you intend add.
  * For each of the frameworks that PaaS Charm supports:

    - The commonly used package(s) to make use of the integration.
    - The environment variables, configuration etc. that would be made available
      to the app.
    - An example for how to use the integration within an app.

  * The proposed implementation in `paas-app`. Take a look at
    [`charm.py`](paas_charm/_gunicorn/charm.py) for `gunicorn` based
    frameworks for integration examples.

1. Update the
  [reference](https://canonical-charmcraft.readthedocs-hosted.com/en/stable/reference/extensions/)
  with the new integration
1. Raise a pull request to this repository adding support for the integration.
1. Add a commented entry for `requires` to all the relevant Charmcraft
  [templates](https://github.com/canonical/charmcraft/tree/main/charmcraft/templates)
  for the new integration

## Add a framework

There are a few recommended steps to add a new framework which we'll go through
below.

1. Please write a proposal on the
  [charm topic on Discourse](https://discourse.charmhub.io/c/charm/41). This
  should cover things like:

  * The programming language and framework you are thinking of
  * Create an example `rockcraft.yaml` file and build a working OCI image. To
    see an example for `flask`, install Rockcraft and run
    `rockcraft init --profile flask-framework` and run
    `rockcraft expand-extensions` and inspect the output.
  * Create an example `charmcraft.yaml` file and build a working charm. To see
    an example for `flask`, install Charmcraft and run
    `charmcraft init --profile flask-framework` and run
    `charmcraft expand-extensions` and inspect the output.
  * How the configuration options of the charm map to environment variables,
    configurations or another method of passing the information to the app
  * The requirements and conventions for how users need to configure their app
    to work with PaaS Charm
  * Which web server to use

1. Raise a pull request to [rockcraft](https://github.com/canonical/rockcraft)
  adding a new extension and profile for the framework. This is the flask
  [profile](https://github.com/canonical/rockcraft/blob/fdd2dee18c81b12f25e6624a5a48f9f1ac9fdb90/rockcraft/commands/init.py#L79)
  and
  [extension](https://github.com/canonical/rockcraft/blob/fdd2dee18c81b12f25e6624a5a48f9f1ac9fdb90/rockcraft/extensions/gunicorn.py#L176).
  The OCI image should work standalone, not just with the charm for the
  framework.
1. Raise a pull request to this repository adding a new parent class that can be
  used by the app charms. The following is the
  [example for flask](./paas_charm/flask/charm.py).
1. Raise a pull request to
  [charmcraft](https://github.com/canonical/charmcraft) adding a new extension
  and profile for the framework. This is the flask
  [profile](https://github.com/canonical/charmcraft/tree/main/charmcraft/templates/init-flask-framework)
  and
  [extension](https://github.com/canonical/charmcraft/blob/b6baa10566e3f3933cbd42392a0fe62cc79d2b6b/charmcraft/extensions/gunicorn.py#L167).

