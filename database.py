from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise Exception("DATABASE_URL not set")

# 🔥 FORCE psycopg3 ALWAYS
DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://")
DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://")

print("USING DB:", DATABASE_URL)

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()