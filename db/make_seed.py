"""Builds db/seed.sql. All dates are written relative to NOW() so the demo data
always looks fresh (overdue bills stay overdue, "this month" stays this month).
Run:  python db/make_seed.py   (only needed if you change the story below)
"""
import os
import sys
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from werkzeug.security import generate_password_hash  # noqa: E402
from pricing import build_quote, money  # noqa: E402

out = ["USE flooring;", "SET FOREIGN_KEY_CHECKS = 1;"]
D = Decimal


def sql(v):
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, (int, float, Decimal)):
        return str(v)
    if isinstance(v, Raw):
        return v.s
    return "'" + str(v).replace("'", "''") + "'"


class Raw:
    def __init__(self, s):
        self.s = s


def ago(days, hours=0, minutes=0):
    m = int(days * 1440 + hours * 60 + minutes)
    return Raw(f"(NOW() - INTERVAL {m} MINUTE)")


def day(days):  # a DATE, negative = future
    return Raw(f"DATE(NOW() - INTERVAL {days} DAY)" if days >= 0 else f"DATE(NOW() + INTERVAL {-days} DAY)")


def after(base, hours):
    return Raw(f"({base.s} + INTERVAL {int(hours * 60)} MINUTE)")


THIS_MONTH = Raw("GREATEST(CAST(DATE_FORMAT(NOW(), '%Y-%m-01 00:05:00') AS DATETIME), NOW() - INTERVAL 3 DAY)")


def ins(table, **cols):
    out.append(f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join(sql(v) for v in cols.values())});")


# ---------------------------------------------------------------- catalog
ins("contractor", contractor_id=1, username="anna", password_hash=generate_password_hash("anna123"),
    full_name="Anna Johnson")
cats = ["Hardwood", "Engineered wood", "Laminate", "Vinyl plank", "Ceramic tile", "Porcelain tile", "Carpet", "Other"]
for i, c in enumerate(cats, 1):
    ins("product_category", category_id=i, category_name=c)

P = {}
def product(pid, cat, name, brand, style, color, price, unit="sq_ft", L=None, W=None, cover=None, desc=None):
    P[pid] = dict(product_id=pid, product_name=name, unit_price=D(str(price)), pricing_unit=unit, sqft_per_unit=cover)
    ins("product", product_id=pid, category_id=cats.index(cat) + 1, product_name=name, brand=brand,
        material_style=style, color=color, unit_price=price, pricing_unit=unit, length_in=L, width_in=W,
        sqft_per_unit=cover, description=desc)

product(1, "Hardwood", "Solid Oak Hardwood", "Northwood Mills", "3/4 in solid oak", "Natural", 7.50, L=48, W=5,
        desc="Classic solid oak, can be refinished many times.")
product(2, "Hardwood", "Hard Maple Hardwood", "Northwood Mills", "Solid maple", "Honey", 8.25, L=48, W=4)
product(3, "Engineered wood", "Engineered Hickory", "Ridgeline", "Engineered, click lock", "Saddle", 5.90, L=60, W=6.5)
product(4, "Laminate", "AquaShield Laminate", "Coastline Floors", "12 mm laminate", "Grey oak look", 2.89)
product(5, "Vinyl plank", "Luxury Vinyl Plank", "Coastline Floors", "LVP 20 mil wear layer", "Driftwood", 4.25, L=48, W=7)
product(6, "Vinyl plank", "Waterproof LVP Plus (box)", "Coastline Floors", "Rigid core LVP", "Ash", 89.95,
        unit="box", L=48, W=7, cover=23.64, desc="Sold by the box, 23.64 sq ft per box. Good for basements.")
product(7, "Porcelain tile", "Porcelain Tile 12x24", "Stonecraft", "Matte porcelain", "Warm grey", 3.95, L=24, W=12)
product(8, "Ceramic tile", "Ceramic Tile 12x12", "Stonecraft", "Glazed ceramic", "White", 2.75, L=12, W=12)
product(9, "Carpet", "Plush Carpet", "SoftStep", "Nylon plush", "Beige", 3.25)
product(10, "Carpet", "Berber Carpet", "SoftStep", "Loop berber", "Oatmeal", 2.95)
product(11, "Other", "Marble Mosaic Sheet", "Stonecraft", "Marble mosaic", "Carrara", 14.00,
        unit="piece", L=12, W=12, cover=1.00)

