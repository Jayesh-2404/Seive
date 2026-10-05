"""HTTP handlers."""
from auth import check_auth, Session
from cart import cart_total
from cache import get_cached
def handle_request(token, store):
    if check_auth(token, store): return {"ok": True}
    return {"ok": False, "error": "unauthorized"}
def handle_checkout(items, prices):
    return {"total": cart_total(items, prices)}
def handle_profile(uid, conn):
    from db import get_user
    return get_user(uid, conn)
