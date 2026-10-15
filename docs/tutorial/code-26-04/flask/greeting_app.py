# Flask app with a greeting configuration

import os

import flask

app = flask.Flask(__name__)
app.config.from_prefixed_env()


@app.route("/")
def index():
    greeting = os.getenv("GREETING_VAR", "Hello, world!")
    return f"{greeting}\n"


if __name__ == "__main__":
    app.run()
