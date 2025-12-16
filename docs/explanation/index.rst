.. Copyright 2025 Canonical Ltd.
.. See LICENSE file for licensing details.

.. _explanation:

Explanation
===========

The following explanations provide context and clarification on key topics related to the use and
configuration of web app frameworks.

12-factor app principles
------------------------

The glue point of the 12-factor framework support in Rockcraft and Charmcraft is
the `12-factor methodology <https://12factor.net/>`_. The 12-Factor methodology
is a set of best practices for building modern, scalable, and maintainable web
applications. By following these principles, you can easily create a rock
(OCI image) and a charm (software operator) for your web app that can take
advantage of the full Juju ecosystem.

Learn more about the components involved and how the principles are applied in
the following pages:

* :ref:`Juju, charms and rocks <explanation_foundations>`: Descriptions of
  the Canonical products involved. 
* :ref:`How the 12-factor principles are applied in rocks and charms <explanation_12_factor_principles_applied>`: 
  An overview on how the 12-factor methodology is applied to rocks and charms.

12-factor ecosystem
-------------------

The native 12-factor framework support in Rockcraft and Charmcraft provides an
opinionated way to easily integrate your web application into the Juju ecosystem.
The Juju ecosystem provides a multitude of `curated software operators <https://charmhub.io/>`_
for your observability stack, database, SSO, and many more and allows their deployment and
lifecycle management on metal, on VMs, on K8s and on cloud providers
(see :ref:`substrates <juju:kubernetes-clouds-and-juju>`).

That way, the 12-factor framework support in Rockcraft and Charmcraft offers
a fully fledged Platform as a Service that streamlines managing the
infrastructure, whether on premises or on cloud, at any scale, and allows developers
to focus on their core competences instead of a complex software stack.

* :ref:`How everything connects <explanation_full_lifecycle>`: An overview of how the
  various components come together to form the 12-factor ecosystem.
* :ref:`Web app framework <explanation_web_app_frameworks>`: More details about the
  supported web app frameworks.
* :ref:`Why use the 12-factor support <explanation_why_use_12_factor>`: A summary of the
  advantages of using the native support in Charmcraft and Rockcraft.
* :ref:`Opinionated nature of the 12-factor tooling <explanation_opinionated_nature>`:
  Description of how the 12-factor tooling is opinionated and when those opinions can be
  overridden by users.

12-factor app charm
-------------------

The software operator built with Charmcraft containerizes the web app workload so that
you can deploy, configure, and integrate your web app in the Juju ecosystem. The following
page provides an overview of the architecture, components, and source code.

* :ref:`Charm architecture <explanation_charm_architecture>`

Development and operations
--------------------------

.. vale off

.. mermaid::

    flowchart LR
    %% -- Styling Classes --
    classDef nodeBox fill:#fff,stroke:#666,stroke-width:2px,color:#333,rx:5,ry:5,text-align:center;
    classDef groupContainer fill:none,stroke:#7c4dff,stroke-width:2px,stroke-dasharray: 5 5,color:#333,font-size:12px;
    
    %% -- Main Flow Styling --
    linkStyle default stroke:#7c4dff,stroke-width:2px,fill:none;

    %% -- Phase 1 --
    subgraph P1 ["CODE"]
        direction TB
        Node1["Source:<br/>12-factor web app"]:::nodeBox
    end

    %% -- Phase 2 --
    subgraph P2 ["BUILD + TEST"]
        direction TB
        Node2["Container:<br/>12-factor app rock"]:::nodeBox
        Node3["Software operator:<br/>12-factor app charm"]:::nodeBox
    end

    %% -- Phase 3 --
    subgraph P3 ["RELEASE"]
        direction TB
        Node4["Published:<br/>12-factor app rock<br/>and charm in the<br/>Charmhub store"]:::nodeBox
    end

    %% -- Phase 4 --
    subgraph P4 ["DEPLOY + OPERATE"]
        direction LR
        Node5["Production:<br/>12-factor app deployed<br/>to end users"]:::nodeBox
        Node6["Day 1 Operations:<br/>Integrate with database, ingress, SSO, etc."]:::nodeBox
        
        %% Internal Link (Grey)
        Node5 --> Node6
    end

    %% -- Phase 5 --
    subgraph P5 ["MONITOR"]
        direction TB
        Node7["Observe: <br/> Track and monitor<br/>with COS"]:::nodeBox
    end

    %% -- Connections --
    %% Connect Source to the first item in Build
    Node1 --> Node2
    Node1 --> Node3
    
    %% Connect both Build items to Release
    Node2 --> Node4
    Node3 --> Node4
    
    %% Connect Release to Deploy
    Node4 --> Node5
    
    %% Connect Deploy to Monitor
    Node6 --> Node7

    %% -- Apply Group Styles --
    class P1,P2,P3,P4,P5 groupContainer

.. vale on

The diagram above shows the 12-factor tooling in the context of the development
and operations lifecycle. The developer creates the app, uses Rockcraft and Charmcraft
to build a container image and software operator, publishes the contents to the
`Charmhub store <https://charmhub.io/>`_, and deploys the app to a Kubernetes cloud
using Juju. The charming ecosystem provides everything needed for operating the charm,
including databases, ingresses, and more. 

.. toctree::
   :maxdepth: 1
   :numbered:
   :hidden:

   Juju, charms and rocks <foundations>
   How the 12-factor principles are applied in rocks and charms <how-are-12-factor-principles-applied>
   The 12-factor ecosystem <full-lifecycle>
   Web app framework <web-app-framework>
   Why use 12-factor? <why-12-factor>
   Opinionated nature of the tooling <opinionated-nature-tooling>
   Charm architecture <charm-architecture>
