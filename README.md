# PaaS Charm

Easily deploy and operate your Flask, Django, FastAPI, Go, Express,
or Spring Boot applications and associated
infrastructure, such as databases and ingress, using open source tooling.
This lets you focus on creating applications for your users backed with the
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

This project provides 12-factor app support across multiple frameworks
(Flask, Django, FastAPI, Go, Express, and Spring Boot).
The quickest way to get started is to follow the framework-specific tutorials linked below.

Make sure that you have the `latest/edge` version of Charmcraft and Rockcraft
installed:

```bash
sudo snap install charmcraft --channel latest/edge --classic
sudo snap install rockcraft --channel latest/edge --classic
```

Both tools provide framework profiles and extensions that
generate the required files and handle the operational workload.
You only need to fill in some metadata in the `rockcraft.yaml` and `charmcraft.yaml` files.
To create the necessary files (example shown for Flask):

```bash
rockcraft init --profile flask-framework
mkdir charm
cd charm
charmcraft init --profile flask-framework
```

After packing the rock and charm using `rockcraft pack` and `charmcraft pack`
and uploading the rock to a k8s registry, you can juju deploy your application,
integrate it with ingress, and start serving traffic to your users.

Read the framework-specific tutorials for a complete walkthrough:

* [Django](https://documentation.ubuntu.com/charmcraft/stable/tutorial/kubernetes-charm-django/)
* [Express](https://documentation.ubuntu.com/charmcraft/stable/tutorial/kubernetes-charm-express/)
* [FastAPI](https://documentation.ubuntu.com/charmcraft/stable/tutorial/kubernetes-charm-fastapi/)
* [Flask](https://documentation.ubuntu.com/charmcraft/stable/tutorial/kubernetes-charm-flask/)
* [Go](https://documentation.ubuntu.com/charmcraft/stable/tutorial/kubernetes-charm-go/)
* [Spring Boot](https://documentation.ubuntu.com/charmcraft/stable/tutorial/kubernetes-charm-spring-boot/)


## Documentation

The 12-Factor framework support documentation provides guidance and learning material about
the tooling, getting started, customization, and usage.
The documentation is hosted on Read the Docs.

Build the 12-Factor app support documentation located in this repository:

```bash
cd docs
make run
```

If you have any documentation-related comments, issues, or suggestions, please open an issue or
pull request in this repository, or reach out to us on [Matrix](https://matrix.to/#/#12-factor-charms:ubuntu.com).


## Additional resources

* [12-Factor app support documentation](https://canonical-12-factor-app-support.readthedocs-hosted.com/latest/)
* [Rockcraft](https://documentation.ubuntu.com/rockcraft/latest/):
  Documentation related to the OCI image containers
* [Charmcraft](https://documentation.ubuntu.com/charmcraft/stable/):
  Documentation related to the software operators (charms)

## Contributing

Is there something missing from the 12-Factor app support framework?
We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for more details.

Reach out to us on [Matrix](https://matrix.to/#/#12-factor-charms:ubuntu.com) with your questions
and use cases.
