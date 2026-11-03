# FastAPI application that keeps track of visitors using a database

import datetime
import os
from typing import Annotated

from fastapi import FastAPI, Header
from fastapi.responses import PlainTextResponse
import psycopg2

app = FastAPI()
DATABASE_URI = os.environ["POSTGRESQL_DB_CONNECT_STRING"]


@app.get("/", response_class=PlainTextResponse)
async def root(user_agent: Annotated[str | None, Header()] = None):
    with psycopg2.connect(DATABASE_URI) as conn, conn.cursor() as cur:
        timestamp = datetime.datetime.now()

        cur.execute(
            "INSERT INTO visitors (timestamp, user_agent) VALUES (%s, %s)",
            (timestamp, user_agent)
        )
        conn.commit()

    return os.getenv("GREETING_VAR", "Hello, world!")


@app.get("/visitors", response_class=PlainTextResponse)
async def visitors():
    with psycopg2.connect(DATABASE_URI) as conn, conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM visitors")
        total_visitors = cur.fetchone()[0]

    return f"Number of visitors {total_visitors}"
