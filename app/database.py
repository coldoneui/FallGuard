# Database Query
import mysql.connector
from mysql.connector import pooling
from app.config import settings

_pool = pooling.MySQLConnectionPool(
    pool_name="fallguard_pool",
    pool_size=10,
    host=settings.DB_HOST,
    port=settings.DB_PORT,
    user=settings.DB_USER,
    password=settings.DB_PASSWORD,
    database=settings.DB_NAME,
)


def get_connection():
    """Grab a connection from the pool. Caller is responsible for closing it
    (or use the query helpers below, which close automatically)."""
    return _pool.get_connection()


def query_all(sql: str, params: tuple = ()):
    """Run a SELECT and return all rows as a list of dicts."""
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        cursor.close()
        return rows
    finally:
        conn.close()


def query_one(sql: str, params: tuple = ()):
    """Run a SELECT and return the first row as a dict, or None."""
    rows = query_all(sql, params)
    return rows[0] if rows else None


def execute(sql: str, params: tuple = ()):
    """Run an INSERT/UPDATE/DELETE. Returns (lastrowid, rowcount)."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        conn.commit()
        last_id = cursor.lastrowid
        row_count = cursor.rowcount
        cursor.close()
        return last_id, row_count
    finally:
        conn.close()
