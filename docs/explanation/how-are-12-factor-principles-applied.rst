.. _explanation_12_factor_principles_applied:

How 12-Factor app principles are applied in rocks and charms
============================================================

The `12-factor App <https://12factor.net/>`_ is a methodology to build
applications that are scalable, maintainable, and deployable. The twelve
factors are a set of well established best practices that are specially
relevant for web applications in cloud platforms.

Juju provides a strong ecosystem composed of a multitude of high
quality software operators that enables the deployment, integration and
lifecycle management at any scale, on any infrastructure. The best way
to take advantage of this strong ecosystem is to create a charm for
your application.

If your web application is written in one of the supported frameworks
and follows the conventions for the 12-Factor app support in Charmcraft
and Rockcraft based on the 12-Factor principles, you will be able to create
a charm out of the box. In the spirit of Platform as a Service (PaaS)
you will be able to access a complete platform based on Juju.

This is how the 12-Factor principles are applied in the context of rocks and charms:

- **I Codebase.** A twelve-factor app should be always tracked in version control. There
  can be many deploys in many environments of one commit and there can be deploys
  that are related to different commits versions. A single repository can contain
  the web app, the ``rockcraft.yaml`` and the charm code, but will not contain configuration
  related to a deployment. A commit revision will be related to a charm revision and also related
  to a specific rock OCI Image revision.
- **II Dependencies.** Rocks, as proper OCI-images, are immutable images that contain all dependencies.
  There is no explicit or implicit dependency on the rock on outside dependencies. The
  interface between the images, containers and the runtime is well established and standardized.
- **III Configuration is exposed as environment variables.** The 12-Factor project is very
  opinionated on the way of exposing configuration to the apps as environment variables. Each
  app will receive environment variables with names and values following the conventions of the specific
  web framework. The configuration for backing services provided by Juju relations is also exposed
  through environment variables.You can define the configuration with the Juju Provider for Terraform.
- **IV Backing services.** Backing services are managed by Juju and provided to the web app at runtime
  thanks to Juju relations.
- **V Build, release, run.** The 12-Factor project together with rocks and charms provide a clear boundary
  between the build stage and the release stage. Infrastructure as Code and GitOps best practices can
  be easily achieved using the Juju Terraform Provider.
- **VI Processes.** The processes that your rock runs should be stateless. It is the responsibility of the
  application developer to only use the backing services for data that must be persistent and not use the
  file system to store persistent data. Using stateless applications, horizontal scalability can be achieved
  increasing the number of units in a Juju application.
- **VII. Port binding.** The twelve-factor app is completely self-contained and should bind to a port.
  The 12-Factor project is specially designed for HTTP traffic, and integrations like ``ingress``
  will provide a ``routing layer`` to your application. SSL certificates can be added easily to your
  ``ingress`` provider with charms like the `Lego operator <https://charmhub.io/lego>`_.
- **VIII. Concurrency.** Juju applications can be easily scaled adding more units. This is possible thanks to
  the stateless and share-nothing approach that should be taken when developing 12-Factor applications.
- **IX. Disposability.** The twelve-factor app’s processes are disposable. This concept fits nicely in Kubernetes,
  that is the substrate used in Juju for the 12-Factor project. The application can be scaled and downscaled
  and the pods and containers can be restarted and recreated.
- **X. Development/production parity.** Juju facilitates the development/production parity, as very similar environments
  can be created using Juju tooling. It is also up to the good processes and practices to close the gap between
  development and production.
- **XI. Logs.** Taking advantage of `Pebble log forwarding <https://documentation.ubuntu.com/pebble/reference/log-forwarding/>`_
  and the `Canonical Observability Stack <https://documentation.ubuntu.com/observability/>`_, the 12-Factor project in
  Charmcraft and Rockcraft provides the best tools and practices in observability. Following the 12-Factor principle,
  the web apps just have to log to the standard Unix output streams.
- **XII. Admin processes.** The 12-Factor project already provides some functionality out of the box for certain one-off
  processes like migration scripts. Other management tasks can be cleanly defined in
  `Juju Actions <https://documentation.ubuntu.com/juju/3.6/reference/action/>`_.
