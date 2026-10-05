"""Auth middleware sample."""
import hashlib
def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

def check_auth(token: str, store: dict) -> bool:
    # BUG: KeyError when token missing
    return store[token] == "active"

class Session:
    def __init__(self): self.data = {}
    def login(self, user): self.data[user] = "active"
