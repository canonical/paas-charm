# PaaS Charm

Easily deploy and operate your Flask or Django applications and associated
infrastructure, such as databases and ingress, using open source tooling. This
lets you focus on creating applications for your users backed with the
confidence that your operations are taken care of by world class tooling
developed by Canonical, the creators of Ubuntu.

Have you ever created an application and then wanted to deploy it for your users
only to either be forced to use a proprietary public cloud platform or manage
the deployment and operations yourself? PaaS Charm will take your
application and create an OCI image using Rockcraft and operations code using
Charmcraft for you. The full suite of tools is open source so you can see
exactly how it works and even contribute! After creating the app charm and
image, you can then deploy your application into any Kubernetes cluster using
Juju. Need a database? Using Juju you can deploy a range of popular open source
databases, such as [PostgreSQL](https://charmhub.io/postgresql) or
[MySQL](https://charmhub.io/mysql), and integrate them with your application
with a few commands. Need an ingress to serve traffic? Use Juju to deploy and
integrate a range of ingresses, such as
[Traefik](https://charmhub.io/traefik-k8s), and expose your application to
external traffic in seconds.

## Getting Started

There are 2 requirements for the flask application:

* There is a `requirements.txt` file in the project root
* The WSGI path is `app:app`

Make sure that you have the `latest/edge` version of Charmcraft and Rockcraft
installed:

```bash
sudo snap install charmcraft --channel latest/edge --classic
sudo snap install rockcraft --channel latest/edge --classic
```

Both have the `flask-framework` profile to create the required files
and include the `flask-framework` extension which will do all the hard
operational work for you and you just need to fill in some metadata in the
`rockcraft.yaml` and `charmcraft.yaml` files. To create the necessary files:

```bash
rockcraft init --profile flask-framework
mkdir charm
cd charm
charmcraft init --profile flask-framework
```

After packing the rock and charm using `rockcraft pack` and `charmcraft pack`
and uploading the rock to a k8s registry, you can juju deploy your flask
application, integrate it with ingress and start serving traffic to your users!

Read the
[comprehensive getting started tutorial](https://juju.is/docs/sdk/write-your-first-kubernetes-charm-for-a-flask-app)
for more!

Additional resources:

* [Tutorial to build a rock for a Flask application](https://documentation.ubuntu.com/rockcraft/en/latest/tutorial/flask.html)
* [Charmcraft `flask-framework` reference](https://juju.is/docs/sdk/charmcraft-extension-flask-framework)
* [Charmcraft `flask-framework` how to guides](https://juju.is/docs/sdk/build-a-paas-charm)
* [Rockcraft`flask-framework`
   reference](https://documentation.ubuntu.com/rockcraft/en/latest/reference/extensions/flask-framework/)

## Contributing

Is there something missing from the PaaS Charm framework? PaaS Charm
welcomes contributions! This section covers how to add a new integration and a
new framework.

### Add an Integration

There are a few recommended steps to add a new integration which we'll go
through below.

1. Please write a proposal on the
  [charm topic on discourse](https://discourse.charmhub.io/c/charm/41). This
  should cover things like:

  * The integration you intend add
  * For each of the frameworks that PaaS Charm supports:

    - The commonly used package(s) to make use of the integration
    - The environment variables, configuration etc. that would be made available
      to the app
    - An example for how to use the integration within an app

  * The proposed implementation in `paas-app`. Take a look at
    [`charm.py`](paas_charm/_gunicorn/charm.py) for `gunicorn` based
    frameworks for integration examples.

1. Update the
  [reference](https://juju.is/docs/sdk/charmcraft-extension-flask-framework)
  with the new integration
1. Raise a pull request to this repository adding support for the integration.
1. Add a commented entry for `requires` to all the relevant Charmcraft
  [templates](https://github.com/canonical/charmcraft/tree/main/charmcraft/templates)
  for the new integration

### Add a Framework

There are a few recommended steps to add a new framework which we'll go through
below.

1. Please write a proposal on the
  [charm topic on discourse](https://discourse.charmhub.io/c/charm/41). This
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
1. Write a tutorial and reference documentation for the framework. As an
  example, this is the flask
  [tutorial](https://juju.is/docs/sdk/write-your-first-kubernetes-charm-for-a-flask-app)
  and [reference](https://juju.is/docs/sdk/charmcraft-extension-flask-framework)
  documentation.
