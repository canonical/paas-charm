.. _explanation_full_lifecycle:

How everything connects (source to production)
==============================================

The 12-Factor app support in Charmcraft and Rockcraft is an opinionated
framework based on the 12-Factor methodology. If you web app uses one of the
supported framework and follows the conventions of the tool, you can
easily containerize, charm, and deploy it with Juju.

.. vale off

.. mermaid::

    flowchart TD
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

We recommend to put the Rockcraft project file (``rockcraft.yaml``) in the same
repository as your code, created with the
:ref:`Rockcraft extension <rockcraft:reference-extensions>`
for your specific framework. The rock generated with this project file
is a fully compliant OCI-image that can be used outside of the Juju ecosystem.

Your web app containerized in a rock will be managed by a charm, a software
operator orchestrated by Juju. You can create the charm using the
:doc:`init profile <charmcraft:reference/commands/init>`,
that will use the appropriate
:ref:`Charmcraft extension <charmcraft:extensions>`.
We recommend to place the charm code inside the ``charm`` directory in the same repository
as your code.

The 12-Factor app support in Charmcraft and Rockcraft does not enforce any
specific CI/CD pipeline. Some recommendations and useful tools are:

- For the build stage, the ``rockcraft`` and ``charmcraft`` tools are used to create the rock and charm artifacts.
- For integration tests involving charms, use the `Jubilant <https://github.com/canonical/jubilant>`_ library.
- `concierge <https://github.com/canonical/concierge>`_ is an opinionated utility to provision testing machines.
- Charmcraft's :doc:`test command <charmcraft:reference/commands/test>`, based
  on `Spread <https://github.com/canonical/spread>`_ is a convenient full-system test (task) distribution.
- Once your artifacts are ready, they can be
  :doc:`uploaded to Charmhub <charmcraft:reference/commands/upload>` and
  :doc:`promoted <charmcraft:reference/commands/release>` to the
  desired :ref:`channel <charmcraft:manage-channels>`. 
  This is not a mandatory step, as you can deploy charms locally without Charmhub.
- For the deployment, the current recommendation is to use the
  `Juju Terraform Provider <https://registry.terraform.io/providers/juju/juju/latest/docs>`_.

Juju is the engine that will orchestrate the software operators.
The Juju ecosystem provides a multitude of `curated software operators <https://charmhub.io/>`_
for your observability stack, database, SSO, and many more and allows their deployment and
lifecycle management on metal, on VMs, on K8s and on cloud providers
(see :ref:`substrates <juju:kubernetes-clouds-and-juju>`).

Your web app will be able to integrate seamlessly with other charms, that can be running in
Kubernetes or in Machines, and on-premises or in the cloud.

For the operation of your applications, it is strongly recommended to use the 
`Canonical Observability Stack <https://charmhub.io/cos-lite>`_, an
out-of-the-box solution for improved day-2 operational insight.
