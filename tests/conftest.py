import os
import dotenv
import psycopg
import pytest

# Load .env file variables into environment
dotenv.load_dotenv()


@pytest.fixture(autouse=True)
def clean_database():
    """Ensure database is clean before and after each test."""
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        try:
            with psycopg.connect(db_url) as conn:
                with conn.cursor() as cur:
                    cur.execute("TRUNCATE TABLE expenses RESTART IDENTITY;")
                conn.commit()
        except Exception:
            pass
    yield

