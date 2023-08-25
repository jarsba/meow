import os

from fastapi import FastAPI
import uvicorn
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from routes import router
from db import SessionLocal
import logging
from logging.config import dictConfig

logging.config.fileConfig('logging.conf', disable_existing_loggers=False)
logger = logging.getLogger(__name__)

load_dotenv()

API_URL = os.getenv("API_URL")
PROJECT_NAME = os.getenv("PROJECT_NAME")

app = FastAPI(
    title=PROJECT_NAME, docs_url="/api/docs", openapi_url="/api", debug=True
)

origins = [
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get(API_URL)
async def root():
    return {"message": "Hello World"}


# Routers
app.include_router(
    router,
    prefix=API_URL,
)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", reload=True, port=8888)
