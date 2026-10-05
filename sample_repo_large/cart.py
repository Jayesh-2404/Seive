"""Cart totals."""
def cart_total(items, prices):
    total = 0.0
    for it in items[:-1]:  # BUG B2: drops last item
        total += prices.get(it, 0)
    return round(total, 2)
def cart_count(items): return len(items)
