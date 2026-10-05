"""Generate a realistic 18-file Python repo (~10-14k tokens) so budget pressure is real.

Layout: auth, api, db, models, services, utils, middleware, cache, payments, ...
Includes 3 known bugs with failing tests (for honest eval without LLM):
  B1 auth.check_auth KeyError on missing token
  B2 cart.total off-by-one (ignores last item)
  B3 cache.get stale (never expires)
"""
from pathlib import Path

FILES = {
"auth.py": '''"""Auth: hashing, sessions, token checks."""\nimport hashlib, time\ndef hash_pw(pw: str) -> str:\n    return hashlib.sha256(pw.encode()).hexdigest()\ndef check_auth(token: str, store: dict) -> bool:\n    return store[token] == "active"  # BUG B1: KeyError if missing\nclass Session:\n    def __init__(self): self.data = {}\n    def login(self, user): self.data[user] = "active"\n    def logout(self, user): self.data.pop(user, None)\n    def is_active(self, user): return self.data.get(user) == "active"\n''',
"api.py": '''"""HTTP handlers."""\nfrom auth import check_auth, Session\nfrom cart import cart_total\nfrom cache import get_cached\ndef handle_request(token, store):\n    if check_auth(token, store): return {"ok": True}\n    return {"ok": False, "error": "unauthorized"}\ndef handle_checkout(items, prices):\n    return {"total": cart_total(items, prices)}\ndef handle_profile(uid, conn):\n    from db import get_user\n    return get_user(uid, conn)\n''',
"db.py": '''"""DB helpers."""\ndef get_user(uid, conn):\n    cur = conn.cursor()\n    cur.execute("SELECT id,name FROM users WHERE id=?", (uid,))\n    return cur.fetchone()\ndef list_orders(uid, conn):\n    cur = conn.cursor()\n    cur.execute("SELECT * FROM orders WHERE uid=? ORDER BY ts DESC LIMIT 50", (uid,))\n    return cur.fetchall()\n''',
"models.py": '''"""Domain models."""\nfrom dataclasses import dataclass\n@dataclass\nclass User:\n    id: int; name: str; email: str\n@dataclass\nclass Order:\n    id: int; uid: int; total: float; ts: str\n''',
"cart.py": '''"""Cart totals."""\ndef cart_total(items, prices):\n    total = 0.0\n    for it in items[:-1]:  # BUG B2: drops last item\n        total += prices.get(it, 0)\n    return round(total, 2)\ndef cart_count(items): return len(items)\n''',
"cache.py": '''"""Tiny TTL cache."""\nimport time\n_STORE = {}\ndef put(k, v, ttl=60): _STORE[k] = (v, time.time() + ttl)\ndef get_cached(k):\n    if k in _STORE: return _STORE[k][0]  # BUG B3: ignores expiry\n    return None\ndef invalidate(k): _STORE.pop(k, None)\n''',
"payments.py": '''"""Payments."""\nfrom db import list_orders\ndef charge(uid, amount, gateway):\n    if amount <= 0: raise ValueError("amount must be > 0")\n    return gateway.charge(uid, amount)\ndef refund(payment_id, gateway): return gateway.refund(payment_id)\n''',
"middleware.py": '''"""Auth middleware."""\nfrom auth import Session\n_sess = Session()\ndef require_login(user):\n    if not _sess.is_active(user): raise PermissionError("login required")\n    return True\n''',
"utils.py": '''"""Formatting utils."""\ndef money(x): return f"${x:.2f}"\ndef clamp(x, lo, hi): return max(lo, min(hi, x))\ndef chunks(xs, n):\n    for i in range(0, len(xs), n): yield xs[i:i+n]\n''',
"services_search.py": '''"""Search service."""\nfrom db import get_user\ndef search_users(q, conn):\n    cur = conn.cursor()\n    cur.execute("SELECT id,name FROM users WHERE name LIKE ?", (f"%{q}%",))\n    return cur.fetchall()\n''',
"services_notify.py": '''"""Notifications."""\ndef send_email(to, subject, body, mailer): return mailer.send(to, subject, body)\ndef send_sms(to, msg, sms): return sms.send(to, msg)\n''',
"config.py": '''"""Config."""\nimport os\nDB_URL = os.getenv("DB_URL", "sqlite:///app.db")\nCACHE_TTL = int(os.getenv("CACHE_TTL", "60"))\nDEBUG = os.getenv("DEBUG", "0") == "1"\n''',
"logger.py": '''"""Logging."""\nimport logging\nlogging.basicConfig(level=logging.INFO)\nlog = logging.getLogger("app")\ndef audit(action, uid): log.info("audit %s uid=%s", action, uid)\n''',
"validators.py": '''"""Input validation."""\nimport re\nEMAIL = re.compile(r"^[^@]+@[^@]+\\.[^@]+$")\ndef valid_email(e): return bool(EMAIL.match(e or ""))\ndef valid_qty(q): return isinstance(q, int) and q > 0\n''',
"orders.py": '''"""Order flow."""\nfrom cart import cart_total\nfrom payments import charge\ndef place_order(uid, items, prices, gateway):\n    total = cart_total(items, prices)\n    return charge(uid, total, gateway)\n''',
"reports.py": '''"""Reports."""\nfrom db import list_orders\ndef revenue(uid, conn):\n    rows = list_orders(uid, conn)\n    return round(sum(r[2] for r in rows), 2)\n''',
"app.py": '''"""App entry."""\nfrom api import handle_request, handle_checkout\nfrom config import DEBUG\ndef main():\n    print("app start debug=", DEBUG)\n''',
"tests_core.py": '''"""Hidden tests for eval (run by harness, not by LLM).""\"""\nfrom auth import check_auth\nfrom cart import cart_total\nfrom cache import put, get_cached\nimport time\ndef t_b1():\n    try: check_auth("missing", {})\n    except KeyError: return False  # bug present\n    return True\ndef t_b2(): return cart_total(["a","b"], {"a":10,"b":5}) == 15\ndef t_b3():\n    put("k","v",ttl=-1); return get_cached("k") is None\n''',
}

def build(path="sample_repo_large"):
    p = Path(path); p.mkdir(parents=True, exist_ok=True)
    for name, src in FILES.items():
        (p / name).write_text(src)
    return p

if __name__ == "__main__":
    print("wrote", build())
