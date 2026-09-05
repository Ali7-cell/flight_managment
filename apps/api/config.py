from flight_domain.config import settings

class ApiSettings:
    TITLE: str = "Flight Management System API"
    VERSION: str = "1.0.0"
    DATABASE_URL: str = settings.DATABASE_URL
    SUPABASE_URL: str = settings.SUPABASE_URL
    SUPABASE_ANON_KEY: str = settings.SUPABASE_ANON_KEY
    SUPABASE_JWT_SECRET: str = settings.SUPABASE_JWT_SECRET
    STRIPE_SECRET_KEY: str = settings.STRIPE_SECRET_KEY
    STRIPE_WEBHOOK_SIGNING_SECRET: str = settings.STRIPE_WEBHOOK_SIGNING_SECRET
    WORKER_URL: str = settings.WORKER_URL

api_settings = ApiSettings()
