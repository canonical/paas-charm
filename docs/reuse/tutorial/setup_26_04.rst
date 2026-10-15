First, :external+multipass:ref:`install Multipass <how-to-guides-install-multipass>`.
Launch an Ubuntu 26.04 VM named ``charm-dev``:

.. code-block:: bash

    multipass launch --cpus 4 --disk 50G --memory 8G --name charm-dev 26.04
    multipass shell charm-dev

Unless stated otherwise, work entirely within the VM from now on.

Install Rockcraft and Charmcraft
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Ubuntu 26.04 extensions require the edge releases of Rockcraft and Charmcraft.
Install both tools with classic confinement:

.. code-block:: bash

    sudo snap install rockcraft --channel latest/edge --classic
    sudo snap install charmcraft --channel latest/edge --classic

Install LXD, Canonical Kubernetes, and Juju
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

LXD provides the build environment for the rock and charm. If it isn't installed,
install it with ``sudo snap install lxd``. Initialize it:

.. code-block:: bash

    lxd init --auto

Canonical Kubernetes will host the |12FactorApp| app and PostgreSQL.
Install the Kubernetes and Juju snaps:

.. code-block:: bash

    sudo snap install k8s --channel 1.34-classic/stable --classic
    sudo snap install juju --channel 3.6/stable

Bootstrap a single-node cluster and enable local storage and Gateway API:

.. literalinclude:: /reuse/tutorial/bootstrap_26_04.sh
    :language: bash
    :start-after: [docs:bootstrap-k8s]
    :end-before: [docs:bootstrap-k8s-end]

The ``--wait-ready`` option waits for the cluster to become ready.
Local storage supplies the volumes needed by Juju, PostgreSQL, and the image registry.
Gateway API supplies the ingress controller used later in the tutorial.

Configure the load balancer to use the VM's address, so the app will be
accessible from outside the VM. In a separate terminal on your host, find the
VM's IPv4 address:

.. code-block:: bash

    multipass info charm-dev

Return to the VM terminal and enable the load balancer:

.. literalinclude:: /reuse/tutorial/bootstrap_26_04.sh
    :language: bash
    :start-after: [docs:enable-load-balancer]
    :end-before: [docs:enable-load-balancer-end]

Set its address range, replacing ``<VM_IP>`` with that IPv4 address:

.. code-block:: bash

    sudo k8s set load-balancer.cidrs="<VM_IP>/32"

Use the same address in place of ``<VM_IP>`` in the later ``curl`` commands.
Keep the quotes around the placeholder when replacing it.

Create a local image registry
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Canonical Kubernetes doesn't include a registry addon. We'll deploy an OCI
registry in the cluster to store the rocks built during this tutorial.
Download the registry manifest from the ``paas-charm`` repository:

.. code-block:: bash

    curl --fail --location --output registry.yaml \
      https://raw.githubusercontent.com/canonical/paas-charm/main/docs/reuse/tutorial/registry_26_04.yaml

Apply the downloaded ``registry.yaml`` and wait for the registry to be ready:

.. literalinclude:: /reuse/tutorial/bootstrap_26_04.sh
    :language: bash
    :start-after: [docs:deploy-registry]
    :end-before: [docs:deploy-registry-end]

Access the registry at ``localhost:32000`` from within the VM.
It uses a persistent volume so its images survive pod restarts.
The NodePort service also exposes port 32000 on the VM's network interfaces.

Bootstrap Juju
~~~~~~~~~~~~~~~

Register Canonical Kubernetes as a Juju cloud, then bootstrap the development
controller:

.. literalinclude:: /reuse/tutorial/bootstrap_26_04.sh
    :language: bash
    :start-after: [docs:bootstrap-juju]
    :end-before: [docs:bootstrap-juju-end]

It can take a few minutes to download the controller images.
