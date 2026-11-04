"""Builds docs/Project2.pdf (title, names, video URL, E-R diagram, assumptions, relational schema)."""
import os
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image, Preformatted,
                                Table, TableStyle, KeepTogether)
from PIL import Image as PILImage

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

NAME = "YOUR NAME"
ACCESS_ID = "YOUR ACCESS ID"
PARTNER = "No Partner"
VIDEO = "https://PASTE-YOUR-VIDEO-LINK-HERE"

ss = getSampleStyleSheet()
H1 = ParagraphStyle("h1", parent=ss["Heading1"], fontSize=16, spaceAfter=6, textColor=colors.HexColor("#3b2a1c"))
H2 = ParagraphStyle("h2", parent=ss["Heading2"], fontSize=12.5, spaceBefore=10, spaceAfter=4, textColor=colors.HexColor("#3b2a1c"))
B = ParagraphStyle("b", parent=ss["Normal"], fontSize=10, leading=14, spaceAfter=5)
LI = ParagraphStyle("li", parent=B, leftIndent=14, bulletIndent=4, spaceAfter=3)
SM = ParagraphStyle("sm", parent=B, fontSize=8.8, leading=11.5)
CODE = ParagraphStyle("code", fontName="Courier", fontSize=7.2, leading=8.6)

story = []
P = lambda t, s=B: story.append(Paragraph(t, s))
def bullets(items):
    for t in items:
        story.append(Paragraph(t, LI, bulletText="•"))

# ---------------------------------------------------------------- page 1
story.append(Spacer(1, 1.2 * inch))
story.append(Paragraph("Project 2", ParagraphStyle("t", parent=ss["Title"], fontSize=30, leading=38, spaceAfter=14, textColor=colors.HexColor("#3b2a1c"))))
story.append(Paragraph("Anna Johnson Flooring: database driven website", ParagraphStyle("st", parent=B, fontSize=13, alignment=1)))
story.append(Paragraph("DSE 6100 · Fall 2026", ParagraphStyle("st2", parent=B, fontSize=11, alignment=1, textColor=colors.grey)))
story.append(Spacer(1, 0.5 * inch))
t = Table([["Student", NAME], ["Access ID", ACCESS_ID], ["Partner", PARTNER], ["Demo video", VIDEO]],
          colWidths=[1.4 * inch, 4.2 * inch])
