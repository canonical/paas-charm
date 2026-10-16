# initial hello world Flask app

import flask

app = flask.Flask(__name__)


@app.route("/")
def index():
    return flask.Response("Hello world!", mimetype="text/plain")


if __name__ == "__main__":
    app.run()
