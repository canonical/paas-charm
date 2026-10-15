import os

from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {"message": os.getenv("GREETING_VAR", "Hello World")}
