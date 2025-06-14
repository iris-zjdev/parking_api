# DB_CONFIG = {
#     "host": "ep-shy-band-a5vmxekw-pooler.us-east-2.aws.neon.tech",
#     "database": "neondb",
#     "user": "neondb_owner",
#     "password": "npg_3CbjfwlJ0cIx",
#     "port": 5432,
#     "sslmode": "require"
# }
from sqlalchemy import create_engine
import os

DATABASE_URL = os.environ.get("DATABASE_URL")

# SQLAlchemy engine using pg8000 as the driver
engine = create_engine(DATABASE_URL, echo=False, future=True)
