# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

import logging
import os
import socket
import time

from flask import Flask, g, jsonify, request

app = Flask(__name__)


@app.route("/")
def hello_world():
    return "Hello, World!"


@app.route("/sleep")
def sleep():
    duration_seconds = int(request.args.get("duration"))
    time.sleep(duration_seconds)
    return ""
