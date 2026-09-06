from apps.api.routers.admin import router as admin_router
from apps.api.routers.search import router as search_router
from apps.api.routers.bookings import router as bookings_router
from apps.api.routers.waitlist import router as waitlist_router
from apps.api.routers.payments import router as payments_router
from apps.api.routers.auth import router as auth_router
from apps.api.routers.policy import router as policy_router
from apps.api.routers.chat import router as chat_router

__all__ = [
    "admin_router",
    "search_router",
    "bookings_router",
    "waitlist_router",
    "payments_router",
    "auth_router",
    "policy_router",
    "chat_router",
]
