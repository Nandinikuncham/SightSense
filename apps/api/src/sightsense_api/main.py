
"""SightSense FastAPI application."""

from fastapi import FastAPI

from sightsense_api.api.v1 import (
    analysis,
    audio,
    auth,
    health,
    sessions,
)

app = FastAPI(
    title="SightSense API",
    description="AI-powered assistive scene understanding API",
    version="1.0.0",
)
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(analysis.router, prefix="/api/v1")
app.include_router(audio.router, prefix="/api/v1")
app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(sessions.router, prefix="/api/v1")


@app.get("/")
async def root():
    return {
        "message": "SightSense API is running",
        "docs": "/docs",
    }