t.setStyle(TableStyle([("FONT", (0, 0), (0, -1), "Helvetica-Bold", 10.5), ("FONT", (1, 0), (1, -1), "Helvetica", 10.5),
                       ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#d9d2c5")),
                       ("BOTTOMPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 8)]))
story.append(t)
story.append(Spacer(1, 0.5 * inch))
P("<b>What is in this file:</b> 1. E-R diagram  2. Assumptions and design decisions  3. Relational schema  "
  "4. CREATE TABLE statements. The dashboard SQL is in sql.txt and the code, setup scripts and README are in the ZIP.")
P("<b>Stack:</b> Python 3 + Flask for the website, MySQL 8 (tested on MariaDB 10.11 too), plain HTML/CSS. "
  "Everything in the demo is done through the website, I only used the MySQL client to load the schema and the demo data.")
story.append(PageBreak())

# ---------------------------------------------------------------- ER
P("1. E-R Diagram", H1)
P("Notation follows the course textbook: an arrow from an entity to a relationship is a key constraint (at most one), "
  "a thick line is total participation (at least one), a thick arrow means exactly one. Weak entities have a thick border "
  "and their identifying relationship is a double diamond. Underlined attributes are keys or partial keys.", SM)
w, h = PILImage.open(os.path.join(HERE, "er.png")).size
maxw, maxh = 7.3 * inch, 8.4 * inch
scale = min(maxw / w, maxh / h)
story.append(Image(os.path.join(HERE, "er.png"), width=w * scale, height=h * scale))
story.append(PageBreak())

# ---------------------------------------------------------------- assumptions
P("2. Assumptions and Design Decisions", H1)
P("I wrote down the things the project description left open and how I decided them. Most of these came up while I was "
  "actually building the pages, not before.")

P("Business assumptions", H2)
bullets([
    "There is only one contractor, Anna. She logs in with her own account (table <i>contractor</i>). I did not build employee roles because the description never mentions any.",
    "A client is identified by an auto generated <i>client_id</i>. Email is UNIQUE because it's what people log in with.",
    "A request has at least one room. A room belongs to exactly one request, so I made Room a weak entity of Request with room_name as the partial key (you can't have two rooms called \"Kitchen\" in the same request, but you can in different ones).",
    "Each room picks exactly one desired product. If a client wants two products in one space (like tile plus a carpet runner) they enter it as two areas.",
    "The client gives length and width, or just the total square feet. Stairs fit here too, the client just types the sq ft.",
    "Photos are optional, max 5 per request. I enforced the 5 in the schema with photo_no BETWEEN 1 AND 5 and UNIQUE(request_id, photo_no), so even a bug in the code can't add a 6th one.",
    "Anna answers with a full quote, or a note only, or a rejection. A client answers with accept, a counterproposal (free text) or reject/cancel. The counterproposal is text because the examples in the description (cheaper tile, move the date, I remove the carpet myself) are all different kinds of changes.",
    "Only the newest quote of a request is \"open\". When Anna sends a new one the older one becomes \"superseded\". Accepting creates exactly one order.",
    "One bill per order at a time, but it can have many versions. A payment pays one bill version in full (no partial payments). I think partial payments are real life but they were not asked for and they would make the overdue rules much harder to define.",
    "A disputed bill is still an unpaid bill, so it shows up in the overdue report if it is older than 7 days.",
])

P("Rules for the reports", H2)
bullets([
    "<b>Overdue</b> means not paid within 7 days of the bill date. Superseded bill versions are ignored, the clock is on the version the client actually has to pay.",
    "<b>Problem customers</b>: at least 2 overdue bills, and none of the overdue ones was paid within 7 days after becoming overdue (that is, within 14 days of the bill date).",
    "<b>Excellent customers</b>: every paid bill was paid within 24 hours. A brand new bill that is less than 24 hours old and not paid yet doesn't disqualify anyone, the client still has time. At least one paid bill is required.",
    "<b>Best customers</b> uses money actually paid (payment table), not the quoted price, and only on completed orders. I show the top 10 ranked.",
    "<b>Installed square footage</b> (queries 5 and 6) is the floor area of the rooms in completed orders. Material quantity (query 7) is a different thing, it includes the waste.",
    "<b>Total project price</b> in query 5 is the latest valid bill, or the agreed price if there is no bill yet.",
])

P("Important design decisions", H2)
bullets([
    "<b>Nothing gets overwritten.</b> Quotes and bills are versioned with (request_id, version_no) and (order_id, version_no), both UNIQUE. A new version is always a new row. The only thing that changes on an old row is its status. Every message (counterproposal, dispute, explanation) is its own row with a timestamp. This was the most important requirement for me because the description says these records may be needed in a disagreement.",
    "<b>Line items.</b> Quotes and bills have item tables so the totals can be explained line by line (material, removal, labor, underlayment, trim, stairs, delivery, discount). I also kept material_cost, labor_cost, other_cost and total_price on the quote itself and added CHECK (total_price = material_cost + labor_cost + other_cost) so the header can't disagree with itself.",
    "<b>Waste factor.</b> Estimated quantity = area x (1 + waste%). For a 500 sq ft room with 10% waste that is 550 sq ft, same as the example in the description.",
    "<b>Snapshots in the order.</b> The order copies the service address, agreed price and the price per sq ft for each product. If Anna changes a product price next month, the old agreement still shows what was agreed. Order also stores client_id, which is technically derivable through quote and request, but I kept it for simpler queries and because the description says the order should preserve the client.",
    "<b>Derived total area.</b> The total requested sq ft is computed with the view <i>request_area</i> instead of a stored column, so it can never get out of sync with the rooms.",
    "<b>Products are hidden, not deleted.</b> Old quotes point to them (ON DELETE RESTRICT), so Anna can only mark a product inactive.",
    "<b>Credit card.</b> I store the card number because the project asks for it and payment uses the registered card. In a real system I would never do this, it would go to a payment processor and I would only keep a token and the last 4 digits. The payment table already only keeps the last 4.",
])

P("A real world observation", H2)
P("When I was looking at vinyl plank at a home improvement store, the price tag was per square foot but you could only buy it "
  "by the box, and one box covered something odd like 23.64 sq ft. So if you need 550 sq ft you actually buy 24 boxes, not 23.3. "
  "That's why my product table has pricing_unit and sqft_per_unit, and the quote rounds box products up to whole boxes. "
  "I also noticed most installers I talked to just say \"add 10 percent\", so I made 10% the default waste, but Anna can change it per quote "
  "(herringbone and diagonal tile usually need more like 15%).")
story.append(PageBreak())

# ---------------------------------------------------------------- relational schema
P("3. Relational Schema", H1)
P("Primary keys are underlined, foreign keys are in italics with the table they reference.", SM)
rels = [
    ("contractor", "<u>contractor_id</u>, username (UNIQUE), password_hash, full_name"),
    ("client", "<u>client_id</u>, first_name, last_name, address, phone, email (UNIQUE), password_hash, card_holder, card_number, card_exp_month, card_exp_year, registered_at"),
    ("product_category", "<u>category_id</u>, category_name (UNIQUE)"),
    ("product", "<u>product_id</u>, <i>category_id</i> → product_category, product_name, brand, material_style, color, unit_price, pricing_unit, length_in, width_in, sqft_per_unit, description, is_active; UNIQUE(product_name, brand)"),
    ("flooring_request", "<u>request_id</u>, <i>client_id</i> → client, service_address, pref_start_date, pref_end_date, budget, note, status, created_at"),
    ("request_room", "<u>room_id</u>, <i>request_id</i> → flooring_request, room_name, room_type, length_ft, width_ft, sqft, <i>product_id</i> → product, current_flooring, removal_required, install_pattern; UNIQUE(request_id, room_name)"),
    ("request_photo", "<u>photo_id</u>, <i>request_id</i> → flooring_request, photo_no, file_name, uploaded_at; UNIQUE(request_id, photo_no)"),
    ("request_area (view)", "request_id, total_sqft, room_count"),
    ("quote", "<u>quote_id</u>, <i>request_id</i> → flooring_request, version_no, created_at, waste_pct, material_cost, labor_cost, other_cost, total_price, proposed_start, proposed_end, note, status, decided_at; UNIQUE(request_id, version_no)"),
    ("quote_item", "<u>quote_item_id</u>, <i>quote_id</i> → quote, item_type, <i>room_id</i> → request_room, <i>product_id</i> → product, description, area_sqft, quantity, unit, unit_price, amount"),
    ("negotiation_message", "<u>message_id</u>, <i>request_id</i> → flooring_request, <i>quote_id</i> → quote, sender, msg_type, message, created_at"),
    ("service_order", "<u>order_id</u>, <i>quote_id</i> → quote (UNIQUE), <i>client_id</i> → client, service_address, agreed_price, scheduled_start, scheduled_end, status, created_at, actual_install_date, completion_date, completion_note"),
    ("order_item", "<u>order_item_id</u>, <i>order_id</i> → service_order, <i>room_id</i> → request_room, <i>product_id</i> → product, installed_sqft, est_qty_sqft, actual_qty_sqft, unit_price_sqft; UNIQUE(order_id, room_id)"),
    ("bill", "<u>bill_id</u>, <i>order_id</i> → service_order, version_no, created_at, amount_due, note, status; UNIQUE(order_id, version_no)"),
    ("bill_item", "<u>bill_item_id</u>, <i>bill_id</i> → bill, item_type, description, amount"),
    ("bill_message", "<u>message_id</u>, <i>bill_id</i> → bill, sender, msg_type, message, created_at"),
    ("payment", "<u>payment_id</u>, <i>bill_id</i> → bill (UNIQUE), amount, paid_at, card_last4"),
]
t = Table([[Paragraph(f"<b>{n}</b>", SM), Paragraph(a, SM)] for n, a in rels], colWidths=[1.45 * inch, 5.85 * inch])
t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#e2ded6")),
                       ("BOTTOMPADDING", (0, 0), (-1, -1), 4), ("TOPPADDING", (0, 0), (-1, -1), 4)]))
story.append(t)
P("Surrogate keys: for the weak entities (rooms, quotes, bills, items) I used an AUTO_INCREMENT id as the primary key to keep "
  "the foreign keys short, but the real identifying key from the E-R diagram is still enforced with a UNIQUE constraint "
  "(for example UNIQUE(request_id, version_no) on quote).", SM)
story.append(PageBreak())

# ---------------------------------------------------------------- DDL
P("4. CREATE TABLE Statements", H1)
P("Same as db/schema.sql in the ZIP.", SM)
ddl = open(os.path.join(ROOT, "db", "schema.sql")).read()
for block in ddl.split("\n\n"):
    story.append(KeepTogether(Preformatted(block.strip("\n"), CODE)))
    story.append(Spacer(1, 5))


def footer(c, doc):
    c.saveState()
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.grey)
    c.drawString(0.6 * inch, 0.45 * inch, f"Project 2 · {NAME}")
    c.drawRightString(letter[0] - 0.6 * inch, 0.45 * inch, f"Page {doc.page}")
    c.restoreState()


doc = SimpleDocTemplate(os.path.join(HERE, "Project2.pdf"), pagesize=letter, leftMargin=0.6 * inch,
                        rightMargin=0.6 * inch, topMargin=0.6 * inch, bottomMargin=0.7 * inch,
                        title="Project 2", author=NAME)
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print("ok")
