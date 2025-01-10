# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

import os

from flask import Flask, request
from sqlalchemy import Column, Integer, String, create_engine, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from werkzeug.security import generate_password_hash

app = Flask(__name__)

engine = create_engine(os.environ["POSTGRESQL_DB_CONNECT_STRING"], echo=True)

Session = scoped_session(sessionmaker(bind=engine))


Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    password = Column(String(256), nullable=False)


@app.route("/users", methods=["POST"])
def create_user():
    username = request.json["username"]
    password = request.json["password"]
    session = Session()
    hashed_password = generate_password_hash(password)
    new_user = User(username=username, password=hashed_password)

    if session.query(User).filter_by(username=username).first():
        return f"user {username} exists", 400

    session.add(new_user)
    session.commit()
    return "", 201


@app.route("/tables/<table>", methods=["HEAD"])
def test_table(table: str):
    if inspect(engine).has_table(table):
        return "", 200
    else:
        return "", 404
