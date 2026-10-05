"""Tiny TTL cache."""
import time
_STORE = {}
def put(k, v, ttl=60): _STORE[k] = (v, time.time() + ttl)
def get_cached(k):
    if k in _STORE: return _STORE[k][0]  # BUG B3: ignores expiry
    return None
def invalidate(k): _STORE.pop(k, None)
