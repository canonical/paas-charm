# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

import datetime
import json
import logging
import os
import socket
import time
import urllib.parse
import uuid
from typing import Callable, Generator, List, Optional, Type, TypeVar
from urllib.parse import urlparse

import boto3
import botocore.config
import pika
import psycopg
import pymongo
import pymongo.database
import pymongo.errors
import pymysql
import pymysql.cursors
import redis
from celery import Celery, Task
from flask import Flask, g, jsonify, request
from kafka import (
    KafkaAdminClient,
    KafkaClient,
    KafkaConsumer,
    KafkaProducer,
    OffsetAndMetadata,
    TopicPartition,
)
from kafka.admin import NewTopic

T = TypeVar("T")

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


app = Flask(__name__)
app.config.from_prefixed_env()

broker_url = os.environ.get("REDIS_DB_CONNECT_STRING")
# Configure Celery only if Redis is configured
celery_app = celery_init_app(app, broker_url)
redis_client = redis.Redis.from_url(broker_url) if broker_url else None


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

SOME_ITERABLE = ["TEST-MESSAGE 1", "TEST-MESSAGE 2", "TEST-MESSAGE 3"]


def retrying(value_assigner: Callable[[], T], exception: Type[Exception], max_retries=10) -> T:
    counter = 0
    value = None
    while not value:
        try:
            value = value_assigner()
        except exception as e:
            if counter == max_retries:
                raise e
            counter += 1
            print(f"Exception {e} raised. Retrying {counter} in 2 seconds...")
            time.sleep(2)
    return value

def get_origin() -> str:
    hostname = socket.gethostname()
    return f"{hostname} ({socket.gethostbyname(hostname)})"


@app.route("/kafkap")
def produce_message():

    bootstrap_servers = os.environ.get("ALI_SERVERS").split(",")# ["192.168.1.203:31612"]#.split(",")# event.relation.data[self.app].get("bootstrap-server", "").split(",")
    num_brokers = len(bootstrap_servers)
    username = os.environ.get("ALI_USER")#"admin"#event.relation.data[self.app].get("username", ""),
    password = os.environ.get("ALI_PASS")#"SbmWFinF6iVPoFaIvgfzLPn3PqSeeSEE"#event.relation.data[self.app].get("password", ""),
    roles = os.environ.get("ALI_ROLE")#"producer"#event.relation.data[event.app].get("extra-user-roles", "").split(",")
    topic_name = os.environ.get("ALI_TOPIC")#"test-topic"#event.relation.data[event.app].get("topic", "")
    num_partitions = 10
    replication_factor = 3
    admin_client = retrying(
        lambda: KafkaAdminClient(
        client_id=username,
        bootstrap_servers=bootstrap_servers,
        ssl_check_hostname=False,
        security_protocol="SASL_PLAINTEXT",  # SASL_SSL for TLS enabled Kafka clusters
        sasl_plain_username=username,
        sasl_plain_password = password,
        sasl_mechanism = "SCRAM-SHA-512",
        ssl_cafile= None,
        ssl_certfile= None,
        ssl_keyfile= None,
        api_version= None,
        ),
        Exception
    )
    producer_client = retrying(
        lambda: KafkaProducer(
        bootstrap_servers=bootstrap_servers,
        ssl_check_hostname=False,
        security_protocol="SASL_PLAINTEXT",  # SASL_SSL for TLS enabled Kafka clusters
        sasl_plain_username=username,
        sasl_plain_password = password,
        sasl_mechanism = "SCRAM-SHA-512",
        ssl_cafile= None,
        ssl_certfile= None,
        ssl_keyfile= None,
        api_version= None,
        retries=5,
        retry_backoff_ms=1000
        ),
        Exception
    )
    topic = NewTopic(
            name=topic_name,
            num_partitions=num_partitions,
            replication_factor=replication_factor,
        )
    print("Producer - Create Topic...")
    admin_client.create_topics(new_topics=[topic], validate_only=False)

    # time.sleep(2)
    print("Producer - Starting...")
    # message = {
    # "timestamp": datetime.datetime.now().timestamp(),
    # "_id": uuid.uuid4().hex,
    # "origin": get_origin(),
    # "content": f"Message #1"
    # }
    message_content = "Message #1"
    future = producer_client.send(topic_name, str.encode(message_content))
    future.get(timeout=60)
    print(f"Message published to topic={topic_name}, message content: {message_content}")
    # client.send(
    #     topic=topic_name, value=json.dumps(message)
    # )
    # for _ in range(2):
    #     producer.send('test-topic', b'some_message_bytes')
    print("Producer - Done...")

    consumer_client = retrying(
        lambda: KafkaConsumer(
        topic_name,
        bootstrap_servers=bootstrap_servers,
        ssl_check_hostname=False,
        security_protocol="SASL_PLAINTEXT",  # SASL_SSL for TLS enabled Kafka clusters
        sasl_plain_username=username,
        sasl_plain_password = password,
        sasl_mechanism = "SCRAM-SHA-512",
        ssl_cafile= None,
        ssl_certfile= None,
        ssl_keyfile= None,
        api_version= None,
        group_id= None,
        enable_auto_commit=True,
        auto_offset_reset="earliest",
        consumer_timeout_ms=15000,
        ),
        Exception
    )
    for msg in consumer_client:
        print(msg)
    # consumer_client.subscribe(topics=[topic_name])

    # # if topic has not yet been created
    # if "admin" in roles:
    #     topic_config = NewTopic(
    #         name=topic,
    #         num_partitions=5,
    #         replication_factor=len(num_brokers)-1
    #     )

    #     logger.info(f"Creating new topic - {topic}")
    #     client.create_topic(topic=topic_config)

    # for message in SOME_ITERABLE:
    #     client.produce_message(topic_name=topic, message_content=message)

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
    return "FAIL"


@app.route("/s3/status")
def s3_status():
    """S3 status endpoint."""
    if client := get_boto3_client():
        bucket_name = os.environ["S3_BUCKET"]
        objectsresponse = client.list_objects(Bucket=bucket_name)
        return "SUCCESS"
    return "FAIL"


@app.route("/postgresql/status")
def postgresql_status():
    """Postgresql status endpoint."""
    if database := get_postgresql_database():
        with database.cursor() as cursor:
            sql = "SELECT version()"
            cursor.execute(sql)
            cursor.fetchone()
            return "SUCCESS"
    return "FAIL"


@app.route("/mongodb/status")
def mongodb_status():
    """Mongodb status endpoint."""
    if (database := get_mongodb_database()) is not None:
        database.list_collection_names()
        return "SUCCESS"
    return "FAIL"


@app.route("/redis/status")
def redis_status():
    """Redis status endpoint."""
    if database := get_redis_database():
        try:
            database.set("foo", "bar")
            return "SUCCESS"
        except redis.exceptions.RedisError:
            logging.exception("Error querying redis")
    return "FAIL"


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


@app.route("/rabbitmq/send")
def rabbitmq_send():
    """Send a message to "charm" queue."""
    if connection := get_rabbitmq_connection():
        channel = connection.channel()
        channel.queue_declare(queue="charm")
        channel.basic_publish(exchange="", routing_key="charm", body="SUCCESS")
        return "SUCCESS"
    return "FAIL"


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
