"""API layer."""
from auth import check_auth, Session
def handle_request(token, store):
    if check_auth(token, store): return {"ok": True}
    return {"ok": False, "error": "unauthorized"}

def add(a, b): return a + b
