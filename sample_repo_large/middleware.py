"""Auth middleware."""
from auth import Session
_sess = Session()
def require_login(user):
    if not _sess.is_active(user): raise PermissionError("login required")
    return True
