# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

import os

from flask import Flask, jsonify

app = Flask(__name__)
app.config.from_prefixed_env()


@app.route("/")
def hello_world():
    return "Hello, World!"


@app.route("/config/<config_name>")
def config(config_name: str):
    return jsonify(app.config.get(config_name))


@app.route("/env")
def get_env():
    """Return environment variables"""
    return jsonify(dict(os.environ))
