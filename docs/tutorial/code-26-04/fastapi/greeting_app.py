import os

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

app = FastAPI()

@app.get("/", response_class=PlainTextResponse)
async def root():
    return os.getenv("GREETING_VAR", "Hello, world!")
