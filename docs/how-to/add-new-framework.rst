.. _how_to_add_new_framework:

How to add a new framework
==========================

This guide describes the process for adding a new framework to ``paas-charm``
and the corresponding support in Rockcraft and Charmcraft.

Describe use case
-----------------

Reach out to us on `Matrix <https://matrix.to/#/#12-factor-charms:ubuntu.com>`_
with your use case and need. So we can understand the full context, it's helpful
if you have a working app that demonstrates your use case.
We then determine whether the 12-factor tooling is an appropriate solution and
will meet the requirements of your use case. During this stage, we conduct a
thorough evaluation to understand the time requirements, priority, and whether
your use case fits into the 12-factor story.

Work into roadmap
-----------------

Before any development begins, we must add the work into our official roadmap.
During routine roadmap planning, we further evaluate your use case, stakeholders,
and relevant needs. If approved, the framework development
and implementation is added to upcoming cycles in our roadmap.

Develop
-------

Once the work is added to our official roadmap, we can begin developing the
new framework. Your role now shifts from *requester* to *stakeholder*, where you
will attend meetings, review and approve any functional specifications, and
provide your input on  the user experience, features, framework assumptions,
processes, and practices.

Implement
---------

The implementation process has a three-staged approach, where implementing the
Rockcraft support always occurs first. The support in ``paas-charm`` and Charmcraft can
be worked on simultaneously, and the order of their implementation can alternate.

Once the implementation happens, the initial framework support will be behind
an experimental flag. This flag is removed only after significant
testing has occurred and we have a production-ready deployment. 
After the experimental flag is removed, no breaking changes will be allowed for
the framework until the next ``paas-charm`` LTS release.

Add more features
-----------------

If you require additional features in the framework, determine whether the features
need to be added to ``pass-charm``, Rockcraft, or Charmcraft.
Follow the :ref:`contributing guide <how_to_contribute>` for ``paas-charm`` or the contributing
guides in `Rockcraft <https://github.com/canonical/rockcraft/blob/main/CONTRIBUTING.rst>`_
and `Charmcraft <https://github.com/canonical/charmcraft/blob/main/CONTRIBUTING.md>`_.

