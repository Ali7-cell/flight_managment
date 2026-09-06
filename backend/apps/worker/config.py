from flight_domain.config import settings

class WorkerSettings:
    TITLE: str = "Flight Management System Worker"
    DATABASE_URL: str = settings.DATABASE_URL
    LANGGRAPH_CHECKPOINT_DB_URI: str = settings.LANGGRAPH_CHECKPOINT_DB_URI
    PINECONE_API_KEY: str = settings.PINECONE_API_KEY
    PINECONE_INDEX_HOST: str = settings.PINECONE_INDEX_HOST
    LLM_API_KEY: str = settings.LLM_API_KEY
    EMBEDDING_MODEL: str = settings.EMBEDDING_MODEL
    GMAIL_SERVICE_ACCOUNT_JSON: str = settings.GMAIL_SERVICE_ACCOUNT_JSON
    GMAIL_SENDER_ADDRESS: str = settings.GMAIL_SENDER_ADDRESS
    GMAIL_DELEGATED_SUBJECT: str = settings.GMAIL_DELEGATED_SUBJECT

worker_settings = WorkerSettings()
