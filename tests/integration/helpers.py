# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

import io
import json
import os
import pathlib
import uuid
import zipfile

import requests
import yaml
from tenacity import retry, stop_after_attempt, wait_exponential


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


def inject_charm_config(charm: pathlib.Path | str, config: dict, tmp_dir: pathlib.Path) -> str:
    """Inject some charm configurations into the config.yaml in a packed charm file."""
    charm_zip = zipfile.ZipFile(charm, "r")
    with charm_zip.open("config.yaml") as file:
        charm_config = yaml.safe_load(file)
    charm_config["options"].update(config)
    modified_config = yaml.safe_dump(charm_config)
    new_charm = io.BytesIO()
    with zipfile.ZipFile(new_charm, "w") as new_charm_zip:
        for item in charm_zip.infolist():
            if item.filename == "config.yaml":
                new_charm_zip.writestr(item, modified_config)
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
    req = requests.get(
        url,
        verify=False,
    )
    assert req.status_code == 200
    traces = json.loads(req.text)["traces"]
    return traces


@retry(stop=stop_after_attempt(15), wait=wait_exponential(multiplier=1, min=4, max=10))
async def get_traces_patiently(tempo_host, service_name="tracegen-otlp_http"):
    """Get traces directly from Tempo REST API, but also try multiple times.

    Useful for cases when Tempo might not return the traces immediately (its API is known for returning data in
    random order).
    """
    traces = get_traces(tempo_host, service_name=service_name)
    assert len(traces) > 0
    return traces
