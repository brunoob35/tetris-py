# tetris/db.py
import os
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL não definido no .env")

engine: Engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    future=True,
)

def get_conn():
    return engine.connect()
