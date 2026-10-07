# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Bounded, read-only diagnostics for Loki fixture failures."""

import logging
import re
import shutil
import subprocess

logger = logging.getLogger(__name__)

_TOKEN_DIAGNOSTICS = """
import base64
import json
import os
import ssl
import sys
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

directory = Path("/var/run/secrets/kubernetes.io/serviceaccount")
path = directory / "token"
with path.open() as token_file:
    token = token_file.read().strip()
    stat = os.fstat(token_file.fileno())
payload = token.split(".")[1]
claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
print(json.dumps({
    "token_metadata": {key: claims.get(key) for key in ("iat", "nbf", "exp", "aud")},
    "token_inode": stat.st_ino,
    "token_mtime": stat.st_mtime,
    "observed_at": time.time(),
}), flush=True)
host = os.environ["KUBERNETES_SERVICE_HOST"]
port = os.environ.get("KUBERNETES_SERVICE_PORT_HTTPS", "443")
namespace, app_name = sys.argv[1:]
url = f"https://{host}:{port}/apis/apps/v1/namespaces/{namespace}/statefulsets/{app_name}"
request = Request(url, headers={"Authorization": "Bearer " + token})
try:
    with urlopen(request, context=ssl.create_default_context(cafile=directory / "ca.crt"),
                 timeout=5) as response:
        print(json.dumps({"mounted_token_api_status": response.status}))
except HTTPError as error:
    print(json.dumps({"mounted_token_api_status": error.code}))
"""


def _run(command: list[str], label: str) -> str | None:
    """Run a diagnostic command, reporting failures without exposing partial output."""
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True, timeout=15)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        # Partial command output may contain authentication material.
        logger.warning(
            "Loki diagnostics: %s unavailable (%s, exit=%s)",
            label,
            type(error).__name__,
            getattr(error, "returncode", None),
        )
        return None
    return result.stdout


def collect_loki_diagnostics(namespace: str, app_name: str) -> None:
    """Log Kubernetes state and token metadata when the Loki fixture fails.

    Commands are read-only and individually bounded. Pod environments, Secret objects,
    bearer tokens, and full JWT payloads are never logged. Diagnostic command failures
    are reported without replacing the original fixture failure.

    Args:
        namespace: Kubernetes namespace of the Juju model.
        app_name: Loki application name.
    """
    if shutil.which("k8s"):
        kubectl = ["sudo", "-n", "k8s", "kubectl"]
    elif shutil.which("microk8s"):
        kubectl = ["sudo", "-n", "microk8s", "kubectl"]
    else:
        kubectl = ["kubectl"]
    kubectl += ["--request-timeout=10s", "-n", namespace]
    logger.info("Loki diagnostics for %s/%s", namespace, app_name)
    for label, command in (
        ("Juju version", ["juju", "version"]),
        (
            "Kubernetes versions",
            [
                *kubectl,
                "get",
                "nodes",
                "-o",
                "custom-columns=NAME:.metadata.name,KUBELET:.status.nodeInfo.kubeletVersion",
            ],
        ),
        (
            "model RoleBindings",
            [
                *kubectl,
                "get",
                "rolebindings",
                "-o",
                "custom-columns=NAME:.metadata.name,ROLE:.roleRef.name,"
                "SUBJECT_KIND:.subjects[*].kind,SUBJECT_NAME:.subjects[*].name",
            ],
        ),
        (
            "Loki pod metadata",
            [
                *kubectl,
                "get",
                "pods",
                "-l",
                f"app.kubernetes.io/name={app_name}",
                "-o",
                "custom-columns=NAME:.metadata.name,UID:.metadata.uid,"
                "DELETING:.metadata.deletionTimestamp,"
                "GRACE:.metadata.deletionGracePeriodSeconds,"
                "REVISION:.metadata.labels.controller-revision-hash,"
                "NODE:.spec.nodeName,SA:.spec.serviceAccountName,"
                "PHASE:.status.phase,START:.status.startTime,"
                "READY:.status.containerStatuses[*].ready,"
                "RESTARTS:.status.containerStatuses[*].restartCount,"
                "TERMINATED:.status.containerStatuses[*].state.terminated.reason,"
                "EXIT:.status.containerStatuses[*].state.terminated.exitCode,"
                "TOKEN_EXPIRY:.spec.volumes[*].projected.sources[*]."
                "serviceAccountToken.expirationSeconds,"
                "TOKEN_AUDIENCE:.spec.volumes[*].projected.sources[*].serviceAccountToken.audience",
            ],
        ),
        (
            "Loki rollout metadata",
            [
                *kubectl,
                "get",
                "statefulsets",
                app_name,
                "-o",
                "custom-columns=NAME:.metadata.name,GENERATION:.metadata.generation,"
                "OBSERVED:.status.observedGeneration,STRATEGY:.spec.updateStrategy.type,"
                "CURRENT:.status.currentRevision,UPDATE:.status.updateRevision,"
                "READY:.status.readyReplicas,UPDATED:.status.updatedReplicas",
            ],
        ),
    ):
        result = _run(command, label)
        if result is not None:
            logger.info("%s:\n%s", label, result)
    output = _run(
        [*kubectl, "get", "pods", "-l", f"app.kubernetes.io/name={app_name}", "-o", "name"],
        "pod query",
    )
    if output is not None:
        pods = output.split()
        logger.info("Loki pod count: %d", len(pods))
        for pod in pods[:3]:
            pod_name = pod.removeprefix("pod/")
            events = _run(
                [
                    *kubectl,
                    "get",
                    "events",
                    "--field-selector",
                    f"involvedObject.name={pod_name},involvedObject.kind=Pod",
                    "--sort-by=.metadata.creationTimestamp",
                ],
                "pod events",
            )
            if events is not None:
                logger.info("Loki pod events:\n%s", events)
            metadata = _run(
                [
                    *kubectl,
                    "exec",
                    pod_name,
                    "-c",
                    "charm",
                    "--",
                    "python3",
                    "-c",
                    _TOKEN_DIAGNOSTICS,
                    namespace,
                    app_name,
                ],
                "mounted token metadata and authentication probe",
            )
            if metadata is not None:
                logger.info("Loki mounted token diagnostics:\n%s", metadata)
    authentication = _run(
        [
            "sudo",
            "-n",
            "journalctl",
            "--since=-10min",
            "--no-pager",
            "--grep=Unable to authenticate the request|invalid bearer token",
            "-n",
            "50",
        ],
        "API server authentication logs",
    )
    if authentication is not None:
        authentication = re.sub(
            r"\b[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]+\b",
            "<redacted JWT>",
            authentication,
        )
        logger.info("API server authentication logs:\n%s", authentication)
