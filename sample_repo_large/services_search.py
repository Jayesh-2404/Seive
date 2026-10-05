"""Search service."""
from db import get_user
def search_users(q, conn):
    cur = conn.cursor()
    cur.execute("SELECT id,name FROM users WHERE name LIKE ?", (f"%{q}%",))
    return cur.fetchall()
