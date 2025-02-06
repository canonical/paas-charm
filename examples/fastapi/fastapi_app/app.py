# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
import os

from fastapi import FastAPI, HTTPException
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import get_tracer_provider, set_tracer_provider
from sqlalchemy import Column, Integer, String, create_engine, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker

app = FastAPI()

set_tracer_provider(TracerProvider())
get_tracer_provider().add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
FastAPIInstrumentor.instrument_app(app)
tracer = trace.get_tracer(__name__)

engine = create_engine(os.environ["POSTGRESQL_DB_CONNECT_STRING"], echo=True)

Session = scoped_session(sessionmaker(bind=engine))

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    password = Column(String(256), nullable=False)


@app.get("/")
async def root():
    with tracer.start_as_current_span("custom-span"):
        return "Hello, World!"


@app.get("/env/user-defined-config")
async def user_defined_config():
    return os.getenv("APP_USER_DEFINED_CONFIG", None)


@app.get("/table/{table}")
def test_table(table: str):
    if inspect(engine).has_table(table):
        return "SUCCESS"
    else:
        raise HTTPException(status_code=404, detail="Table not found")
