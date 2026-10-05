"""Input validation."""
import re
EMAIL = re.compile(r"^[^@]+@[^@]+\.[^@]+$")
def valid_email(e): return bool(EMAIL.match(e or ""))
def valid_qty(q): return isinstance(q, int) and q > 0
