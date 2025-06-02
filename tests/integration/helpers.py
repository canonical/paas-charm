# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

import io
import json
import logging
import os
import pathlib
import uuid
import zipfile

import requests
import yaml
from tenacity import retry, stop_after_attempt, wait_exponential, wait_fixed

logger = logging.getLogger(__name__)


def inject_venv(charm: pathlib.Path | str, src: pathlib.Path | str):
    """Inject a Python library into the charm venv directory inside a charm file."""
    with zipfile.ZipFile(charm, "a") as zip_file:
        src = pathlib.Path(src)
        if not src.exists():
            raise FileNotFoundError(f"Python library {src} not found")
        for file in src.rglob("*"):
            if "__pycache__" in str(file):
                continue
            rel_path = file.relative_to(src.parent)
            zip_file.write(file, os.path.join("venv/", rel_path))


def inject_charm_config(charm: pathlib.Path | str, charm_dict: dict, tmp_dir: pathlib.Path) -> str:
    """Inject some charm configurations into the correct yaml file in a packed charm file."""
    config_dict = charm_dict.get("config", {})
    action_dict = charm_dict.get("actions", {})
    metadata_dict = {k: v for k, v in charm_dict.items() if k not in ["config", "actions"]}
    charm_zip = zipfile.ZipFile(charm, "r")
    with charm_zip.open("config.yaml") as file:
        charm_config = yaml.safe_load(file)
    with charm_zip.open("metadata.yaml") as file:
        charm_metadata = yaml.safe_load(file)
    with charm_zip.open("actions.yaml") as file:
        charm_actions = yaml.safe_load(file)
    charm_config.setdefault("options", {}).update(config_dict.get("options", {}))
    charm_metadata.update(metadata_dict)
    charm_actions.update(action_dict)
    modified_config = yaml.safe_dump(charm_config)
    modified_metadata = yaml.safe_dump(charm_metadata)
    modified_actions = yaml.safe_dump(charm_actions)
    new_charm = io.BytesIO()
    with zipfile.ZipFile(new_charm, "w") as new_charm_zip:
        for item in charm_zip.infolist():
            if item.filename == "config.yaml":
                new_charm_zip.writestr(item, modified_config)
            elif item.filename == "metadata.yaml":
                new_charm_zip.writestr(item, modified_metadata)
            elif item.filename == "actions.yaml":
                new_charm_zip.writestr(item, modified_actions)
            else:
                with charm_zip.open(item) as file:
                    data = file.read()
                new_charm_zip.writestr(item, data)
    charm_zip.close()
    charm = (tmp_dir / f"{uuid.uuid4()}.charm").absolute()
    with open(charm, "wb") as new_charm_file:
        new_charm_file.write(new_charm.getvalue())
    return str(charm)


def get_traces(tempo_host: str, service_name: str):
    """Get traces directly from Tempo REST API."""
    url = f"http://{tempo_host}:3200/api/search?tags=service.name={service_name}"
    logger.info("url to get traces from: %s", url)
    req = requests.get(
        url,
        verify=False,
    )
    assert req.status_code == 200
    traces = json.loads(req.text)["traces"]
    return traces


@retry(stop=stop_after_attempt(15), wait=wait_exponential(multiplier=1.5, min=4, max=10))
def get_traces_patiently(tempo_host: str, service_name: str):
    """Get traces directly from Tempo REST API, but also try multiple times.

    Useful for cases when Tempo might not return the traces immediately (its API is known for returning data in
    random order).
    """
    traces = get_traces(tempo_host, service_name=service_name)
    assert len(traces) > 0
    return traces


@retry(stop=stop_after_attempt(5), wait=wait_fixed(5))
def get_mails_patiently(mailcatcher_pod_ip: str):
    """Get mails directly from Mailcatcher REST API, but also try multiple times."""
    url = f"http://{mailcatcher_pod_ip}:1080/messages"
    req = requests.get(
        url,
        timeout=5,
        verify=False,
    )
    assert req.status_code == 200
    mails = req.json()
    assert len(mails) > 0
    return mails


@retry(stop=stop_after_attempt(5), wait=wait_fixed(5))
def check_grafana_datasource_types_patiently(
    grafana_session: requests.session,
    grafana_ip: str,
    expected_datasource_types: list[str],
):
    """Get datasources directly from Grafana REST API, but also try multiple times."""
    url = f"http://{grafana_ip}:3000/api/datasources"
    datasources = grafana_session.get(url, timeout=10).json()
    datasource_types = set(datasource["type"] for datasource in datasources)
    for datasource in expected_datasource_types:
        assert datasource in datasource_types, f"Datasource type {datasource} not found in Grafana"


@retry(stop=stop_after_attempt(5), wait=wait_fixed(15))
def check_grafana_dashboards_patiently(
    grafana_session: requests.session, grafana_ip: str, dashboard: str
):
    """Check if dashboard can be found in Grafana directly from Grafana REST API,
    but also try multiple times."""
    dashboards = grafana_session.get(
        f"http://{grafana_ip}:3000/api/search",
        timeout=10,
        params={"query": dashboard},
    ).json()
    assert len(dashboards)


@retry(stop=stop_after_attempt(5), wait=wait_fixed(15))
def check_openfga_auth_models_patiently(unit_ip: str, port: int):
    """Check if authorization models can be listed in OpenFGA directly from OpenFGA REST API,
    but also try multiple times."""
    response = requests.get(
        f"http://{unit_ip}:{port}/openfga/list-authorization-models", timeout=5
    )
    assert "Listed authorization models" in response.text
    assert response.status_code == 200
