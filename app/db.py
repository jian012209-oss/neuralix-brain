import os
import psycopg

def check_database():
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        return False

    try:
        with psycopg.connect(
            database_url,
            connect_timeout=10
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                return cursor.fetchone()[0] == 1

    except Exception:
        return False
