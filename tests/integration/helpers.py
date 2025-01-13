# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

import io
import os
import pathlib
import uuid
import zipfile

import yaml


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
