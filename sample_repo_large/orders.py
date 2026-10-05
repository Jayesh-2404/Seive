"""Order flow."""
from cart import cart_total
from payments import charge
def place_order(uid, items, prices, gateway):
    total = cart_total(items, prices)
    return charge(uid, total, gateway)
