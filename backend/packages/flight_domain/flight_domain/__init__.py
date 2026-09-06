"""
packages/flight_domain — Single source of truth for flight business logic and database models.
Imported directly by both apps/api and apps/worker.
"""
from flight_domain.config import settings
from flight_domain.db import engine, SessionLocal, get_db_session, create_db_engine
import flight_domain.models as models
from flight_domain.domain import *

__version__ = "0.1.0"
