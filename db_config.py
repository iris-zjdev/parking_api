import psycopg2
import urllib.parse

DATABASE_URL = "postgresql://neondb_owner:npg_3CbjfwlJ0cIx@ep-shy-band-a5vmxekw-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require"

url = urllib.parse.urlparse(DATABASE_URL)

DB_CONFIG = {
    "host": url.hostname,
    "database": url.path.lstrip("/"),
    "user": url.username,
    "password": url.password,
    "port": url.port,
    "sslmode": "require"
}
# from sqlalchemy import create_engine
# import os

# DATABASE_URL = os.environ.get("DATABASE_URL")

# # SQLAlchemy engine using pg8000 as the driver
# DATABASE_URL = os.getenv("DATABASE_URL", "").replace("postgresql://", "postgresql+pg8000://")
# engine = create_engine(DATABASE_URL, echo=False, future=True)
