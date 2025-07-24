# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

import json
import logging
import os
import socket
import time
import urllib.parse
from urllib.parse import urlparse

import boto3
import botocore.config
import pika
import psycopg
import pymongo
import pymongo.database
import pymysql
import redis
import urllib3
from authlib.integrations.flask_client import OAuth
from celery import Celery, Task
from flask import Flask, g, jsonify, redirect, render_template, request, session, url_for
from flask_mail import Mail, Message
from openfga_sdk import ClientConfiguration
from openfga_sdk.credentials import CredentialConfiguration, Credentials
from openfga_sdk.sync import OpenFgaClient
from opentelemetry import trace
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from werkzeug.middleware.proxy_fix import ProxyFix


def hostname():
    """Get the hostname of the current machine."""
    return socket.gethostbyname(socket.gethostname())


def celery_init_app(app: Flask, broker_url: str) -> Celery:
    """Initialise celery using the redis connection string.

    See https://flask.palletsprojects.com/en/3.0.x/patterns/celery/#integrate-celery-with-flask.
    """

    class FlaskTask(Task):
        def __call__(self, *args: object, **kwargs: object) -> object:
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app = Celery(app.name, task_cls=FlaskTask)
    celery_app.set_default()
    app.extensions["celery"] = celery_app
    app.config.from_mapping(
        CELERY=dict(
            broker_url=broker_url,
            result_backend=broker_url,
            task_ignore_result=True,
        ),
    )
    celery_app.config_from_object(app.config["CELERY"])
    return celery_app


def init_smtp(app: Flask) -> bool:
    if os.environ.get("SMTP_HOST"):
        app.config["MAIL_SERVER"] = os.environ.get("SMTP_HOST")
        app.config["MAIL_PORT"] = os.environ.get("SMTP_PORT")
        app.config["MAIL_USERNAME"] = (
            f'{os.environ.get("SMTP_USER")}@{os.environ.get("SMTP_DOMAIN")}'
        )
        app.config["MAIL_PASSWORD"] = os.environ.get("SMTP_PASSWORD")
        app.config["MAIL_USE_TLS"] = (
            True if os.environ.get("SMTP_TRANSPORT_SECURITY") == "tls" else False
        )
        app.config["MAIL_USE_SSL"] = (
            True
            if os.environ.get("SMTP_TRANSPORT_SECURITY") == "starttls"
            and os.environ.get("SMTP_SKIPSSL_VERIFY") == "false"
            else False
        )
        return True
    return False


app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

app.config.from_prefixed_env()
mail = Mail(app) if init_smtp(app) else None

app.secret_key = os.getenv("FLASK_SECRET_KEY")
oauth = OAuth(app)

oauth.register(
    name="oidc",
    # We are doing this to avoid SSL verification issues in tests.
    # If you don't need to disable SSL verification, no need to set `client_kwargs`,
    # It will be read from FLASK_OIDC_CLIENT_KWARGS env argument automatically.
    client_kwargs={**json.loads(os.getenv("FLASK_OIDC_CLIENT_KWARGS", "{}")), "verify": False},
    jwks_uri=os.getenv("FLASK_OIDC_JWKS_URL"),
)

broker_url = os.environ.get("REDIS_DB_CONNECT_STRING")
# Configure Celery only if Redis is configured
celery_app = celery_init_app(app, broker_url)
redis_client = redis.Redis.from_url(broker_url) if broker_url else None

FlaskInstrumentor().instrument_app(app)
tracer = trace.get_tracer(__name__)


def fib_slow(n):
    if n <= 1:
        return n
    return fib_slow(n - 1) + fib_fast(n - 2)


def fib_fast(n):
    nth_fib = [0] * (n + 2)
    nth_fib[1] = 1
    for i in range(2, n + 1):
        nth_fib[i] = nth_fib[i - 1] + nth_fib[i - 2]
    return nth_fib[n]


