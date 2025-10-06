<!-- vale Canonical.007-Headings-sentence-case = NO -->

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Place any unreleased changes here, that are subject to release in coming versions :).

* feat: Add profiles configuration option to Spring Boot.
* fix: Fix bug in rabbitmq relation. When an application with units integrate with
       rabbitmq-server it can fail with RelationDataAccessError.

## 2025-10-01

* docs: Add link to Matrix channel in README.

## 2025-09-19

* docs: Update `paas-charm` v1.8 release notes to include Charmcraft updates.

## 2025-09-15

* docs: Add explanation document describing the value proposition of the tooling.

## 2025-09-11

* docs: Add explanation document describing the opinionated nature of the 12-factor tooling.

## 1.8.7 - 2025-09-10

* fix: Unintentional removal of trailing `/` character from redirect-path is fixed.
* docs: Refactor explanation documentation in the RTD site.
* docs: Add links to Spring Boot documentation.
* docs: Update RTD project to latest version of the starter pack.
* docs: Add release notes for `paas-charm v1.8`.
* fix: The ingress library doesn't properly handle pod restarts, and in some cases
  using the nginx-integrator charm, the IP field is not updated correctly.
  As a workaround, refresh the ingress relation data on every update-status hook.

## 1.8.6 - 2025-08-01

* feat: Add OIDC support for Express.

## 1.8.5 - 2025-08-01

* feat: Add OIDC support for Go.
* docs: Refactor how-to landing page.

## 1.8.4 - 2025-07-29

* feat: Add OIDC support for FastAPI.

## 1.8.3 - 2025-07-29

* feat: Add OIDC support for Spring Boot.

## 1.8.2 - 2025-07-28

* feat: Add OIDC support for Django.
* docs: Added "Supported customizable features and capabilities".

## 1.8.1 - 2025-07-25

* feat: add X-Request-ID header to Gunicorn logs if present in response.

## 1.8.0 - 2025-07-24

* feat: Add OIDC support for Flask.

## 2025-07-23

* docs: Added "How to add a new framework".

## 2025-07-21

* docs: Refactor reference documentation.

## 2025-07-17

* docs: Added release notes to the project.

## 2025-07-15

* feat: Spring Boot support for RabbitMQ.

## 2025-07-11

* docs: Refactored the RTD tutorial landing page.

## 1.7.9 - 2025-06-26

* feat: Added Prometheus support for Spring Boot.

## 1.7.8 - 2025-06-25

* feat: Added OpenFGA support for Spring Boot.

## 1.7.7 - 2025-06-25

* feat: Added Tracing support for Spring Boot.

## 1.7.6 - 2025-06-24

* feat: Added MySQL support for Spring Boot.

## 1.7.5 - 2025-06-20

* feat: Added MongoDB support for Spring Boot.

## 1.7.4 - 2025-06-20

* feat: Added S3 support for Spring Boot.

## 1.7.3 - 2025-06-17

* feat: Added Redis support for Spring boot.
* docs: Refactored the RTD home page. Moved content into Explanation.

## 1.7.2 - 2025-06-17

* feat: Added SAML support for Spring Boot.

## 1.7.1 - 2025-06-12

* docs: Added an edit button to the RTD project.
* feat: Added SMTP support for Spring Boot.

## 1.7.0 - 2025-06-11

* feat: Added support for Spring Boot.

## 1.6.0 - 2025-05-26

* feat: Added support for Express.

## v1.5.3 - 2025-05-08

* feat: Added support for 
[rootless charms](https://discourse.charmhub.io/t/juju-3-6-0-released/16027#rootless-charms-on-k8s-3).

## v1.5.2 - 2025-04-29

* fix: Properly update ingress integration and opened ports when 
  configuration changes.
* fix: Ensure Prometheus scraping information refreshes correctly on 
  configuration changes.
* docs: Updated README and contributing guide. Added links to Charmcraft and Rockcraft.

## v1.5.1 - 2025-04-24

* fix: Fix issue with `typehint` leading to errors due to missing import

## v1.5.0 - 2025-04-14

* feat: Added support for OpenFGA integration.

## v1.4.2 - 2025-04-24

* feat: Added peer(s) FQDN(s) as an environment variable

## v1.4.2 - 2025-04-03

* fix: Fixed a bug that occurred when users attempted to use [ args ] in service
  commands for the Django and Flask frameworks.

* fix: Updated broken doc links.

## v1.4.1 - 2025-03-26

* feat(docs): Add Google Analytics capabilities to RTD build.

## v1.4.1 - 2025-03.25

* fix: Added event handler for `secret_storage_relation_changed` 
  event.

## v1.4.0 - 2025-03-04

* feat: Added support for smtp integration.

## v1.3.2 - 2025-02-27

* chore: Changed workload container name to a constant value for the
  go-framework

## v1.3.0 - 2025-02-24

* feat: Added support for non-optional configuration options.

## v1.2.3 - 2025-02-07

* fix: Missing charm libraries at import time are now logged as a warning
  rather than an exception.

## v1.2.2 - 2025-02-07

* fix: Removed `__init__.py` file for templates and included the Jinja templates
  in the `package-data` in `pyproject.toml`.

## v1.2.1 - 2025-02-07

* fix: Added an init file to fix `missing templates folder` issue in the pypi
  package.

## v1.2.0 - 2025-02-06

* docs: Updated the home page for the Read the Docs site to align closer to the
  standard model for Canonical products.

## v1.2.0 - 2025-02-06

* feat: Added support for tracing web applications using an integration with
  [Charmed Tempo HA](https://charmhub.io/topics/charmed-tempo-ha).

## v1.1.0 - 2024-12-19

* docs: Updated the home page for the Read the Docs site to provide relevant
  information about the project.

* feat: Added support for async workers for Gunicorn services (flask and Django).

## v1.0.0 - 2024-11-29

* docs: Added a `docs` folder to hold the
  [Canonical Sphinx starter pack](https://github.com/canonical/sphinx-docs-starter-pack)
  and to eventually publish the docs on Read the Docs.
