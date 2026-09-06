from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apps.api.config import api_settings
from apps.api.routers import (
    admin_router,
    search_router,
    bookings_router,
    waitlist_router,
    payments_router,
    auth_router,
    policy_router,
)

app = FastAPI(
    title=api_settings.TITLE,
    version=api_settings.VERSION,
    description="Production-ready Flight Management System API",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import os
from fastapi.staticfiles import StaticFiles

# Register routers
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(search_router)
app.include_router(bookings_router)
app.include_router(waitlist_router)
app.include_router(payments_router)
app.include_router(policy_router)

@app.get("/api/info", tags=["System"])
def api_info():
    return {
        "status": "online",
        "service": api_settings.TITLE,
        "version": api_settings.VERSION,
        "docs": "/docs",
        "health": "/healthz",
    }

from fastapi import Response

@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)

@app.get("/healthz", tags=["System"])
def health_check():
    return {"status": "ok", "service": "apps/api"}

# Mount frontend directory for SPA web application
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
