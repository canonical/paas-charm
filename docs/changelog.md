# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Place any unreleased changes here, that are subject to release in coming versions :).

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
