import os

import psycopg
from dotenv import load_dotenv


def run_migration():
    """Reads schema.sql and runs migrations against the PostgreSQL database."""
    # Load environment variables
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("Error: DATABASE_URL environment variable is not set.")
        return

    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    if not os.path.exists(schema_path):
        print(f"Error: Schema file not found at {schema_path}")
        return

    with open(schema_path, encoding="utf-8") as f:
        schema_sql = f.read()

    print("Connecting to PostgreSQL database...")
    try:
        with psycopg.connect(db_url) as conn:
            with conn.cursor() as cur:
                cur.execute(schema_sql)
            conn.commit()
        print("Migration executed successfully: Table 'expenses' is ready.")
    except Exception as e:
        print(f"Database migration failed: {e}")


if __name__ == "__main__":
    run_migration()
