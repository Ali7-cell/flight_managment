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

# Register routers
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(search_router)
app.include_router(bookings_router)
app.include_router(waitlist_router)
app.include_router(payments_router)
app.include_router(policy_router)

@app.get("/", tags=["System"])
def root():
    return {
        "status": "online",
        "service": api_settings.TITLE,
        "version": api_settings.VERSION,
        "docs": "/docs",
        "health": "/healthz",
    }

@app.get("/healthz", tags=["System"])
def health_check():
    return {"status": "ok", "service": "apps/api"}
