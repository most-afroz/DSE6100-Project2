"""Anna Johnson Flooring - Project 2 (DSE 6100)
Run:  python app.py   then open http://localhost:5000
"""
import os
import uuid
from datetime import date, datetime
from decimal import Decimal
from functools import wraps

import pymysql
from flask import (Flask, abort, flash, g, redirect, render_template, request,
                   send_from_directory, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

from pricing import build_quote, money
from queries import QUERIES

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-change-me")
app.config["UPLOAD_FOLDER"] = os.path.join(os.path.dirname(__file__), "uploads")
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024
ALLOWED_IMG = {"png", "jpg", "jpeg", "gif", "webp"}

ROOM_TYPES = ['living room', 'kitchen', 'bedroom', 'bathroom', 'hallway', 'basement', 'stairs', 'other']
PATTERNS = ['straight', 'diagonal', 'herringbone', 'chevron', 'brick', 'other']
QUOTE_EXTRAS = ['underlayment', 'trim', 'stairs', 'delivery', 'other', 'discount']
BILL_EXTRAS = ['extra_material', 'subfloor_repair', 'extra_labor', 'upgrade', 'discount', 'credit', 'other']


# ------------------------------------------------------------------ database
def get_db():
    if "db" not in g:
        g.db = pymysql.connect(
            host=os.environ.get("DB_HOST", "localhost"),
            port=int(os.environ.get("DB_PORT", 3306)),
            user=os.environ.get("DB_USER", "root"),
            password=os.environ.get("DB_PASSWORD", ""),
            database=os.environ.get("DB_NAME", "flooring"),
            cursorclass=pymysql.cursors.DictCursor, autocommit=False)
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def q_all(sql, args=None):
    with get_db().cursor() as cur:
        cur.execute(sql, args)
        return cur.fetchall()


def q_one(sql, args=None):
    with get_db().cursor() as cur:
        cur.execute(sql, args)
        return cur.fetchone()


def execute(sql, args=None):
    with get_db().cursor() as cur:
        cur.execute(sql, args)
        return cur.lastrowid


# ------------------------------------------------------------------ auth
def client_required(f):
    @wraps(f)
    def wrap(*a, **kw):
        if session.get("role") != "client":
            return redirect(url_for("login"))
        return f(*a, **kw)
    return wrap


def anna_required(f):
    @wraps(f)
    def wrap(*a, **kw):
        if session.get("role") != "anna":
            return redirect(url_for("anna_login"))
        return f(*a, **kw)
    return wrap


def login_required(f):
    @wraps(f)
    def wrap(*a, **kw):
        if session.get("role") not in ("client", "anna"):
            return redirect(url_for("login"))
        return f(*a, **kw)
    return wrap


@app.context_processor
def inject():
    return dict(role=session.get("role"), user_name=session.get("name"))


@app.template_filter("usd")
def usd(v):
    if v is None:
        return "-"
    v = Decimal(v)
    return ("-$" if v < 0 else "$") + f"{abs(v):,.2f}"


@app.route("/")
def home():
    if session.get("role") == "anna":
        return redirect(url_for("anna_home"))
    if session.get("role") == "client":
        return redirect(url_for("client_home"))
    products = q_all("""SELECT p.*, pc.category_name FROM product p JOIN product_category pc
                        USING (category_id) WHERE is_active ORDER BY category_name, product_name""")
    return render_template("home.html", products=products)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        f = request.form
        card = f["card_number"].replace(" ", "").replace("-", "")
        try:
            month, year = int(f["card_exp_month"]), int(f["card_exp_year"])
            if not (card.isdigit() and len(card) == 16):
                raise ValueError("Card number must be 16 digits.")
            if (year, month) < (date.today().year, date.today().month):
                raise ValueError("That card is expired.")
            if len(f["password"]) < 6:
                raise ValueError("Password should be at least 6 characters.")
            cid = execute("""INSERT INTO client (first_name,last_name,address,phone,email,password_hash,
                                 card_holder,card_number,card_exp_month,card_exp_year)
                             VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                          (f["first_name"].strip(), f["last_name"].strip(), f["address"].strip(),
                           f["phone"].strip(), f["email"].strip().lower(),
                           generate_password_hash(f["password"]), f["card_holder"].strip(),
                           card, month, year))
            get_db().commit()
        except ValueError as e:
            flash(str(e), "error")
            return render_template("register.html", f=f)
        except pymysql.err.IntegrityError as e:
            get_db().rollback()
            flash("That email is already registered." if "Duplicate" in str(e)
                  else "Some information is not valid: " + str(e.args[1]), "error")
            return render_template("register.html", f=f)
        session.clear()
        session.update(role="client", client_id=cid, name=f["first_name"])
        flash(f"Welcome! Your client ID is {cid}.", "ok")
        return redirect(url_for("client_home"))
    return render_template("register.html", f={})


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        c = q_one("SELECT * FROM client WHERE email=%s", (request.form["email"].strip().lower(),))
        if c and check_password_hash(c["password_hash"], request.form["password"]):
            session.clear()
            session.update(role="client", client_id=c["client_id"], name=c["first_name"])
            return redirect(url_for("client_home"))
        flash("Wrong email or password.", "error")
    return render_template("login.html", who="client")


@app.route("/anna/login", methods=["GET", "POST"])
def anna_login():
    if request.method == "POST":
        a = q_one("SELECT * FROM contractor WHERE username=%s", (request.form["email"].strip(),))
        if a and check_password_hash(a["password_hash"], request.form["password"]):
            session.clear()
            session.update(role="anna", name=a["full_name"])
            return redirect(url_for("anna_home"))
        flash("Wrong username or password.", "error")
    return render_template("login.html", who="anna")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# ------------------------------------------------------------------ client side
@app.route("/client")
@client_required
def client_home():
    cid = session["client_id"]
    me = q_one("SELECT * FROM client WHERE client_id=%s", (cid,))
    reqs = q_all("""SELECT r.*, ra.total_sqft, ra.room_count,
                       (SELECT COUNT(*) FROM quote q WHERE q.request_id=r.request_id) AS n_quotes
                    FROM flooring_request r LEFT JOIN request_area ra USING (request_id)
                    WHERE r.client_id=%s ORDER BY r.created_at DESC""", (cid,))
    orders = q_all("""SELECT o.*, q.request_id FROM service_order o JOIN quote q USING (quote_id)
                      WHERE o.client_id=%s ORDER BY o.created_at DESC""", (cid,))
    bills = q_all("""SELECT b.*, p.paid_at FROM bill b JOIN service_order o USING (order_id)
                     LEFT JOIN payment p USING (bill_id)
                     WHERE o.client_id=%s ORDER BY b.created_at DESC""", (cid,))
    return render_template("client_home.html", me=me, reqs=reqs, orders=orders, bills=bills)


@app.route("/request/new", methods=["GET", "POST"])
@client_required
def request_new():
    products = q_all("""SELECT p.*, pc.category_name FROM product p JOIN product_category pc USING (category_id)
                        WHERE is_active ORDER BY category_name, product_name""")
    me = q_one("SELECT address FROM client WHERE client_id=%s", (session["client_id"],))
    if request.method == "GET":
        return render_template("request_new.html", products=products, room_types=ROOM_TYPES,
                               patterns=PATTERNS, default_address=me["address"])
    f = request.form
    try:
        rooms = []
        names = f.getlist("room_name")
        for i, name in enumerate(names):
            if not name.strip():
                continue
            L, W, S = f.getlist("length")[i], f.getlist("width")[i], f.getlist("sqft")[i]
            if L and W:
                L, W = Decimal(L), Decimal(W)
                sqft = money(L * W)
            elif S:
                L = W = None
                sqft = money(S)
            else:
                raise ValueError(f"Room '{name}': give length and width, or total square feet.")
            if sqft <= 0:
                raise ValueError(f"Room '{name}': area has to be more than 0.")
            rooms.append((name.strip(), f.getlist("room_type")[i], L, W, sqft,
                          int(f.getlist("product_id")[i]), f.getlist("current")[i].strip() or None,
                          f.getlist("removal")[i] == "1", f.getlist("pattern")[i]))
        if not rooms:
            raise ValueError("Add at least one room or area.")
        if len({r[0].lower() for r in rooms}) != len(rooms):
            raise ValueError("Each room needs a different name (like 'Bedroom 1', 'Bedroom 2').")
        photos = [p for p in request.files.getlist("photos") if p and p.filename]
        if len(photos) > 5:
            raise ValueError("You can upload up to 5 photos.")
        for p in photos:
            if p.filename.rsplit(".", 1)[-1].lower() not in ALLOWED_IMG:
                raise ValueError(f"{p.filename} is not an image file.")
        rid = execute("""INSERT INTO flooring_request (client_id,service_address,pref_start_date,
                            pref_end_date,budget,note) VALUES (%s,%s,%s,%s,%s,%s)""",
                      (session["client_id"], f["service_address"].strip(), f["pref_start_date"],
                       f.get("pref_end_date") or None, f.get("budget") or None, f.get("note") or None))
        for r in rooms:
            execute("""INSERT INTO request_room (request_id,room_name,room_type,length_ft,width_ft,sqft,
                          product_id,current_flooring,removal_required,install_pattern)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""", (rid, *r))
        for n, p in enumerate(photos, start=1):
            fname = f"{rid}_{n}_{uuid.uuid4().hex[:8]}.{p.filename.rsplit('.', 1)[-1].lower()}"
            p.save(os.path.join(app.config["UPLOAD_FOLDER"], fname))
            execute("INSERT INTO request_photo (request_id,photo_no,file_name) VALUES (%s,%s,%s)",
                    (rid, n, fname))
        get_db().commit()
    except (ValueError, ArithmeticError, pymysql.err.IntegrityError, pymysql.err.OperationalError) as e:
        get_db().rollback()
        flash(str(e), "error")
        return render_template("request_new.html", products=products, room_types=ROOM_TYPES,
                               patterns=PATTERNS, default_address=me["address"])
    flash("Request sent to Anna. You will see her quote here.", "ok")
    return redirect(url_for("request_view", rid=rid))


def load_request(rid):
    r = q_one("""SELECT r.*, ra.total_sqft, ra.room_count, CONCAT(c.first_name,' ',c.last_name) AS client_name,
                    c.email, c.phone
                 FROM flooring_request r JOIN client c USING (client_id)
                 LEFT JOIN request_area ra USING (request_id) WHERE r.request_id=%s""", (rid,))
    if not r:
        abort(404)
    if session.get("role") == "client" and r["client_id"] != session["client_id"]:
        abort(403)
    return r


@app.route("/request/<int:rid>")
@login_required
def request_view(rid):
    r = load_request(rid)
    rooms = q_all("""SELECT rr.*, p.product_name, p.unit_price, p.pricing_unit FROM request_room rr
                     JOIN product p USING (product_id) WHERE request_id=%s ORDER BY room_id""", (rid,))
    photos = q_all("SELECT * FROM request_photo WHERE request_id=%s ORDER BY photo_no", (rid,))
    quotes = q_all("SELECT * FROM quote WHERE request_id=%s ORDER BY version_no", (rid,))
    items = q_all("""SELECT qi.* FROM quote_item qi JOIN quote q USING (quote_id)
                     WHERE q.request_id=%s ORDER BY qi.quote_item_id""", (rid,))
    for q in quotes:
        q["items"] = [i for i in items if i["quote_id"] == q["quote_id"]]
    msgs = q_all("SELECT * FROM negotiation_message WHERE request_id=%s ORDER BY created_at, message_id", (rid,))
    # one timeline with quotes and messages in the order they happened
    timeline = sorted([("quote", q["created_at"], q) for q in quotes] +
                      [("msg", m["created_at"], m) for m in msgs], key=lambda t: t[1])
    open_quote = next((q for q in quotes if q["status"] == "open"), None)
    order = q_one("""SELECT o.* FROM service_order o JOIN quote q USING (quote_id)
                     WHERE q.request_id=%s""", (rid,))
    return render_template("request_view.html", r=r, rooms=rooms, photos=photos, timeline=timeline,
                           open_quote=open_quote, order=order, quotes=quotes)


@app.route("/uploads/<path:fname>")
@login_required
def uploaded(fname):
    ph = q_one("SELECT request_id FROM request_photo WHERE file_name=%s", (fname,))
    if not ph:
        abort(404)
    load_request(ph["request_id"])   # permission check
    return send_from_directory(app.config["UPLOAD_FOLDER"], fname)


@app.route("/request/<int:rid>/respond", methods=["POST"])
@client_required
def client_respond(rid):
    r = load_request(rid)
    action, text = request.form["action"], request.form.get("message", "").strip()
    q = q_one("SELECT * FROM quote WHERE request_id=%s AND status='open' ORDER BY version_no DESC LIMIT 1", (rid,))
    if not q:
        flash("There is no open quote to respond to.", "error")
        return redirect(url_for("request_view", rid=rid))
    db = get_db()
    try:
        if action == "accept":
            execute("UPDATE quote SET status='accepted', decided_at=NOW() WHERE quote_id=%s", (q["quote_id"],))
            execute("UPDATE flooring_request SET status='accepted' WHERE request_id=%s", (rid,))
            execute("""INSERT INTO negotiation_message (request_id,quote_id,sender,msg_type,message)
                       VALUES (%s,%s,'client','accept',%s)""",
                    (rid, q["quote_id"], text or f"Accepted quote v{q['version_no']}."))
            oid = execute("""INSERT INTO service_order (quote_id,client_id,service_address,agreed_price,
                                scheduled_start,scheduled_end) VALUES (%s,%s,%s,%s,%s,%s)""",
                          (q["quote_id"], r["client_id"], r["service_address"], q["total_price"],
                           q["proposed_start"], q["proposed_end"]))
            mats = q_all("""SELECT qi.*, p.pricing_unit, p.unit_price AS p_price, p.sqft_per_unit
                            FROM quote_item qi JOIN product p USING (product_id)
                            WHERE qi.quote_id=%s AND qi.item_type='material'""", (q["quote_id"],))
            for m in mats:
                est = money(m["area_sqft"] * (1 + q["waste_pct"] / 100))
                pps = m["unit_price"] if m["unit"] == "sq ft" else money(m["unit_price"] / m["sqft_per_unit"])
                execute("""INSERT INTO order_item (order_id,room_id,product_id,installed_sqft,est_qty_sqft,
                              unit_price_sqft) VALUES (%s,%s,%s,%s,%s,%s)""",
                        (oid, m["room_id"], m["product_id"], m["area_sqft"], est, pps))
            flash(f"Quote accepted. Order #{oid} is scheduled.", "ok")
        elif action == "counter":
            if not text:
                raise ValueError("Write what you would like changed.")
            execute("""INSERT INTO negotiation_message (request_id,quote_id,sender,msg_type,message)
                       VALUES (%s,%s,'client','counter',%s)""", (rid, q["quote_id"], text))
            execute("UPDATE flooring_request SET status='negotiating' WHERE request_id=%s", (rid,))
            flash("Your counterproposal was sent to Anna.", "ok")
        elif action == "reject":
            execute("UPDATE quote SET status='rejected', decided_at=NOW() WHERE quote_id=%s", (q["quote_id"],))
            execute("UPDATE flooring_request SET status='cancelled' WHERE request_id=%s", (rid,))
            execute("""INSERT INTO negotiation_message (request_id,quote_id,sender,msg_type,message)
                       VALUES (%s,%s,'client','cancel',%s)""",
                    (rid, q["quote_id"], text or "Client rejected the quote and cancelled the request."))
            flash("Request cancelled.", "ok")
        db.commit()
    except ValueError as e:
        db.rollback()
        flash(str(e), "error")
    return redirect(url_for("request_view", rid=rid))


@app.route("/request/<int:rid>/cancel", methods=["POST"])
@client_required
def client_cancel(rid):
    r = load_request(rid)
    if r["status"] not in ("pending", "quoted", "negotiating"):
        flash("This request can't be cancelled anymore.", "error")
        return redirect(url_for("request_view", rid=rid))
    execute("""UPDATE quote SET status='cancelled', decided_at=NOW()
               WHERE request_id=%s AND status='open'""", (rid,))
    execute("UPDATE flooring_request SET status='cancelled' WHERE request_id=%s", (rid,))
    execute("""INSERT INTO negotiation_message (request_id,sender,msg_type,message)
               VALUES (%s,'client','cancel',%s)""",
            (rid, request.form.get("message") or "Client cancelled the request."))
    get_db().commit()
    flash("Request cancelled.", "ok")
    return redirect(url_for("request_view", rid=rid))


# ------------------------------------------------------------------ bills (both roles)
def load_bill(bid):
    b = q_one("""SELECT b.*, o.client_id, o.agreed_price, o.order_id, CONCAT(c.first_name,' ',c.last_name) AS client_name,
                    c.card_number, q.request_id
                 FROM bill b JOIN service_order o USING (order_id) JOIN client c ON c.client_id=o.client_id
                 JOIN quote q ON q.quote_id=o.quote_id WHERE b.bill_id=%s""", (bid,))
    if not b:
        abort(404)
    if session.get("role") == "client" and b["client_id"] != session["client_id"]:
        abort(403)
    return b


@app.route("/bill/<int:bid>")
@login_required
def bill_view(bid):
    b = load_bill(bid)
    versions = q_all("""SELECT b.*, p.paid_at, p.amount AS paid_amount, p.card_last4 FROM bill b
                        LEFT JOIN payment p USING (bill_id) WHERE order_id=%s ORDER BY version_no""",
                     (b["order_id"],))
    items = q_all("""SELECT bi.* FROM bill_item bi JOIN bill b USING (bill_id)
                     WHERE b.order_id=%s ORDER BY bill_item_id""", (b["order_id"],))
    msgs = q_all("""SELECT m.*, b.version_no FROM bill_message m JOIN bill b USING (bill_id)
                    WHERE b.order_id=%s ORDER BY m.created_at, m.message_id""", (b["order_id"],))
    for v in versions:
        v["items"] = [i for i in items if i["bill_id"] == v["bill_id"]]
    current = versions[-1]
    return render_template("bill_view.html", b=b, versions=versions, msgs=msgs, current=current,
                           extras=BILL_EXTRAS)


@app.route("/bill/<int:bid>/pay", methods=["POST"])
@client_required
def bill_pay(bid):
    b = load_bill(bid)
    if b["status"] not in ("unpaid", "disputed"):
        flash("This bill can't be paid (it's already paid or was replaced by a newer version).", "error")
        return redirect(url_for("bill_view", bid=bid))
    execute("INSERT INTO payment (bill_id,amount,card_last4) VALUES (%s,%s,%s)",
            (bid, b["amount_due"], b["card_number"][-4:]))
    execute("UPDATE bill SET status='paid' WHERE bill_id=%s", (bid,))
    get_db().commit()
    flash(f"Paid {usd(b['amount_due'])} with card ending {b['card_number'][-4:]}. Thank you!", "ok")
    return redirect(url_for("bill_view", bid=bid))


@app.route("/bill/<int:bid>/dispute", methods=["POST"])
@client_required
def bill_dispute(bid):
    b = load_bill(bid)
    text = request.form.get("message", "").strip()
    if b["status"] not in ("unpaid", "disputed") or not text:
        flash("Please explain the reason for the dispute.", "error")
        return redirect(url_for("bill_view", bid=bid))
    execute("UPDATE bill SET status='disputed' WHERE bill_id=%s", (bid,))
    execute("INSERT INTO bill_message (bill_id,sender,msg_type,message) VALUES (%s,'client','dispute',%s)",
            (bid, text))
    get_db().commit()
    flash("Dispute sent to Anna.", "ok")
    return redirect(url_for("bill_view", bid=bid))


@app.route("/bill/<int:bid>/respond", methods=["POST"])
@anna_required
def bill_respond(bid):
    b = load_bill(bid)
    f = request.form
    text = f.get("message", "").strip()
    if b["status"] not in ("unpaid", "disputed"):
        flash("Only the current unpaid bill can be answered or revised.", "error")
        return redirect(url_for("bill_view", bid=bid))
    try:
        if f["action"] == "explain":
            if not text:
                raise ValueError("Write the explanation.")
            execute("""INSERT INTO bill_message (bill_id,sender,msg_type,message)
                       VALUES (%s,'contractor','explanation',%s)""", (bid, text))
            flash("Explanation sent.", "ok")
        else:  # revise -> brand new version, old one kept as superseded
            old_items = q_all("SELECT item_type, description, amount FROM bill_item WHERE bill_id=%s", (bid,))
            new_items = [dict(i) for i in old_items]
            for k, i in enumerate(f.getlist("adj_type")):
                amt, desc = f.getlist("adj_amount")[k], f.getlist("adj_desc")[k].strip()
                if amt:
                    amt = money(amt)
                    if i in ("discount", "credit"):
                        amt = -abs(amt)
                    new_items.append(dict(item_type=i, description=desc or i.replace("_", " ").title(), amount=amt))
            if len(new_items) == len(old_items):
                raise ValueError("Add at least one adjustment line to make a revised bill.")
            total = money(sum(i["amount"] for i in new_items))
            if total < 0:
                raise ValueError("Bill total can't go below zero.")
            execute("UPDATE bill SET status='superseded' WHERE bill_id=%s", (bid,))
            nb = execute("""INSERT INTO bill (order_id,version_no,amount_due,note) VALUES (%s,%s,%s,%s)""",
                         (b["order_id"], b["version_no"] + 1, total, text or None))
            for i in new_items:
                execute("INSERT INTO bill_item (bill_id,item_type,description,amount) VALUES (%s,%s,%s,%s)",
                        (nb, i["item_type"], i["description"], i["amount"]))
            execute("""INSERT INTO bill_message (bill_id,sender,msg_type,message)
                       VALUES (%s,'contractor','revision',%s)""",
                    (nb, text or f"Revised bill v{b['version_no'] + 1}: new total {usd(total)}"))
            get_db().commit()
            flash(f"Revised bill v{b['version_no'] + 1} created.", "ok")
            return redirect(url_for("bill_view", bid=nb))
        get_db().commit()
    except (ValueError, ArithmeticError) as e:
        get_db().rollback()
        flash(str(e), "error")
    return redirect(url_for("bill_view", bid=bid))


# ------------------------------------------------------------------ Anna side
@app.route("/anna")
@anna_required
def anna_home():
    stats = q_one("""SELECT
        (SELECT COUNT(*) FROM client) AS clients,
        (SELECT COUNT(*) FROM flooring_request
         WHERE status IN ('pending','negotiating')) AS needs_reply,
        (SELECT COUNT(*) FROM service_order
         WHERE status IN ('scheduled','in_progress')) AS active_orders,
        (SELECT COALESCE(SUM(amount_due),0) FROM bill
         WHERE status IN ('unpaid','disputed')) AS outstanding""")

    todo = q_all("""SELECT r.*, CONCAT(c.first_name,' ',c.last_name) AS client_name,
                           ra.total_sqft
                    FROM flooring_request r
                    JOIN client c USING (client_id)
                    LEFT JOIN request_area ra USING (request_id)
                    WHERE r.status IN ('pending','negotiating')
                    ORDER BY r.created_at""")

    # Chart 1: Requests by status
    request_status = q_all("""
        SELECT status, COUNT(*) AS total
        FROM flooring_request
        GROUP BY status
        ORDER BY total DESC
    """)

    # Chart 2: Monthly requests over the last six months
    # same six calendar months as the revenue chart, so a month with
    # no requests shows as 0 instead of disappearing
    monthly_requests = q_all("""
        WITH RECURSIVE months AS (
            SELECT DATE_SUB(
                CAST(DATE_FORMAT(CURDATE(), '%Y-%m-01') AS DATE),
                INTERVAL 5 MONTH
            ) AS month_start
            UNION ALL
            SELECT DATE_ADD(month_start, INTERVAL 1 MONTH)
            FROM months
            WHERE month_start < CAST(DATE_FORMAT(CURDATE(), '%Y-%m-01') AS DATE)
        )
        SELECT DATE_FORMAT(m.month_start, '%b %Y') AS month,
               YEAR(m.month_start) AS year_num,
               MONTH(m.month_start) AS month_num,
               COUNT(r.request_id) AS total
        FROM months m
        LEFT JOIN flooring_request r
               ON r.created_at >= m.month_start
              AND r.created_at < DATE_ADD(m.month_start, INTERVAL 1 MONTH)
        GROUP BY m.month_start
        ORDER BY m.month_start
    """)

    # Chart 3: Service orders by status
    order_status = q_all("""
        SELECT status, COUNT(*) AS total
        FROM service_order
        GROUP BY status
        ORDER BY total DESC
    """)

    # Chart 4: Monthly revenue from actual payments
    monthly_revenue = q_all("""
        WITH RECURSIVE months AS (
            SELECT DATE_SUB(
                CAST(DATE_FORMAT(CURDATE(), '%Y-%m-01') AS DATE),
                INTERVAL 5 MONTH
            ) AS month_start
            UNION ALL
            SELECT DATE_ADD(month_start, INTERVAL 1 MONTH)
            FROM months
            WHERE month_start < CAST(DATE_FORMAT(CURDATE(), '%Y-%m-01') AS DATE)
        ),
        monthly_payments AS (
            SELECT
                CAST(DATE_FORMAT(paid_at, '%Y-%m-01') AS DATE) AS month_start,
                SUM(amount) AS total
            FROM payment
            WHERE paid_at >= DATE_SUB(
                CAST(DATE_FORMAT(CURDATE(), '%Y-%m-01') AS DATE),
                INTERVAL 5 MONTH
            )
            AND paid_at < DATE_ADD(
                CAST(DATE_FORMAT(CURDATE(), '%Y-%m-01') AS DATE),
                INTERVAL 1 MONTH
            )
            GROUP BY CAST(DATE_FORMAT(paid_at, '%Y-%m-01') AS DATE)
        )
        SELECT
            DATE_FORMAT(months.month_start, '%b %Y') AS month,
            COALESCE(monthly_payments.total, 0) AS total
        FROM months
        LEFT JOIN monthly_payments
            ON months.month_start = monthly_payments.month_start
        ORDER BY months.month_start
    """)

    return render_template(
        "anna_home.html",
        stats=stats,
        todo=todo,
        queries=QUERIES,
        request_status=request_status,
        monthly_requests=monthly_requests,
        order_status=order_status,
        monthly_revenue=monthly_revenue
    )


@app.route("/anna/products", methods=["GET", "POST"])
@anna_required
def products():
    cats = q_all("SELECT * FROM product_category ORDER BY category_name")
    if request.method == "POST":
        if save_product(None):
            return redirect(url_for("products"))
    rows = q_all("""SELECT p.*, pc.category_name FROM product p JOIN product_category pc USING (category_id)
                    ORDER BY pc.category_name, p.product_name""")
    return render_template("products.html", rows=rows, cats=cats, p={})


def save_product(pid):
    f = request.form
    try:
        cat = f["category_id"]
        if f.get("new_category", "").strip():
            cat = execute("INSERT INTO product_category (category_name) VALUES (%s)", (f["new_category"].strip(),))
        vals = (cat, f["product_name"].strip(), f["brand"].strip(), f.get("material_style") or None,
                f.get("color") or None, f["unit_price"], f["pricing_unit"], f.get("length_in") or None,
                f.get("width_in") or None, f.get("sqft_per_unit") or None, f.get("description") or None)
        if pid:
            execute("""UPDATE product SET category_id=%s,product_name=%s,brand=%s,material_style=%s,color=%s,
                         unit_price=%s,pricing_unit=%s,length_in=%s,width_in=%s,sqft_per_unit=%s,description=%s
                       WHERE product_id=%s""", vals + (pid,))
        else:
            execute("""INSERT INTO product (category_id,product_name,brand,material_style,color,unit_price,
                         pricing_unit,length_in,width_in,sqft_per_unit,description)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""", vals)
        get_db().commit()
        flash("Product saved.", "ok")
        return True
    except (pymysql.err.IntegrityError, pymysql.err.OperationalError, pymysql.err.DataError) as e:
        get_db().rollback()
        msg = str(e.args[1]) if len(e.args) > 1 else str(e)
        if "chk_coverage" in msg:
            msg = "Box or piece products need the sq ft covered per box/piece."
        elif "Duplicate" in msg:
            msg = "A product with that name and brand already exists."
        flash("Could not save: " + msg, "error")
        return False


@app.route("/anna/products/<int:pid>", methods=["GET", "POST"])
@anna_required
def product_edit(pid):
    if request.method == "POST":
        if request.form.get("toggle"):
            execute("UPDATE product SET is_active = NOT is_active WHERE product_id=%s", (pid,))
            get_db().commit()
            return redirect(url_for("products"))
        if save_product(pid):
            return redirect(url_for("products"))
    p = q_one("SELECT * FROM product WHERE product_id=%s", (pid,)) or abort(404)
    cats = q_all("SELECT * FROM product_category ORDER BY category_name")
    return render_template("product_edit.html", p=p, cats=cats)


@app.route("/anna/requests")
@anna_required
def anna_requests():
    st = request.args.get("status", "")
    rows = q_all("""SELECT r.*, CONCAT(c.first_name,' ',c.last_name) AS client_name, ra.total_sqft, ra.room_count,
                       (SELECT COUNT(*) FROM quote q WHERE q.request_id=r.request_id) AS n_quotes
                    FROM flooring_request r JOIN client c USING (client_id) LEFT JOIN request_area ra USING (request_id)
                    WHERE (%s='' OR r.status=%s) ORDER BY r.created_at DESC""", (st, st))
    return render_template("requests.html", rows=rows, st=st)


@app.route("/anna/request/<int:rid>/quote", methods=["GET", "POST"])
@anna_required
def quote_form(rid):
    r = load_request(rid)
    if r["status"] not in ("pending", "quoted", "negotiating"):
        flash("This request is closed, no new quote can be made.", "error")
        return redirect(url_for("request_view", rid=rid))
    rooms = q_all("SELECT * FROM request_room WHERE request_id=%s ORDER BY room_id", (rid,))
    prods = q_all("""SELECT p.*, pc.category_name FROM product p JOIN product_category pc USING (category_id)
                     ORDER BY category_name, product_name""")
    last = q_one("SELECT * FROM quote WHERE request_id=%s ORDER BY version_no DESC LIMIT 1", (rid,))
    if request.method == "POST":
        f = request.form
        try:
            pmap = {p["product_id"]: p for p in prods}
            for rm in rooms:
                rm["product_id"] = int(f.get(f"product_{rm['room_id']}", rm["product_id"]))
            extras = {k: f.get(k) for k in QUOTE_EXTRAS}
            items, mat, lab, oth, tot = build_quote(rooms, pmap, Decimal(f["waste_pct"]),
                                                    Decimal(f["labor_rate"] or 0), Decimal(f["removal_rate"] or 0),
                                                    extras)
            ver = (last["version_no"] + 1) if last else 1
            execute("UPDATE quote SET status='superseded' WHERE request_id=%s AND status='open'", (rid,))
            qid = execute("""INSERT INTO quote (request_id,version_no,waste_pct,material_cost,labor_cost,other_cost,
                                total_price,proposed_start,proposed_end,note) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                          (rid, ver, f["waste_pct"], mat, lab, oth, tot, f["proposed_start"],
                           f.get("proposed_end") or None, f.get("note") or None))
            for i in items:
                execute("""INSERT INTO quote_item (quote_id,item_type,room_id,product_id,description,area_sqft,
                              quantity,unit,unit_price,amount) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (qid, i["item_type"], i["room_id"], i["product_id"], i["description"], i["area_sqft"],
                         i["quantity"], i["unit"], i["unit_price"], i["amount"]))
            execute("UPDATE flooring_request SET status='quoted' WHERE request_id=%s", (rid,))
            get_db().commit()
            flash(f"Quote v{ver} sent: {usd(tot)}", "ok")
            return redirect(url_for("request_view", rid=rid))
        except (ValueError, ArithmeticError, KeyError, pymysql.err.IntegrityError, pymysql.err.OperationalError) as e:
            get_db().rollback()
            flash(f"Could not create quote: {e}", "error")
    return render_template("quote_form.html", r=r, rooms=rooms, prods=prods, last=last, extras=QUOTE_EXTRAS)


@app.route("/anna/request/<int:rid>/reply", methods=["POST"])
@anna_required
def anna_reply(rid):
    r = load_request(rid)
    text = request.form.get("message", "").strip()
    if not text:
        flash("Write a message first.", "error")
        return redirect(url_for("request_view", rid=rid))
    q = q_one("SELECT quote_id FROM quote WHERE request_id=%s AND status='open'", (rid,))
    if request.form["action"] == "reject":
        if r["status"] not in ("pending", "quoted", "negotiating"):
            flash("Request is already closed.", "error")
            return redirect(url_for("request_view", rid=rid))
        execute("UPDATE quote SET status='rejected', decided_at=NOW() WHERE request_id=%s AND status='open'", (rid,))
        execute("UPDATE flooring_request SET status='rejected' WHERE request_id=%s", (rid,))
        execute("""INSERT INTO negotiation_message (request_id,quote_id,sender,msg_type,message)
                   VALUES (%s,%s,'contractor','reject',%s)""", (rid, q and q["quote_id"], text))
        flash("Request rejected.", "ok")
    else:
        execute("""INSERT INTO negotiation_message (request_id,quote_id,sender,msg_type,message)
                   VALUES (%s,%s,'contractor','note',%s)""", (rid, q and q["quote_id"], text))
        flash("Note sent.", "ok")
    get_db().commit()
    return redirect(url_for("request_view", rid=rid))


@app.route("/anna/orders")
@anna_required
def anna_orders():
    rows = q_all("""SELECT o.*, CONCAT(c.first_name,' ',c.last_name) AS client_name, q.request_id,
                       (SELECT SUM(installed_sqft) FROM order_item oi WHERE oi.order_id=o.order_id) AS sqft,
                       (SELECT b.bill_id FROM bill b WHERE b.order_id=o.order_id ORDER BY version_no DESC LIMIT 1) AS bill_id,
                       (SELECT b.status FROM bill b WHERE b.order_id=o.order_id ORDER BY version_no DESC LIMIT 1) AS bill_status
                    FROM service_order o JOIN client c USING (client_id) JOIN quote q USING (quote_id)
                    ORDER BY FIELD(o.status,'in_progress','scheduled','completed','cancelled'), o.scheduled_start""")
    return render_template("orders.html", rows=rows)


def load_order(oid):
    o = q_one("""SELECT o.*, CONCAT(c.first_name,' ',c.last_name) AS client_name, q.request_id, q.version_no,
                    q.waste_pct
                 FROM service_order o JOIN client c USING (client_id) JOIN quote q USING (quote_id)
                 WHERE o.order_id=%s""", (oid,))
    if not o:
        abort(404)
    if session.get("role") == "client" and o["client_id"] != session["client_id"]:
        abort(403)
    return o


@app.route("/order/<int:oid>", methods=["GET", "POST"])
@login_required
def order_view(oid):
    o = load_order(oid)
    items = q_all("""SELECT oi.*, rr.room_name, p.product_name FROM order_item oi
                     JOIN request_room rr USING (room_id) JOIN product p ON p.product_id=oi.product_id
                     WHERE order_id=%s ORDER BY oi.order_item_id""", (oid,))
    if request.method == "POST":
        if session.get("role") != "anna":
            abort(403)
        f, act = request.form, request.form["action"]
        try:
            if act == "start" and o["status"] == "scheduled":
                execute("UPDATE service_order SET status='in_progress', actual_install_date=%s WHERE order_id=%s",
                        (f["actual_install_date"], oid))
            elif act == "complete" and o["status"] in ("scheduled", "in_progress"):
                for it in items:
                    qty = f.get(f"actual_{it['order_item_id']}")
                    if not qty:
                        raise ValueError(f"Enter actual material used for {it['room_name']}.")
                    execute("UPDATE order_item SET actual_qty_sqft=%s WHERE order_item_id=%s",
                            (qty, it["order_item_id"]))
                execute("""UPDATE service_order SET status='completed', completion_date=%s,
                              actual_install_date=COALESCE(actual_install_date,%s), completion_note=%s
                           WHERE order_id=%s""",
                        (f["completion_date"], f.get("actual_install_date") or f["completion_date"],
                         f.get("completion_note") or None, oid))
            elif act == "cancel" and o["status"] in ("scheduled", "in_progress"):
                execute("UPDATE service_order SET status='cancelled', completion_note=%s WHERE order_id=%s",
                        (f.get("completion_note") or None, oid))
            else:
                raise ValueError("That action isn't allowed for the current order status.")
            get_db().commit()
            flash("Order updated.", "ok")
        except (ValueError, pymysql.err.IntegrityError, pymysql.err.OperationalError) as e:
            get_db().rollback()
            flash(f"Could not update order: {e}", "error")
        return redirect(url_for("order_view", oid=oid))
    bills = q_all("SELECT * FROM bill WHERE order_id=%s ORDER BY version_no", (oid,))
    return render_template("order_view.html", o=o, items=items, bills=bills, today=date.today())


@app.route("/anna/order/<int:oid>/bill", methods=["GET", "POST"])
@anna_required
def bill_form(oid):
    o = load_order(oid)
    if o["status"] != "completed":
        flash("Finish the project before billing.", "error")
        return redirect(url_for("order_view", oid=oid))
    if q_one("SELECT 1 FROM bill WHERE order_id=%s", (oid,)):
        flash("This order already has a bill. Use 'revise' on the bill page instead.", "error")
        return redirect(url_for("order_view", oid=oid))
    items = q_all("""SELECT oi.*, rr.room_name, p.product_name FROM order_item oi JOIN request_room rr USING (room_id)
                     JOIN product p ON p.product_id=oi.product_id WHERE order_id=%s""", (oid,))
    # suggest an extra-material line wherever more was used than estimated
    suggest = []
    for it in items:
        if it["actual_qty_sqft"] and it["actual_qty_sqft"] > it["est_qty_sqft"]:
            extra = it["actual_qty_sqft"] - it["est_qty_sqft"]
            suggest.append(dict(item_type="extra_material",
                                description=f"Extra {it['product_name']} in {it['room_name']} ({extra} sq ft)",
                                amount=money(extra * it["unit_price_sqft"])))
    if request.method == "POST":
        f = request.form
        try:
            lines = [dict(item_type="quoted", description=f"Accepted quote v{o['version_no']}",
                          amount=o["agreed_price"])]
            for k, t in enumerate(f.getlist("type")):
                amt = f.getlist("amount")[k]
                if amt:
                    amt = money(amt)
                    if t in ("discount", "credit"):
                        amt = -abs(amt)
                    lines.append(dict(item_type=t, description=f.getlist("desc")[k].strip() or t.replace("_", " "),
                                      amount=amt))
            total = money(sum(l["amount"] for l in lines))
            if total < 0:
                raise ValueError("Bill total can't be negative.")
            bid = execute("INSERT INTO bill (order_id,version_no,amount_due,note) VALUES (%s,1,%s,%s)",
                          (oid, total, f.get("note") or None))
            for l in lines:
                execute("INSERT INTO bill_item (bill_id,item_type,description,amount) VALUES (%s,%s,%s,%s)",
                        (bid, l["item_type"], l["description"], l["amount"]))
            get_db().commit()
            flash(f"Bill created for {usd(total)}.", "ok")
            return redirect(url_for("bill_view", bid=bid))
        except (ValueError, ArithmeticError, pymysql.err.IntegrityError) as e:
            get_db().rollback()
            flash(str(e), "error")
    return render_template("bill_form.html", o=o, suggest=suggest, extras=BILL_EXTRAS)


@app.route("/anna/clients")
@anna_required
def anna_clients():
    rows = q_all("""SELECT c.*, (SELECT COUNT(*) FROM flooring_request r WHERE r.client_id=c.client_id) AS n_req
                    FROM client c ORDER BY c.client_id""")
    return render_template("clients.html", rows=rows)


@app.route("/anna/bills")
@anna_required
def anna_bills():
    rows = q_all("""SELECT b.*, CONCAT(c.first_name,' ',c.last_name) AS client_name, p.paid_at,
                       DATEDIFF(COALESCE(p.paid_at, NOW()), b.created_at) AS days
                    FROM bill b JOIN service_order o USING (order_id) JOIN client c ON c.client_id=o.client_id
                    LEFT JOIN payment p USING (bill_id) ORDER BY b.created_at DESC""")
    return render_template("bills.html", rows=rows)


@app.route("/anna/query/<int:n>")
@anna_required
def run_query(n):
    qd = QUERIES.get(n) or abort(404)
    args, rows, cols = {}, [], []
    if "params" in qd:
        today = date.today()
        args = {"year": int(request.args.get("year", today.year)),
                "month": int(request.args.get("month", today.month))}
    rows = q_all(qd["sql"], args or None)
    cols = list(rows[0].keys()) if rows else []
    return render_template("query.html", n=n, qd=qd, rows=rows, cols=cols, args=args, queries=QUERIES)


@app.errorhandler(403)
def e403(_):
    return render_template("message.html", msg="You don't have access to that page."), 403


@app.errorhandler(404)
def e404(_):
    return render_template("message.html", msg="Page not found."), 404


if __name__ == "__main__":
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
