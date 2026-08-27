"""Minimal HTTP health server for Railway healthcheck."""
import asyncio
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


health_app = FastAPI(lifespan=lifespan)


@health_app.get("/health")
async def health():
    return {"status": "ok"}


async def run_health_server(host: str = "0.0.0.0", port: int = 8080):
    config = uvicorn.Config(health_app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)
    await server.serve()
