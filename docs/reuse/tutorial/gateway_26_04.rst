Copy the complete ``url`` for your application, not the
``gateway-api-integrator`` entry. The example address will differ on your VM.
The app URL already includes its routing prefix; the gateway strips this prefix
before forwarding requests to the app.

In the VM terminal, save that URL for the following commands, replacing
``<app-url>`` with the value returned by the action:

.. code-block:: bash

    export APP_URL='<app-url>'

Use the same complete URL directly in a browser on your host machine. No DNS
entry or custom Host header is needed. ``APP_URL`` exists only in the VM
terminal where you exported it; repeat the export with the same returned URL
if you open another VM terminal. If the gateway address changes, run the action
again and update ``APP_URL``.
