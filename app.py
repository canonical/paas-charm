from flask import Flask
import time

app = Flask(__name__)


@app.route("/")
def index():
    return "Hello, world!"

@app.route("/io")
def io_bound_task():
    start_time = time.time()
    time.sleep(2)
    duration = time.time() - start_time
    return f"I/O task completed in {round(duration, 2)} seconds"
