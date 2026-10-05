"""Reports."""
from db import list_orders
def revenue(uid, conn):
    rows = list_orders(uid, conn)
    return round(sum(r[2] for r in rows), 2)
