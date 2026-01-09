# main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import webhook_router
from .utils.setup import platform
from app.utils.woodlogs import get_logger
from .utils.exceptions import (
    internal_error_handler,
)

logger = get_logger(__file__)

app = FastAPI(
    title="Stripe Payment Service X Firebase Realtime DB",
    description="API service for handling Stripe payments and webhooks.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=platform.cors,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register exception handlers
app.add_exception_handler(Exception, internal_error_handler)

app.include_router(webhook_router)

@app.get("/")
async def read_root():
    return await read_health()

@app.get("/health")
async def read_health():
    return {
        "status": "ok",
        "message": "Stripe Payment Service is running."
    }