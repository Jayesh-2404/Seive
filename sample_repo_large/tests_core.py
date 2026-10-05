"""Hidden tests for eval (run by harness, not by LLM)."""""
from auth import check_auth
from cart import cart_total
from cache import put, get_cached
import time
def t_b1():
    try: check_auth("missing", {})
    except KeyError: return False  # bug present
    return True
def t_b2(): return cart_total(["a","b"], {"a":10,"b":5}) == 15
def t_b3():
    put("k","v",ttl=-1); return get_cached("k") is None