@app.route("/fibonacci")
def fibonacci():
    n = int(request.args.get("n", 1))
    with tracer.start_as_current_span("root"):
        with tracer.start_as_current_span("fib_slow") as slow_span:
            answer = fib_slow(n)
            slow_span.set_attribute("n", n)
            slow_span.set_attribute("nth_fibonacci", answer)
        with tracer.start_as_current_span("fib_fast") as fast_span:
            answer = fib_fast(n)
            fast_span.set_attribute("n", n)
            fast_span.set_attribute("nth_fibonacci", answer)

    return f"F({n}) is: ({answer})"


@app.route("/send_mail")
def send_mail():
    if mail:
        msg = Message("hello", sender="tester@example.com", recipients=["test@example.com"])
        msg.body = "Hello world!"
        mail.send(msg)
        return "Sent"
    return "Mail not configured correctly"


@app.route("/profile")
def profile():
    user = session.get("user")
    return render_template("profile.html", user=user)


@app.route("/login")
def login():
    return oauth.oidc.authorize_redirect(url_for("callback", _external=True))


@app.route(os.getenv("FLASK_OIDC_REDIRECT_PATH", "/callback"))
def callback():
    token = oauth.oidc.authorize_access_token()

    # Store the user information and the id_token for logout
    session["user"] = token.get("userinfo")
    session["id_token"] = token.get("id_token")
    return redirect(url_for("profile"))


@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("hello_world"))


@app.route("/openfga/list-authorization-models")
def list_authorization_models():
    try:
        configuration = ClientConfiguration(
            api_url=os.environ["FGA_HTTP_API_URL"],
            store_id=os.environ["FGA_STORE_ID"],
            credentials=Credentials(
                method="api_token",
                configuration=CredentialConfiguration(api_token=os.environ["FGA_TOKEN"]),
            ),
        )
        fga_client = OpenFgaClient(configuration)
        fga_client.read_authorization_models()
        return "Listed authorization models"
    except urllib3.exceptions.HTTPError as e:
        return f"Failed reaching OpenFGA server: {e}"
    except Exception as e:
        return f"Failed to list authorization models: {e}"


@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """Set up periodic tasks in the scheduler."""
    try:
        # This will only have an effect in the beat scheduler.
        sender.add_periodic_task(0.5, scheduled_task.s(hostname()), name="every 0.5s")
    except NameError as e:
        logging.exception("Failed to configure the periodic task")


@celery_app.task
def scheduled_task(scheduler_hostname):
    """Function to run a schedule task in a worker.

    The worker that will run this task will add the scheduler hostname argument
    to the "schedulers" set in Redis, and the worker's hostname to the "workers"
    set in Redis.
    """
    worker_hostname = hostname()
    logging.info(
        "scheduler host received %s in worker host %s", scheduler_hostname, worker_hostname
    )
    redis_client.sadd("schedulers", scheduler_hostname)
    redis_client.sadd("workers", worker_hostname)
    logging.info("schedulers: %s", redis_client.smembers("schedulers"))
    logging.info("workers: %s", redis_client.smembers("workers"))
    # The goal is to have all workers busy in all processes.
    # For that it maybe necessary to exhaust all workers, but not to get the pending tasks
    # too big, so all schedulers can manage to run their scheduled tasks.
    # Celery prefetches tasks, and if they cannot be run they are put in reserved.
    # If all processes have tasks in reserved, this task will finish immediately to not make
    # queues any longer.
    inspect_obj = celery_app.control.inspect()
    reserved_sizes = [len(tasks) for tasks in inspect_obj.reserved().values()]
    logging.info("number of reserved tasks %s", reserved_sizes)
    delay = 0 if min(reserved_sizes) > 0 else 5
    time.sleep(delay)


def get_mysql_database():
    """Get the mysql db connection."""
    if "mysql_db" not in g:
        if "MYSQL_DB_CONNECT_STRING" in os.environ:
            uri_parts = urlparse(os.environ["MYSQL_DB_CONNECT_STRING"])
            g.mysql_db = pymysql.connect(
                host=uri_parts.hostname,
                user=uri_parts.username,
                password=uri_parts.password,
                database=uri_parts.path[1:],
                port=uri_parts.port,
            )
        else:
            return None
    return g.mysql_db


