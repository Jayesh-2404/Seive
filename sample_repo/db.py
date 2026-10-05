"""DB helpers."""
def get_user(uid, conn):
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id=?", (uid,))
    return cur.fetchone()
