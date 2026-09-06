import logging
from typing import Any
from langgraph.checkpoint.memory import MemorySaver
from flight_domain.config import settings

logger = logging.getLogger("apps.worker.checkpointer")

def get_checkpointer() -> Any:
    """
    Initializes LangGraph checkpointer.
    Uses PostgresSaver with dict_row factory if Postgres is configured,
    otherwise falls back to MemorySaver.
    """
    db_uri = settings.LANGGRAPH_CHECKPOINT_DB_URI
    if db_uri and "postgresql" in db_uri and "localhost" not in db_uri:
        try:
            import psycopg
            from psycopg.rows import dict_row
            from langgraph.checkpoint.postgres import PostgresSaver
            conn = psycopg.connect(db_uri, autocommit=True, prepare_threshold=None, row_factory=dict_row)
            saver = PostgresSaver(conn)
            saver.setup()
            logger.info("Initialized LangGraph PostgresSaver checkpointer.")
            return saver
        except Exception as e:
            logger.warning(f"Could not connect to PostgresSaver: {e}. Falling back to MemorySaver.")
    
    logger.info("Using in-memory LangGraph checkpointer.")
    return MemorySaver()

checkpointer: Any = get_checkpointer()