def get_postgresql_database():
    """Get the postgresql db connection."""
    if "postgresql_db" not in g:
        if "POSTGRESQL_DB_CONNECT_STRING" in os.environ:
            g.postgresql_db = psycopg.connect(
                conninfo=os.environ["POSTGRESQL_DB_CONNECT_STRING"],
            )
        else:
            return None
    return g.postgresql_db


def get_mongodb_database() -> pymongo.database.Database | None:
    """Get the mongodb db connection."""
    if "mongodb_db" not in g:
        if "MONGODB_DB_CONNECT_STRING" in os.environ:
            uri = os.environ["MONGODB_DB_CONNECT_STRING"]
            client = pymongo.MongoClient(uri)
            db = urllib.parse.urlparse(uri).path.removeprefix("/")
            g.mongodb_db = client.get_database(db)
        else:
            return None
    return g.mongodb_db


def get_redis_database() -> redis.Redis | None:
    if "redis_db" not in g:
        if "REDIS_DB_CONNECT_STRING" in os.environ:
            uri = os.environ["REDIS_DB_CONNECT_STRING"]
            g.redis_db = redis.Redis.from_url(uri)
        else:
            return None
    return g.redis_db


def get_rabbitmq_connection() -> pika.BlockingConnection | None:
    """Get rabbitmq connection."""
    if "rabbitmq" not in g:
        if "RABBITMQ_HOSTNAME" in os.environ:
            username = os.environ["RABBITMQ_USERNAME"]
            password = os.environ["RABBITMQ_PASSWORD"]
            hostname = os.environ["RABBITMQ_HOSTNAME"]
            vhost = os.environ["RABBITMQ_VHOST"]
            port = os.environ["RABBITMQ_PORT"]
            credentials = pika.PlainCredentials(username, password)
            parameters = pika.ConnectionParameters(hostname, port, vhost, credentials)
            g.rabbitmq = pika.BlockingConnection(parameters)
        else:
            return None
    return g.rabbitmq


def get_rabbitmq_connection_from_uri() -> pika.BlockingConnection | None:
    """Get rabbitmq connection from uri."""
    if "rabbitmq_from_uri" not in g:
        if "RABBITMQ_CONNECT_STRING" in os.environ:
            uri = os.environ["RABBITMQ_CONNECT_STRING"]
            parameters = pika.URLParameters(uri)
            g.rabbitmq_from_uri = pika.BlockingConnection(parameters)
        else:
            return None
    return g.rabbitmq_from_uri


def get_boto3_client():
    if "boto3_client" not in g:
        if "S3_ACCESS_KEY" in os.environ:
            s3_client_config = botocore.config.Config(
                s3={
                    "addressing_style": os.environ["S3_ADDRESSING_STYLE"],
                },
                # no_proxy env variable is not read by boto3, so
                # this is needed for the tests to avoid hitting the proxy.
                proxies={},
            )
            g.boto3_client = boto3.client(
                "s3",
                os.environ["S3_REGION"],
                aws_access_key_id=os.environ["S3_ACCESS_KEY"],
                aws_secret_access_key=os.environ["S3_SECRET_KEY"],
                endpoint_url=os.environ["S3_ENDPOINT"],
                use_ssl=False,
                config=s3_client_config,
            )
        else:
            return None
    return g.boto3_client


@app.teardown_appcontext
def teardown_database(_):
    """Tear down databases connections."""
    mysql_db = g.pop("mysql_db", None)
    if mysql_db is not None:
        mysql_db.close()
    postgresql_db = g.pop("postgresql_db", None)
    if postgresql_db is not None:
        postgresql_db.close()
    mongodb_db = g.pop("mongodb_db", None)
    if mongodb_db is not None:
        mongodb_db.client.close()
    boto3_client = g.pop("boto3_client", None)
    if boto3_client is not None:
        boto3_client.close()
    rabbitmq = g.pop("rabbitmq", None)
    if rabbitmq is not None:
        rabbitmq.close()
    rabbitmq_from_uri = g.pop("rabbitmq_from_uri", None)
    if rabbitmq_from_uri is not None:
        rabbitmq_from_uri.close()


