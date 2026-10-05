"""Payments."""
from db import list_orders
def charge(uid, amount, gateway):
    if amount <= 0: raise ValueError("amount must be > 0")
    return gateway.charge(uid, amount)
def refund(payment_id, gateway): return gateway.refund(payment_id)