# ---------------------------------------------------------------- clients
pw = generate_password_hash("password123")
clients = [
    (1, "Maria", "Lopez", "18 Elm St, Detroit, MI", 200), (2, "James", "Carter", "402 Oak Ave, Dearborn, MI", 180),
    (3, "Priya", "Shah", "77 Maple Rd, Troy, MI", 150), (4, "Tom", "Nguyen", "9 Birch Ln, Novi, MI", 120),
    (5, "Linda", "Brooks", "310 Pine St, Ferndale, MI", 90), (6, "Kevin", "OBrien", "55 Cedar Ct, Livonia, MI", 30),
    (7, "Sarah", "Kim", "120 Lake Dr, Southfield, MI", 170), (8, "David", "Miller", "8 Hill St, Warren, MI", 160),
    (9, "Emily", "Chen", "61 River Rd, Ann Arbor, MI", 140), (10, "Robert", "Wilson", "14 Park Pl, Royal Oak, MI", 100),
    (11, "Aisha", "Rahman", "230 Grand Blvd, Detroit, MI", 130), (12, "Carlos", "Diaz", "5 Spruce Way, Canton, MI", 60),
    (13, "Nina", "Patel", "88 Vine St, Farmington, MI", 45), (14, "Grace", "Lee", "19 Ash Ave, Sterling Heights, MI", 20),
]
for cid, fn, ln, addr, d in clients:
    ins("client", client_id=cid, first_name=fn, last_name=ln, address=addr, phone=f"313-555-{1000 + cid:04d}",
        email=f"{fn.lower()}.{ln.lower()}@example.com", password_hash=pw, card_holder=f"{fn} {ln}",
        card_number=f"41111111111{10000 + cid:05d}", card_exp_month=(cid % 12) + 1, card_exp_year=2029,
        registered_at=ago(d))
ADDR = {c[0]: c[3] for c in clients}

# ---------------------------------------------------------------- helpers for the story
ids = dict(req=0, room=0, quote=0, qi=0, msg=0, order=0, oi=0, bill=0, bi=0, bmsg=0, pay=0)
def nid(k):
    ids[k] += 1
    return ids[k]


def request_(cid, days, rooms, status, budget=None, note=None, start_in=14):
    rid = nid("req")
    ins("flooring_request", request_id=rid, client_id=cid, service_address=ADDR[cid], pref_start_date=day(days - start_in),
        pref_end_date=day(days - start_in - 7), budget=budget, note=note, status=status, created_at=ago(days))
    out_rooms = []
    for (name, rtype, L, W, pid, cur, rem, pat) in rooms:
        room_id = nid("room")
        sqft = money(D(str(L)) * D(str(W)))
        ins("request_room", room_id=room_id, request_id=rid, room_name=name, room_type=rtype, length_ft=L, width_ft=W,
            sqft=sqft, product_id=pid, current_flooring=cur, removal_required=rem, install_pattern=pat)
        out_rooms.append(dict(room_id=room_id, room_name=name, sqft=sqft, product_id=pid, removal_required=rem))
    return rid, out_rooms


def quote_(rid, ver, days, rooms, status, decided=None, waste=10, labor=2.50, removal=1.00, extras=None,
           note=None, start=None):
    extras = extras or {}
    items, mat, lab, oth, tot = build_quote(rooms, P, D(str(waste)), D(str(labor)), D(str(removal)), extras)
    qid = nid("quote")
    ins("quote", quote_id=qid, request_id=rid, version_no=ver, created_at=ago(days), waste_pct=waste,
        material_cost=mat, labor_cost=lab, other_cost=oth, total_price=tot,
        proposed_start=start or day(days - 14), proposed_end=None, note=note, status=status, decided_at=decided)
    for i in items:
        ins("quote_item", quote_item_id=nid("qi"), quote_id=qid, **i)
    return dict(quote_id=qid, total=tot, waste=D(str(waste)), rooms=rooms)


def msg(rid, qid, sender, mtype, text, when):
    ins("negotiation_message", message_id=nid("msg"), request_id=rid, quote_id=qid, sender=sender,
        msg_type=mtype, message=text, created_at=when)


