"""Auth: hashing, sessions, token checks."""
import hashlib, time
def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()
def check_auth(token: str, store: dict) -> bool:
    return store[token] == "active"  # BUG B1: KeyError if missing
class Session:
    def __init__(self): self.data = {}
    def login(self, user): self.data[user] = "active"
    def logout(self, user): self.data.pop(user, None)
    def is_active(self, user): return self.data.get(user) == "active"
