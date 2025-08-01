How 12-Factor app principles are applied in rocks and charms
============================================================

The 12-Factor app principles offer several advantages when combined
with modern cloud platforms.

The following 12-Factor principles are specially relevant in the
context of rocks and charms:

 - I Codebase. Already achieved with rocks (OCI compliant images) and charms. The repository will create a rock and a charm that will be deployed in many environments.
 - II Dependencies. Already achieved with rocks (OCI compliant images).
 - III Configuration is exposed as environment variables. Besides that, environment variables are homogeneous between different charms and well documented. Besides the environment variables provided by each framework and the integrations, the charm author can define new environment variables that will seamlessly integrate with the application developed.
 - IV Backing services. Backing services are provided by Juju relations. That way, not only the 12-Factor app can be deployed with Juju, but also all the backing services, that will be operated by the charms in an automated way. TODO something better written.
 - V Build, release, run. The 12-Factor project together with rocks and charms provide a clear boundary between build stage and the run stage. Using gitops with terraform using the juju terraform provider you can combine the charm and the configuration in a "release", facilitating launching specific configurations.
 - VI Processes. The processes that your rock runs should be stateless. It is the responsability of the application developer to only use the backing services for data that must be persistent.
 - VII. Port binding. The 12-Factor application should bind to a port. The 12-Factor project is specially designed for HTTP traffic, and integrations like ``ingress`` will provide a ``routing layer`` to your application.
 - VIII. Concurrency. Juju applications can be easily scaled adding more units. This is possible thanks to the stateless and share-nothing approach that should be taken when developing 12-Factor applications.
 - IX. Disposability. TODO
 - X. Dev/prod parity. TODO
 - XI. Logs. TODO
 - XII. Admin processes. TODO