def order_(q, cid, created, status, sched, install=None, done=None, actual=None, note=None):
    """actual: list of multipliers on the estimate per room (1.0 = used exactly the estimate)"""
    oid = nid("order")
    ins("service_order", order_id=oid, quote_id=q["quote_id"], client_id=cid, service_address=ADDR[cid],
        agreed_price=q["total"], scheduled_start=sched, scheduled_end=None, status=status, created_at=created,
        actual_install_date=install, completion_date=done, completion_note=note)
    for k, r in enumerate(q["rooms"]):
        p = P[r["product_id"]]
        est = money(r["sqft"] * (1 + q["waste"] / 100))
        pps = p["unit_price"] if p["pricing_unit"] == "sq_ft" else money(p["unit_price"] / D(str(p["sqft_per_unit"])))
        act = money(est * D(str(actual[k]))) if actual else None
        ins("order_item", order_item_id=nid("oi"), order_id=oid, room_id=r["room_id"], product_id=r["product_id"],
            installed_sqft=r["sqft"], est_qty_sqft=est, actual_qty_sqft=act, unit_price_sqft=pps)
    return dict(order_id=oid, price=q["total"], q=q, cid=cid)


def bill_(o, ver, created, status, extra=(), note=None, base=None):
    bid = nid("bill")
    lines = [("quoted", f"Accepted quote", base if base is not None else o["price"])] + list(extra)
    total = money(sum(D(str(a)) for _, _, a in lines))
    ins("bill", bill_id=bid, order_id=o["order_id"], version_no=ver, created_at=created, amount_due=total,
        note=note, status=status)
    for t, dsc, a in lines:
        ins("bill_item", bill_item_id=nid("bi"), bill_id=bid, item_type=t, description=dsc, amount=money(a))
    return dict(bill_id=bid, total=total, created=created, cid=o["cid"])


def pay(b, hours_after):
    ins("payment", payment_id=nid("pay"), bill_id=b["bill_id"], amount=b["total"],
        paid_at=after(b["created"], hours_after), card_last4=f"{10000 + b['cid']:05d}"[-4:])


def bmsg(b, sender, mtype, text, when):
    ins("bill_message", message_id=nid("bmsg"), bill_id=b["bill_id"], sender=sender, msg_type=mtype,
        message=text, created_at=when)


# ================================================================= the story
# Maria Lopez - best + excellent customer, 2 projects, one with negotiation
rid, rooms = request_(1, 190, [("Living room", "living room", 20, 18, 1, "carpet", True, "straight"),
                               ("Front hallway", "hallway", 30, 4, 1, "carpet", True, "straight")], "accepted",
                      budget=6000, note="Remove the old carpet. Match the oak in the dining room.")
q = quote_(rid, 1, 186, rooms, "accepted", decided=ago(184), extras={"underlayment": 240, "trim": 180})
msg(rid, q["quote_id"], "client", "accept", "Looks good, accepted.", ago(184))
o = order_(q, 1, ago(184), "completed", day(170), install=day(165), done=day(162), actual=[1.0, 1.02])
b = bill_(o, 1, ago(161), "paid"); pay(b, 3)

rid, rooms = request_(1, 100, [("Kitchen", "kitchen", 15, 14, 7, "vinyl", True, "straight"),
                               ("Main bath", "bathroom", 9, 8, 7, "ceramic", True, "diagonal")], "accepted",
                      budget=3000)
q1 = quote_(rid, 1, 97, rooms, "superseded", waste=15, extras={"delivery": 150, "trim": 220})
msg(rid, q1["quote_id"], "client", "counter", "Can we keep the total under $3,000?", ago(96))
q = quote_(rid, 2, 95, rooms, "accepted", decided=ago(94), waste=15, extras={"delivery": 150, "trim": 220, "discount": 200},
           note="Took $200 off and kept the delivery.")
msg(rid, q["quote_id"], "client", "accept", "Thank you Anna!", ago(94))
o = order_(q, 1, ago(94), "completed", day(80), install=day(78), done=day(75), actual=[1.0, 1.05])
b = bill_(o, 1, ago(74), "paid"); pay(b, 5)

# James Carter - biggest finished job so far (1200 sq ft basement), paid in 3 days
rid, rooms = request_(2, 170, [("Basement", "basement", 40, 30, 6, "carpet", True, "straight")], "accepted",
                      budget=9000, note="Need waterproof flooring because this is a basement.")
