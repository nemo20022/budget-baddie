from sqlalchemy import create_engine  # creates connection to the database
from sqlalchemy.orm import sessionmaker, declarative_base  # session = DB operations, base = models foundation
import os  # used to access environment variables

DATABASE_URL = os.getenv("DATABASE_URL")  # get database connection string from environment

if not DATABASE_URL:
    raise Exception("DATABASE_URL not set")  # stop app if DB URL is missing

# FORCE psycopg3 ALWAYS
DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://")  # fix old postgres URL format
DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://")  # enforce psycopg driver

print("USING DB:", DATABASE_URL)  # print DB URL for debugging

engine = create_engine(DATABASE_URL)  # create database engine (connection)

SessionLocal = sessionmaker(
    autocommit=False,  # changes must be committed manually
    autoflush=False,   # don't auto-send changes to DB
    bind=engine        # bind session to the database engine
)

Base = declarative_base()  # base class for all database models (tables)