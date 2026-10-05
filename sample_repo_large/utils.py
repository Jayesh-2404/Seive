"""Formatting utils."""
def money(x): return f"${x:.2f}"
def clamp(x, lo, hi): return max(lo, min(hi, x))
def chunks(xs, n):
    for i in range(0, len(xs), n): yield xs[i:i+n]