q = quote_(rid, 1, 166, rooms, "accepted", decided=ago(165), extras={"underlayment": 0, "delivery": 120})
o = order_(q, 2, ago(165), "completed", day(150), install=day(146), done=day(143), actual=[1.04])
b = bill_(o, 1, ago(142), "paid"); pay(b, 72)

# Priya Shah - window shopper: 3 requests, never accepted
rid, rooms = request_(3, 140, [("Bedroom", "bedroom", 12, 12, 9, "hardwood", False, "straight")], "rejected")
msg(rid, None, "contractor", "reject", "Sorry, I am fully booked for those dates and can't do carpet only jobs that small right now.", ago(138))
rid, rooms = request_(3, 110, [("Kitchen", "kitchen", 14, 12, 8, "linoleum", True, "straight")], "cancelled", budget=1200)
q = quote_(rid, 1, 106, rooms, "rejected", decided=ago(104))
msg(rid, q["quote_id"], "client", "cancel", "Too expensive for me right now.", ago(104))
rid, rooms = request_(3, 20, [("Living room", "living room", 18, 15, 4, "carpet", True, "straight")], "pending", budget=2000,
                      note="I have two dogs.")

# Tom Nguyen - 2 requests, no acceptance (one more makes him a window shopper)
rid, rooms = request_(4, 80, [("Bedroom", "bedroom", 13, 11, 3, "carpet", False, "straight")], "cancelled")
q = quote_(rid, 1, 77, rooms, "cancelled", decided=ago(70))
msg(rid, None, "client", "cancel", "Changed my mind, maybe next year.", ago(70))
rid, rooms = request_(4, 15, [("Hallway", "hallway", 25, 4, 5, "tile", False, "straight")], "quoted")
quote_(rid, 1, 12, rooms, "open")

# Sarah Kim - problem customer: one bill paid 20 days late, one still open and disputed
rid, rooms = request_(7, 160, [("Living room", "living room", 20, 15, 2, "carpet", True, "straight")], "accepted")
q = quote_(rid, 1, 157, rooms, "accepted", decided=ago(156))
o = order_(q, 7, ago(156), "completed", day(140), install=day(124), done=day(121), actual=[1.12])
b = bill_(o, 1, ago(120), "paid", extra=[("extra_material", "Extra maple, 39.6 sq ft", 326.70)]); pay(b, 20 * 24)
rid, rooms = request_(7, 60, [("Bedroom", "bedroom", 14, 14, 9, "hardwood", False, "straight")], "accepted")
q = quote_(rid, 1, 58, rooms, "accepted", decided=ago(57))
o = order_(q, 7, ago(57), "completed", day(40), install=day(29), done=day(27), actual=[1.0])
b = bill_(o, 1, ago(25), "disputed", extra=[("extra_labor", "Furniture moving", 150)])
bmsg(b, "client", "dispute", "The billed square footage is incorrect, and I never approved furniture moving.", ago(23))
bmsg(b, "contractor", "explanation", "The room measured 14 by 14, same as your request. Moving the dresser and bed was discussed on site.", ago(22))

# David Miller - paid one bill 18 days late, current bill is 10 days old (overdue)
rid, rooms = request_(8, 150, [("Kitchen", "kitchen", 15, 12, 8, "vinyl", True, "straight")], "accepted")
q = quote_(rid, 1, 147, rooms, "accepted", decided=ago(146))
o = order_(q, 8, ago(146), "completed", day(120), install=day(113), done=day(111), actual=[1.03])
b = bill_(o, 1, ago(110), "paid"); pay(b, 18 * 24)
rid, rooms = request_(8, 50, [("Bathroom", "bathroom", 10, 6, 7, "ceramic", True, "herringbone")], "accepted")
q = quote_(rid, 1, 47, rooms, "accepted", decided=ago(46), waste=15, extras={"other": 90})
o = order_(q, 8, ago(46), "completed", day(20), install=day(14), done=day(11), actual=[1.0])
b = bill_(o, 1, ago(10), "unpaid", extra=[("subfloor_repair", "Replaced rotted subfloor by the toilet", 260)])