@app.route("/")
def hello_world():
    return "Hello, World!"


@app.route("/sleep")
def sleep():
    duration_seconds = int(request.args.get("duration"))
    time.sleep(duration_seconds)
    return ""


@app.route("/config/<config_name>")
def config(config_name: str):
    return jsonify(app.config.get(config_name))


@app.route("/mysql/status")
def mysql_status():
    """Mysql status endpoint."""
    if database := get_mysql_database():
        with database.cursor() as cursor:
            sql = "SELECT version()"
            cursor.execute(sql)
            cursor.fetchone()
            return "SUCCESS"
    return "FAIL", 500


@app.route("/s3/status")
def s3_status():
    """S3 status endpoint."""
    if client := get_boto3_client():
        bucket_name = os.environ["S3_BUCKET"]
        _ = client.list_objects(Bucket=bucket_name)
        return "SUCCESS"
    return "FAIL", 500


@app.route("/postgresql/status")
def postgresql_status():
    """Postgresql status endpoint."""
    if database := get_postgresql_database():
        with database.cursor() as cursor:
            sql = "SELECT version()"
            cursor.execute(sql)
            cursor.fetchone()
            return "SUCCESS"
    return "FAIL", 500


@app.route("/mongodb/status")
def mongodb_status():
    """Mongodb status endpoint."""
    if (database := get_mongodb_database()) is not None:
        database.list_collection_names()
        return "SUCCESS"
    return "FAIL", 500


@app.route("/redis/status")
def redis_status():
    """Redis status endpoint."""
    if database := get_redis_database():
        try:
            database.set("foo", "bar")
            return "SUCCESS"
        except redis.exceptions.RedisError:
            logging.exception("Error querying redis")
    return "FAIL", 500


@app.route("/redis/clear_celery_stats")
def redis_celery_clear_stats():
    """Reset Redis statistics about workers and schedulers."""
    if database := get_redis_database():
        try:
            database.delete("workers")
            database.delete("schedulers")
            return "SUCCESS"
        except redis.exceptions.RedisError:
            logging.exception("Error querying redis")
    return "FAIL", 500


@app.route("/redis/celery_stats")
def redis_celery_stats():
    """Read Redis statistics about workers and schedulers."""
    if database := get_redis_database():
        try:
            worker_set = [str(host) for host in database.smembers("workers")]
            beat_set = [str(host) for host in database.smembers("schedulers")]
            return jsonify({"workers": worker_set, "schedulers": beat_set})
        except redis.exceptions.RedisError:
            logging.exception("Error querying redis")
    return "FAIL", 500


@app.route("/rabbitmq/send", methods=["POST"])
def rabbitmq_send():
    """Send a message to "charm" queue."""
    if connection := get_rabbitmq_connection():
        channel = connection.channel()
        channel.queue_declare(queue="charm")
        channel.basic_publish(exchange="", routing_key="charm", body="SUCCESS")
        return "SUCCESS"
    return "FAIL", 500


@app.route("/rabbitmq/receive")
def rabbitmq_receive():
    """Receive a message from "charm" queue in blocking form."""
    if connection := get_rabbitmq_connection_from_uri():
        channel = connection.channel()
        method_frame, _header_frame, body = channel.basic_get("charm")
        if method_frame:
            channel.basic_ack(method_frame.delivery_tag)
            if body == b"SUCCESS":
                return "SUCCESS"
            return "FAIL. INCORRECT MESSAGE."
        return "FAIL. NO MESSAGE."
    return "FAIL. NO CONNECTION."


@app.route("/env")
def get_env():
    """Return environment variables"""
    return jsonify(dict(os.environ))
