"""Quote math used by both the website and the seed-data generator."""
import math
from decimal import Decimal, ROUND_HALF_UP

CENT = Decimal("0.01")


def money(x):
    return Decimal(str(x)).quantize(CENT, rounding=ROUND_HALF_UP)


def material_line(area_sqft, waste_pct, product):
    """area * (1 + waste). Box/piece products get rounded UP to whole units,
    because you can't buy 0.3 of a box."""
    area = Decimal(str(area_sqft))
    need = money(area * (1 + Decimal(str(waste_pct)) / 100))
    price = Decimal(str(product["unit_price"]))
    if product["pricing_unit"] == "sq_ft":
        qty, unit, amount = need, "sq ft", money(need * price)
        price_per_sqft = price
    else:
        cover = Decimal(str(product["sqft_per_unit"]))
        units = math.ceil(need / cover)
        qty, unit, amount = Decimal(units), product["pricing_unit"], money(units * price)
        price_per_sqft = money(price / cover)
    return {"need_sqft": need, "quantity": qty, "unit": unit,
            "unit_price": price, "amount": amount, "price_per_sqft": price_per_sqft}


def build_quote(rooms, products, waste_pct, labor_rate, removal_rate, extras):
    """rooms: list of dicts (room_id, room_name, sqft, product_id, removal_required)
    products: {product_id: product row}
    extras: {item_type: amount} for underlayment, trim, stairs, delivery, other, discount
    returns (items, material_cost, labor_cost, other_cost, total)"""
    items = []
    material = labor = other = Decimal("0")
    for r in rooms:
        p = products[r["product_id"]]
        m = material_line(r["sqft"], waste_pct, p)
        items.append(dict(item_type="material", room_id=r["room_id"], product_id=p["product_id"],
                          description=f"{p['product_name']} for {r['room_name']} ({waste_pct}% waste)",
                          area_sqft=r["sqft"], quantity=m["quantity"], unit=m["unit"],
                          unit_price=m["unit_price"], amount=m["amount"]))
        material += m["amount"]
        a = Decimal(str(r["sqft"]))
        if Decimal(str(labor_rate)) > 0:
            amt = money(a * Decimal(str(labor_rate)))
            items.append(dict(item_type="labor", room_id=r["room_id"], product_id=None,
                              description=f"Installation labor, {r['room_name']}", area_sqft=a,
                              quantity=a, unit="sq ft", unit_price=money(labor_rate), amount=amt))
            labor += amt
        if r["removal_required"] and Decimal(str(removal_rate)) > 0:
            amt = money(a * Decimal(str(removal_rate)))
            items.append(dict(item_type="removal", room_id=r["room_id"], product_id=None,
                              description=f"Remove existing floor, {r['room_name']}", area_sqft=a,
                              quantity=a, unit="sq ft", unit_price=money(removal_rate), amount=amt))
            labor += amt
    for kind, val in extras.items():
        if val in (None, "") or Decimal(str(val)) == 0:
            continue
        amt = money(val)
        if kind == "discount":
            amt = -abs(amt)
        items.append(dict(item_type=kind, room_id=None, product_id=None,
                          description=kind.capitalize(), area_sqft=None, quantity=Decimal(1),
                          unit="each", unit_price=amt, amount=amt))
        other += amt
    total = material + labor + other
    if total < 0:
        raise ValueError("Discount is bigger than the job total")
    return items, money(material), money(labor), money(other), money(total)
