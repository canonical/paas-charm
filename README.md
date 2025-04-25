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
[comprehensive getting started tutorial](https://canonical-charmcraft.readthedocs-hosted.com/en/stable/tutorial/flask/)
for more!

Additional resources:

* [Tutorial to build a rock for a Flask application](https://documentation.ubuntu.com/rockcraft/en/latest/tutorial/flask)
* [Charmcraft `flask-framework` reference](https://canonical-charmcraft.readthedocs-hosted.com/en/stable/reference/extensions/flask-framework-extension/)
* [Charmcraft `flask-framework` how to guides](https://canonical-charmcraft.readthedocs-hosted.com/en/stable/howto/manage-a-12-factor-app-charm/)
* [Rockcraft`flask-framework`
   reference](https://documentation.ubuntu.com/rockcraft/en/latest/reference/extensions/flask-framework/)

## Documentation

The 12-Factor framework support documentation provides guidance and learning material about
the tooling, getting started, customization, and usage.
The documentation is hosted on Read the Docs.

Build the 12-Factor app support documentation located in this repository:

```bash
cd docs
make run
```

Additional resources:

* [12-Factor app support documentation](https://canonical-12-factor-app-support.readthedocs-hosted.com/en/latest/)
* [Rockcraft](https://documentation.ubuntu.com/rockcraft/en/latest/):
  Documentation related to the OCI image containers
* [Charmcraft](https://canonical-charmcraft.readthedocs-hosted.com/en/stable/):
  Documentation related to the software operators (charms)

## Contributing

Is there something missing from the 12-Factor app support framework? We
welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for more details.
