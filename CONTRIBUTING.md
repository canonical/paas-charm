# Contributing

This document explains the processes and practices recommended for contributing
enhancements to the 12-Factor app support project.

## Overview

- Generally, before developing enhancements to this charm, you should consider
  [opening an issue](https://github.com/canonical/paas-charm/issues) explaining your use case.
- If you would like to chat with us about your use-cases or proposed implementation, you can reach
  us at [Canonical Matrix public channel](https://matrix.to/#/#12-factor-charms:ubuntu.com).
- Familiarizing yourself with the [Charmed Operator Framework](https://juju.is/docs/sdk) library
  will help you a lot when working on new features or bug fixes.
- All enhancements require review before being merged. Code review typically examines
  - code quality
  - test coverage
  - user experience for Juju operators of this charm.
- Please help us out in ensuring easy to review branches by rebasing your pull request branch onto the `main` branch.
  This also avoids merge commits and creates a linear Git commit history.
- Please generate src documentation for every commit. See the section below for more details.
- If you are adding a feature that interacts with the filesystem, please include an integration test for it,
  ensuring that it runs as a non-root user. You can add the test in the 'tests/integration/general' folder.

## Canonical Contributor Agreement

Canonical welcomes contributions to the 12-Factor app support project. Please check out our
[contributor agreement](https://ubuntu.com/legal/contributors) if you're interested in contributing to the solution.

## Developing

To make contributions to this charm, you'll need a working
[development setup](https://canonical-juju.readthedocs-hosted.com/en/
latest/user/howto/manage-your-deployment/manage-your-deployment-environment/).

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

### Testing

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