# Emily Chen - excellent customer, disputed then paid a revised bill fast
rid, rooms = request_(9, 120, [("Bedroom 1", "bedroom", 14, 12, 3, "carpet", True, "straight"),
                               ("Bedroom 2", "bedroom", 12, 12, 3, "carpet", True, "straight")], "accepted")
q = quote_(rid, 1, 116, rooms, "accepted", decided=ago(115))
o = order_(q, 9, ago(115), "completed", day(95), install=day(92), done=day(90), actual=[1.0, 1.01])
b1 = bill_(o, 1, ago(89), "superseded", extra=[("extra_labor", "Additional labor", 200)])
bmsg(b1, "client", "dispute", "The additional labor charge was never approved.", after(b1["created"], 1))
b2 = bill_(o, 2, after(b1["created"], 2), "paid", extra=[("extra_labor", "Additional labor", 200),
                                                         ("credit", "Removed unapproved labor", -200)],
           note="You are right, removed it.")
bmsg(b2, "contractor", "revision", "You are right, I removed the labor charge. Sorry about that.", after(b1["created"], 2))
pay(b2, 1)

# Robert Wilson - just finished, bill is 3 hours old, not paid yet
rid, rooms = request_(10, 40, [("Living room", "living room", 20, 20, 5, "carpet", True, "straight")], "accepted")
q = quote_(rid, 1, 37, rooms, "accepted", decided=ago(36))
o = order_(q, 10, ago(36), "completed", day(10), install=day(4), done=day(2), actual=[1.0])
b = bill_(o, 1, ago(0, hours=3), "unpaid")

# Aisha Rahman - the 550 vs 620 sq ft hardwood case, and a 1500 sq ft job in progress now
rid, rooms = request_(11, 110, [("Living room", "living room", 25, 20, 1, "carpet", True, "straight")], "accepted")
q = quote_(rid, 1, 107, rooms, "accepted", decided=ago(106))
o = order_(q, 11, ago(106), "completed", day(90), install=day(86), done=day(84),
           actual=[D("620") / D("550")], note="Lots of cuts around the fireplace.")
b = bill_(o, 1, ago(83), "paid", extra=[("extra_material", "Extra oak, 70 sq ft", 525.00)]); pay(b, 48)
rid, rooms = request_(11, 35, [("Basement", "basement", 40, 35, 7, "concrete", False, "straight"),
                               ("Laundry room", "other", 10, 10, 7, "vinyl", True, "straight")], "accepted",
                      budget=15000)
q = quote_(rid, 1, 32, rooms, "accepted", decided=ago(31), extras={"delivery": 200})
order_(q, 11, ago(31), "in_progress", day(5), install=day(3))

# Carlos Diaz - accepted this month, scheduled soon
rid, rooms = request_(12, 10, [("Kitchen", "kitchen", 16, 12, 5, "tile", True, "straight"),
                               ("Dining room", "other", 14, 12, 5, "carpet", True, "straight")], "accepted")
q = quote_(rid, 1, 8, rooms, "accepted", decided=THIS_MONTH, start=day(-14))
msg(rid, q["quote_id"], "client", "accept", "Accepted, see you then.", THIS_MONTH)
order_(q, 12, THIS_MONTH, "scheduled", day(-14))

# Nina Patel - negotiating, open quote v2 (accepting it on camera changes query 3)
rid, rooms = request_(13, 12, [("Kitchen", "kitchen", 12, 11, 7, "vinyl", True, "straight"),
                               ("Guest bath", "bathroom", 8, 6, 7, "vinyl", True, "straight")], "quoted", budget=2500,
                      note="Please minimize transitions between rooms.")
q1 = quote_(rid, 1, 10, rooms, "superseded")
msg(rid, q1["quote_id"], "client", "counter", "Can you use a less expensive tile?", ago(9))
rooms2 = [dict(r, product_id=8) for r in rooms]
quote_(rid, 2, 8, rooms2, "open", note="Switched to the 12x12 ceramic, saves about $300.")

with open(os.path.join(os.path.dirname(__file__), "seed.sql"), "w") as f:
    f.write("-- Demo data for Project 2. Generated by make_seed.py. Logins: anna / anna123,\n"
            "-- clients: <first>.<last>@example.com / password123 (e.g. maria.lopez@example.com)\n")
    f.write("\n".join(out) + "\n")
print("wrote seed.sql with", len(out), "statements")
