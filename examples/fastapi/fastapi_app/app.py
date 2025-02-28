# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
import os

from fastapi import FastAPI, HTTPException
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from fastapi_mail.errors import ConnectionErrors
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import get_tracer_provider, set_tracer_provider
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, create_engine, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from starlette.responses import JSONResponse

conf = ConnectionConfig(
    MAIL_USERNAME=f'{os.environ.get("SMTP_USER")}@{os.environ.get("SMTP_DOMAIN")}',
    MAIL_PASSWORD=os.environ.get("SMTP_PASSWORD", ""),
    MAIL_FROM="tester@example.com",
    MAIL_PORT=os.environ.get("SMTP_PORT", 0),
    MAIL_SERVER=os.environ.get("SMTP_HOST", ""),
    MAIL_FROM_NAME="Desired Name",
    MAIL_STARTTLS=True if os.environ.get("SMTP_TRANSPORT_SECURITY") == "starttls" else False,
    MAIL_SSL_TLS=True if os.environ.get("SMTP_TRANSPORT_SECURITY") == "tls" else False,
    USE_CREDENTIALS=True if os.environ.get("SMTP_PASSWORD", None) else False,
    VALIDATE_CERTS=(
        True if os.environ.get("SMTP_TRANSPORT_SECURITY") in ("starttls", "tls") else False
    ),
)


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


@app.get("/send_mail")
async def simple_send() -> JSONResponse:
    try:
        message = MessageSchema(
            subject="hello",
            recipients=["test@example.com"],
            body="Hello world!",
            subtype=MessageType.plain,
        )

        fm = FastMail(conf)
        await fm.send_message(message)
        return "Sent"
    except ConnectionErrors as e:
        return f"Failed to send mail: {e}"


@app.get("/table/{table}")
def test_table(table: str):
    if inspect(engine).has_table(table):
        return "SUCCESS"
    else:
        raise HTTPException(status_code=404, detail="Table not found")
