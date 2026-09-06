import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/postgres"
    )
    LANGGRAPH_CHECKPOINT_DB_URI: str = os.getenv(
        "LANGGRAPH_CHECKPOINT_DB_URI",
        os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres")
    )
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "https://localhost.supabase.co")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "anon-key-placeholder")
    SUPABASE_JWT_SECRET: str = os.getenv("SUPABASE_JWT_SECRET", "super-secret-jwt-key-placeholder-32char-min")
    
    PINECONE_API_KEY: str = os.getenv("PINECONE_API_KEY", "")
    PINECONE_INDEX_HOST: str = os.getenv("PINECONE_INDEX_HOST", "")
    
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", os.getenv("OPENAI_API_KEY", ""))
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", os.getenv("LLM_API_KEY", ""))
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-5.6-luna")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    
    GMAIL_SERVICE_ACCOUNT_JSON: str = os.getenv("GMAIL_SERVICE_ACCOUNT_JSON", os.getenv("GMAIL_OAUTH_CLIENT_JSON", ""))
    GMAIL_SENDER_ADDRESS: str = os.getenv("GMAIL_SENDER_ADDRESS", "bookings@yourdomain.com")
    GMAIL_DELEGATED_SUBJECT: str = os.getenv("GMAIL_DELEGATED_SUBJECT", "bookings@yourdomain.com")
    GMAIL_APP_PASSWORD: str = os.getenv("GMAIL_APP_PASSWORD", "")
    
    STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "sk_test_placeholder")
    STRIPE_WEBHOOK_SIGNING_SECRET: str = os.getenv("STRIPE_WEBHOOK_SIGNING_SECRET", "whsec_placeholder")
    
    WORKER_URL: str = os.getenv("WORKER_URL", "http://localhost:8001")

    # Policy Constants
    REFUND_ESCALATION_DAYS: int = int(os.getenv("REFUND_ESCALATION_DAYS", "7"))
    WAITLIST_CLAIM_WINDOW_HOURS: int = int(os.getenv("WAITLIST_CLAIM_WINDOW_HOURS", "2"))

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()

# Top-level named constants for LangGraph nodes and domain services
REFUND_ESCALATION_DAYS = settings.REFUND_ESCALATION_DAYS
WAITLIST_CLAIM_WINDOW_HOURS = settings.WAITLIST_CLAIM_WINDOW_HOURS

