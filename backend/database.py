from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from config import DB_URL

connect_opts = {"check_same_thread": False} if DB_URL.startswith("sqlite") else {}
engine       = create_engine(DB_URL, connect_args=connect_opts)

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
Base         = declarative_base()
