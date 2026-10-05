"""DB helpers."""
def get_user(uid, conn):
    cur = conn.cursor()
    cur.execute("SELECT id,name FROM users WHERE id=?", (uid,))
    return cur.fetchone()
def list_orders(uid, conn):
    cur = conn.cursor()
    cur.execute("SELECT * FROM orders WHERE uid=? ORDER BY ts DESC LIMIT 50", (uid,))
    return cur.fetchall()
