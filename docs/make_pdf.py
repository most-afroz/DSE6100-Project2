
"""
Builds docs/Project2.pdf.

Includes:
1. Cover page with both students, Access IDs, and presentation video URL
2. E-R diagram
3. Entity definitions and relationship constraints
4. Relational schema generated from db/schema.sql
5. Consolidated assumptions, reporting rules, and design decisions

The script reads the existing SQL and diagram files but does not modify them.
"""

from pathlib import Path
import re
import xml.sax.saxutils as xml

from PIL import Image as PILImage

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak,
    Image,
    Table,
    TableStyle,
    KeepTogether,
)

# ------------------------------------------------------------
# PATHS AND PROJECT INFORMATION
# ------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent

OUTPUT = ROOT / "docs" / "Project2.pdf"
DIAGRAM = HERE / "er-chen-layout-v2.png"
SQL_FILE = ROOT / "db" / "schema.sql"

STUDENTS = [
    ("Rifah Tasniya", "gx9418"),
    ("Most Afroz", "ic4104"),
]

VIDEO_URL = "https://youtu.be/1mPuhuEytJQ"

PAGE_WIDTH, PAGE_HEIGHT = letter
LEFT_MARGIN = 0.65 * inch
RIGHT_MARGIN = 0.65 * inch
TOP_MARGIN = 0.65 * inch
BOTTOM_MARGIN = 0.65 * inch

# ------------------------------------------------------------
# VALIDATE REQUIRED FILES
# ------------------------------------------------------------

for required_file in (DIAGRAM, SQL_FILE):
    if not required_file.exists():
        raise FileNotFoundError(
            f"Required file was not found: {required_file}"
        )

# ------------------------------------------------------------
# DOCUMENT STYLES
# ------------------------------------------------------------

styles = getSampleStyleSheet()

styles.add(ParagraphStyle(
    name="ProjectTitle",
    parent=styles["Title"],
    fontName="Helvetica-Bold",
    fontSize=23,
    leading=28,
    alignment=TA_CENTER,
    textColor=colors.HexColor("#172B3A"),
    spaceAfter=8,
))

styles.add(ParagraphStyle(
    name="MainHeading",
    parent=styles["Heading1"],
    fontName="Helvetica-Bold",
    fontSize=16,
    leading=20,
    textColor=colors.HexColor("#172B3A"),
    spaceBefore=8,
    spaceAfter=12,
))

styles.add(ParagraphStyle(
    name="SubHeading",
    parent=styles["Heading2"],
    fontName="Helvetica-Bold",
    fontSize=11,
    leading=14,
    textColor=colors.HexColor("#28536B"),
    spaceBefore=9,
    spaceAfter=5,
))

styles.add(ParagraphStyle(
    name="BodyTextCustom",
    parent=styles["BodyText"],
    fontName="Helvetica",
    fontSize=9,
    leading=13,
    alignment=TA_LEFT,
    spaceAfter=6,
))

styles.add(ParagraphStyle(
    name="SmallText",
    parent=styles["BodyText"],
    fontName="Helvetica",
    fontSize=8,
    leading=11,
    textColor=colors.HexColor("#444444"),
))

styles.add(ParagraphStyle(
    name="SchemaText",
    parent=styles["BodyText"],
    fontName="Courier",
    fontSize=7.2,
    leading=9.5,
    spaceAfter=4,
    wordWrap="CJK",
))

styles.add(ParagraphStyle(
    name="EntityName",
    parent=styles["BodyText"],
    fontName="Helvetica-Bold",
    fontSize=8.5,
    leading=11,
    textColor=colors.HexColor("#172B3A"),
))

# ------------------------------------------------------------
# FOOTER
# ------------------------------------------------------------

def add_footer(canvas, doc):
    canvas.saveState()

    canvas.setStrokeColor(colors.HexColor("#D5DDE3"))
    canvas.setLineWidth(0.5)
    canvas.line(
        LEFT_MARGIN,
        0.48 * inch,
        PAGE_WIDTH - RIGHT_MARGIN,
        0.48 * inch,
    )

    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#667580"))

    canvas.drawString(
        LEFT_MARGIN,
        0.30 * inch,
        "DSE 6100 | Project 2",
    )

    canvas.drawRightString(
        PAGE_WIDTH - RIGHT_MARGIN,
        0.30 * inch,
        f"Page {doc.page}",
    )

    canvas.restoreState()


# ------------------------------------------------------------
# SQL PARSING FOR THE RELATIONAL SCHEMA
# Reads db/schema.sql without modifying it.
# ------------------------------------------------------------

def split_sql_definitions(text):
    """Split a CREATE TABLE body at commas outside parentheses."""
    parts = []
    current = []
    depth = 0
    in_single = False
    in_double = False
    in_backtick = False
    escaped = False

    for char in text:
        if escaped:
            current.append(char)
            escaped = False
            continue

        if char == "\\":
            current.append(char)
            escaped = True
            continue

        if char == "'" and not in_double and not in_backtick:
            in_single = not in_single
        elif char == '"' and not in_single and not in_backtick:
            in_double = not in_double
        elif char == "`" and not in_single and not in_double:
            in_backtick = not in_backtick
        elif not in_single and not in_double and not in_backtick:
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            elif char == "," and depth == 0:
                parts.append("".join(current).strip())
                current = []
                continue

        current.append(char)

    if current:
        parts.append("".join(current).strip())

    return parts


def identifiers(text):
    """Return SQL identifiers from a key or foreign-key definition."""
    found = re.findall(
        r"`([^`]+)`|([A-Za-z_][A-Za-z0-9_]*)",
        text,
    )
    return [backtick or plain for backtick, plain in found]


def extract_create_tables(sql):
    """Extract table names, columns, primary keys, and foreign keys."""
    tables = []

    # Drop "-- ..." comments first. Words in comments were being read as
    # columns, and apostrophes in them (e.g. "can't") looked like the start
    # of a string, which swallowed columns and the whole service_order table.
    sql = re.sub(r"--[^\n]*", "", sql)

    pattern = re.compile(
        r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?"
        r"`?([A-Za-z_][A-Za-z0-9_]*)`?\s*\(",
        re.IGNORECASE,
    )

    for match in pattern.finditer(sql):
        table_name = match.group(1)
        opening = match.end() - 1

        depth = 0
        closing = None
        in_single = False
        in_double = False
        in_backtick = False
        escaped = False

        for index in range(opening, len(sql)):
            char = sql[index]

            if escaped:
                escaped = False
                continue

            if char == "\\":
                escaped = True
                continue

            if char == "'" and not in_double and not in_backtick:
                in_single = not in_single
            elif char == '"' and not in_single and not in_backtick:
                in_double = not in_double
            elif char == "`" and not in_single and not in_double:
                in_backtick = not in_backtick
            elif not in_single and not in_double and not in_backtick:
                if char == "(":
                    depth += 1
                elif char == ")":
                    depth -= 1
                    if depth == 0:
                        closing = index
                        break

        if closing is None:
            continue

        body = sql[opening + 1:closing]
        definitions = split_sql_definitions(body)

        columns = []
        primary_keys = []
        foreign_keys = {}

        for definition in definitions:

            # Table-level primary key
            pk_match = re.search(
                r"PRIMARY\s+KEY\s*\((.*?)\)",
                definition,
                re.IGNORECASE | re.DOTALL,
            )

            if pk_match:
                primary_keys.extend(
                    identifiers(pk_match.group(1))
                )
                continue

            # Table-level foreign key
            fk_match = re.search(
                r"FOREIGN\s+KEY\s*\((.*?)\)\s*"
                r"REFERENCES\s+`?([A-Za-z_][A-Za-z0-9_]*)`?\s*"
                r"\((.*?)\)",
                definition,
                re.IGNORECASE | re.DOTALL,
            )

            if fk_match:
                local_columns = identifiers(fk_match.group(1))
                referenced_table = fk_match.group(2)

                for column in local_columns:
                    foreign_keys[column] = referenced_table

                continue

            if re.match(
                r"\s*(CONSTRAINT|UNIQUE|CHECK|KEY|INDEX|"
                r"FULLTEXT|SPATIAL)\b",
                definition,
                re.IGNORECASE,
            ):
                continue

            # Column definition
            column_match = re.match(
                r"\s*`([^`]+)`\s+(.+)",
                definition,
                re.DOTALL,
            )

            if not column_match:
                column_match = re.match(
                    r"\s*([A-Za-z_][A-Za-z0-9_]*)\s+(.+)",
                    definition,
                    re.DOTALL,
                )

            if not column_match:
                continue

            column_name = column_match.group(1)
            column_definition = column_match.group(2).strip()
            # keep the whole type, e.g. ENUM('a','b',...) that spans lines
            type_match = re.match(r"[A-Za-z]+\s*(\([^)]*\))?", column_definition)
            if type_match:
                column_type = re.sub(r"\s+", " ", type_match.group(0))
                column_type = re.sub(r"\s*([(),])\s*", r"\1", column_type).strip()  # keeps 'living room'
            else:
                column_type = column_definition.split()[0]

            columns.append((column_name, column_type))

            # Inline primary key
            if re.search(
                r"\bPRIMARY\s+KEY\b",
                column_definition,
                re.IGNORECASE,
            ):
                primary_keys.append(column_name)

            # Inline foreign key
            inline_fk = re.search(
                r"\bREFERENCES\s+`?([A-Za-z_][A-Za-z0-9_]*)`?",
                column_definition,
                re.IGNORECASE,
            )

            if inline_fk:
                foreign_keys[column_name] = inline_fk.group(1)

        tables.append({
            "name": table_name,
            "columns": columns,
            "primary_keys": primary_keys,
            "foreign_keys": foreign_keys,
        })

    return tables


def build_relational_schema(sql):
    """Create a readable relational-schema listing from the SQL DDL."""
    tables = extract_create_tables(sql)
    output = []

    for table in tables:
        output.append(
            Paragraph(
                xml.escape(table["name"]),
                styles["SubHeading"],
            )
        )

        entries = []

        for column_name, column_type in table["columns"]:
            marks = []

            if column_name in table["primary_keys"]:
                marks.append("PK")

            if column_name in table["foreign_keys"]:
                target = table["foreign_keys"][column_name]
                marks.append(f"FK to {target}")

            suffix = f" [{', '.join(marks)}]" if marks else ""

            entries.append(
                f"{column_name}: {column_type}{suffix}"
            )

        if entries:
            output.append(
                Paragraph(
                    xml.escape(", ".join(entries)),
                    styles["SchemaText"],
                )
            )

    # Include the derived view separately.
    if re.search(
        r"CREATE\s+(?:OR\s+REPLACE\s+)?VIEW\s+`?request_area`?",
        sql,
        re.IGNORECASE,
    ):
        output.append(
            Paragraph(
                "request_area (VIEW)",
                styles["SubHeading"],
            )
        )
        output.append(
            Paragraph(
                "Derived room-area information calculated from the "
                "request-room data. This is a SQL view, not a separate "
                "base table.",
                styles["BodyTextCustom"],
            )
        )

    return output


# ------------------------------------------------------------
# ENTITY DEFINITIONS
# ------------------------------------------------------------

entities = [
    (
        "Contractor",
        "Stores Anna's contractor account and login information. "
        "The project models one contractor and does not introduce "
        "separate employee roles."
    ),
    (
        "Client",
        "Stores client identity, contact information, login credentials, "
        "and the payment-card fields included for the project."
    ),
    (
        "Product Category",
        "Groups flooring products into categories."
    ),
    (
        "Product",
        "Stores flooring product details, including category, brand, "
        "material style, color, dimensions, pricing unit, and availability."
    ),
    (
        "Flooring Request",
        "Records a client's flooring project request, service address, "
        "preferred dates, budget, notes, status, and creation date."
    ),
    (
        "Request Room",
        "Represents an individual room or area included in a flooring "
        "request, including its dimensions, selected product, and "
        "installation requirements."
    ),
    (
        "Request Photo",
        "Stores uploaded photo information associated with a flooring request."
    ),
    (
        "Quote",
        "Stores a contractor's proposed price and terms for a request. "
        "Multiple versions can be retained."
    ),
    (
        "Quote Item",
        "Stores individual quote components, such as material, labor, "
        "removal, delivery, or discounts."
    ),
    (
        "Negotiation Message",
        "Preserves messages exchanged during the request and quote process."
    ),
    (
        "Service Order",
        "Records the accepted project, including its agreed price, "
        "service address, schedule, status, and completion information."
    ),
    (
        "Order Item",
        "Records the rooms and flooring products associated with a service "
        "order, including installed area and material quantities."
    ),
    (
        "Bill",
        "Stores an amount due for a service order. Different bill versions "
        "can be retained."
    ),
    (
        "Bill Item",
        "Stores individual charges that make up a bill."
    ),
    (
        "Bill Message",
        "Preserves messages and explanations associated with a bill, "
        "including disputes."
    ),
    (
        "Payment",
        "Records a payment associated with a bill, including its amount, "
        "date, and card's last four digits."
    ),
    (
        "request_area (View)",
        "Calculates request-level room-area information. It is a derived "
        "view rather than a separately stored base table."
    ),
]


# ------------------------------------------------------------
# RELATIONSHIP CONSTRAINTS
# ------------------------------------------------------------

relationships = [
    (
        "Client and Flooring Request",
        "One client can submit multiple flooring requests. Each request "
        "belongs to one client through its client_id foreign key."
    ),
    (
        "Product Category and Product",
        "One product category can contain multiple products. Each product "
        "references its category."
    ),
    (
        "Flooring Request and Request Room",
        "A request can contain multiple rooms. Each room belongs to one "
        "request. Room names are unique within a request, although the "
        "same room name can appear in different requests."
    ),
    (
        "Flooring Request and Request Photo",
        "A request can have multiple photos. Photos are numbered from "
        "1 through 5, and each request/photo-number combination is unique."
    ),
    (
        "Product and Request Room",
        "A product can be selected for multiple rooms. Each room references "
        "one desired flooring product."
    ),
    (
        "Flooring Request and Quote",
        "A request can have multiple quote versions. Each quote belongs "
        "to a request, and its version number is unique within that request."
    ),
    (
        "Quote and Quote Item",
        "A quote can contain multiple line items. Each quote item belongs "
        "to a quote and can identify the relevant room or product."
    ),
    (
        "Request, Quote, and Negotiation Message",
        "A request can have multiple negotiation messages. Messages preserve "
        "the communication history and can be associated with a quote."
    ),
    (
        "Quote and Service Order",
        "A service order references a quote. The unique quote_id constraint "
        "allows at most one service order to be created from a particular "
        "quote."
    ),
    (
        "Service Order and Order Item",
        "A service order can contain multiple order items. Each order item "
        "records the room and product associated with the installed work."
    ),
    (
        "Service Order and Bill",
        "A service order can have multiple bill versions. The combination "
        "of order_id and version_no prevents duplicate bill versions "
        "for the same order."
    ),
    (
        "Bill and Bill Item",
        "A bill can contain multiple line items, allowing its charges "
        "to be explained individually."
    ),
    (
        "Bill and Bill Message",
        "A bill can have multiple associated messages, preserving "
        "communication about the bill or a dispute."
    ),
    (
        "Bill and Payment",
        "A bill can have at most one payment record because bill_id is "
        "unique in the payment table. Each payment references one bill."
    ),
]


# ------------------------------------------------------------
# CONSOLIDATED ASSUMPTIONS AND DESIGN DECISIONS
# ------------------------------------------------------------

assumption_sections = [
    (
        "1. Clients, Requests, and Rooms",
        [
            "A client is identified by an automatically generated "
            "client_id. Email addresses are unique because email is "
            "used for login.",

            "A flooring request must contain at least one room as a "
            "business rule. Each room belongs to exactly one request. "
            "Room names are unique within a request, so two rooms in "
            "different requests can both be named Kitchen.",

            "Each room has one desired flooring product. If a client "
            "wants different flooring products in separate areas of "
            "the same physical space, those areas are entered separately.",

            "Clients can provide room length and width or enter the "
            "total square footage directly. Stairs can also be entered "
            "using their total square footage.",
        ],
    ),
    (
        "2. Photos, Quotes, and Negotiation",
        [
            "Request photos are optional, with a maximum of five per "
            "request. The photo number range and unique combination "
            "of request_id and photo_no enforce this limit in the database.",

            "Anna can respond to a request with a full quote, a note, "
            "or a rejection. Clients can accept, reject, cancel, or "
            "submit a counterproposal. Counterproposals are stored as "
            "free text because proposed changes can involve different "
            "terms, such as product choice, price, or installation date.",

            "Quotes are versioned rather than overwritten. The combination "
            "of request_id and version_no is unique. Only the newest quote "
            "is intended to remain open; older versions become superseded. "
            "The rule about which quote is currently open is handled by "
            "the application workflow.",

            "A quote can contain multiple line items so material, removal, "
            "labor, underlayment, trim, stairs, delivery, and discounts "
            "can be explained separately. Quote-level material_cost, "
            "labor_cost, other_cost, and total_price provide a summary "
            "of those costs.",
        ],
    ),
    (
        "3. Orders, Bills, and Payments",
        [
            "Accepting a quote creates a service order. The unique "
            "quote_id constraint prevents more than one service order "
            "from referencing the same quote.",

            "The service order preserves the agreed service address "
            "and price information. These snapshots protect the historical "
            "agreement if the client's address or a product's current "
            "price changes later.",

            "Bills are versioned in the same way as quotes. Each order "
            "can have multiple bill versions, identified by a unique "
            "order_id and version_no combination. The application manages "
            "which version is currently active.",

            "The intended payment rule is one full payment per bill "
            "version, with no partial payments. The unique bill_id "
            "constraint allows at most one payment record per bill. "
            "The application must also validate that the payment amount "
            "matches the amount due.",

            "A disputed bill remains unpaid. It therefore continues "
            "to qualify for the overdue rules until it is paid.",
        ],
    ),
    (
        "4. Reporting Rules",
        [
            "<b>Overdue bills:</b> A bill is overdue when it has not been "
            "paid within seven days of its bill date. Superseded bill "
            "versions are excluded; the calculation uses the version "
            "the client is currently expected to pay.",

            "<b>Problem customers:</b> A problem customer has at least "
            "two overdue bills, with none of those overdue bills paid "
            "within seven days after becoming overdue. This is 14 days "
            "from the original bill date.",

            "<b>Excellent customers:</b> Every paid bill must have been "
            "paid within 24 hours. A bill less than 24 hours old does "
            "not disqualify a customer simply because it has not yet "
            "been paid. At least one paid bill is required.",

            "<b>Best customers:</b> Rankings use money actually received "
            "from the payment table, rather than quoted prices. Only "
            "completed orders are included, and the report displays "
            "the top ten customers.",

            "<b>Installed square footage:</b> Queries 5 and 6 use the "
            "floor area of rooms in completed orders. Material quantity "
            "is different because it includes the waste allowance.",

            "<b>Total project price:</b> Query 5 uses the latest valid "
            "bill, or the agreed project price when a bill has not "
            "yet been created.",
        ],
    ),
    (
        "5. Database and Implementation Decisions",
        [
            "<b>Historical records:</b> Quotes, bills, and messages are "
            "preserved instead of being overwritten. New quote and bill "
            "versions are stored as new records, while the status of an "
            "older version can be updated. Messages are stored separately "
            "with timestamps to preserve communication history.",

            "<b>Waste allowance:</b> Estimated material quantity is "
            "calculated as area multiplied by (1 + waste percentage). "
            "For example, a 500-square-foot room with 10% waste requires "
            "an estimated 550 square feet of material.",

            "<b>Derived request area:</b> Total requested square footage "
            "is calculated through the request_area view rather than "
            "stored as a separate request-level value. This avoids "
            "maintaining a duplicate total that could become inconsistent "
            "with the individual rooms.",

            "<b>Product records:</b> Products referenced by historical "
            "quotes are not deleted. Products can instead be marked "
            "inactive, preserving their historical references.",

            "<b>Referential integrity:</b> Primary keys identify records, "
            "foreign keys connect related records, and the schema uses "
            "constraints such as NOT NULL, UNIQUE, CHECK, and referential "
            "actions where defined. Some workflow rules, such as requiring "
            "at least one room or allowing only one active quote version, "
            "must also be checked by the application.",

            "<b>Payment-card information:</b> Card-related fields are "
            "included for the project demonstration. A production system "
            "should use a payment processor and securely retain a token "
            "and limited card details, such as the last four digits, "
            "rather than storing a full card number.",
        ],
    ),
]


# ------------------------------------------------------------
# REAL-WORLD FLOORING OBSERVATION
# ------------------------------------------------------------

real_world_observation = (
    "Flooring materials are sometimes priced by square foot but sold "
    "in whole boxes. For example, if one box covers 23.64 square feet, "
    "a project requiring 550 square feet needs 24 boxes rather than "
    "23.3 boxes. This is why the product design includes pricing_unit "
    "and sqft_per_unit, allowing box quantities to be rounded up to "
    "whole units. A 10% waste allowance is used as the default, while "
    "the contractor can adjust it for installation patterns that "
    "require more material, such as herringbone or diagonal tile."
)


# ------------------------------------------------------------
# HELPER FUNCTIONS FOR THE REPORT
# ------------------------------------------------------------

story = []


def add_paragraph(text, style="BodyTextCustom"):
    story.append(Paragraph(text, styles[style]))


def add_bullets(items):
    for item in items:
        story.append(
            Paragraph(
                f"• {item}",
                ParagraphStyle(
                    "BulletText",
                    parent=styles["BodyTextCustom"],
                    leftIndent=14,
                    firstLineIndent=-9,
                    spaceAfter=5,
                ),
            )
        )


def add_two_column_section(items, left_width=1.55 * inch):
    """Display entity/relationship names alongside their definitions."""
    rows = []

    for heading, description in items:
        rows.append([
            Paragraph(xml.escape(heading), styles["EntityName"]),
            Paragraph(
                xml.escape(description),
                styles["SmallText"],
            ),
        ])

    table = Table(
        rows,
        colWidths=[
            left_width,
            PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN - left_width,
        ],
        hAlign="LEFT",
    )

    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.35,
         colors.HexColor("#D5DDE3")),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))

    story.append(table)


# ------------------------------------------------------------
# CREATE THE PDF
# ------------------------------------------------------------

doc = SimpleDocTemplate(
    str(OUTPUT),
    pagesize=letter,
    rightMargin=RIGHT_MARGIN,
    leftMargin=LEFT_MARGIN,
    topMargin=TOP_MARGIN,
    bottomMargin=BOTTOM_MARGIN,
    title="Project 2 - Anna Johnson Flooring",
    author="Rifah Tasniya and Most Afroz",
)

# ------------------------------------------------------------
# 1. COVER
# ------------------------------------------------------------

story.append(Spacer(1, 0.75 * inch))

story.append(
    Paragraph(
        "PROJECT 2",
        styles["ProjectTitle"],
    )
)

story.append(Spacer(1, 0.15 * inch))

story.append(
    Paragraph(
        "ANNA JOHNSON FLOORING",
        ParagraphStyle(
            "AnnaTitle",
            parent=styles["ProjectTitle"],
            fontSize=25,
            leading=30,
            spaceAfter=18,
        ),
    )
)

story.append(
    Paragraph(
        "DSE 6100 · Fall 2026",
        ParagraphStyle(
            "CourseTitle",
            parent=styles["BodyTextCustom"],
            alignment=TA_CENTER,
            fontSize=12,
            leading=16,
            textColor=colors.HexColor("#526775"),
        ),
    )
)

story.append(Spacer(1, 0.65 * inch))

student_rows = [[
    Paragraph("<b>Student</b>", styles["BodyTextCustom"]),
    Paragraph("<b>Access ID</b>", styles["BodyTextCustom"]),
]]

for name, access_id in STUDENTS:
    student_rows.append([
        Paragraph(xml.escape(name), styles["BodyTextCustom"]),
        Paragraph(xml.escape(access_id), styles["BodyTextCustom"]),
    ])

student_table = Table(
    student_rows,
    colWidths=[3.5 * inch, 2.0 * inch],
    hAlign="CENTER",
)

student_table.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAF0F4")),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#172B3A")),
    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5DC")),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("LEFTPADDING", (0, 0), (-1, -1), 12),
    ("RIGHTPADDING", (0, 0), (-1, -1), 12),
    ("TOPPADDING", (0, 0), (-1, -1), 9),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
]))

story.append(student_table)
story.append(Spacer(1, 0.55 * inch))

story.append(
    Paragraph(
        "<b>Presentation video</b>",
        ParagraphStyle(
            "VideoLabel",
            parent=styles["BodyTextCustom"],
            alignment=TA_CENTER,
            fontSize=10,
        ),
    )
)

safe_video_url = xml.escape(VIDEO_URL, {'"': "&quot;"})

story.append(
    Paragraph(
        f'<link href="{safe_video_url}" color="#28536B">'
        f"{xml.escape(VIDEO_URL)}</link>",
        ParagraphStyle(
            "VideoURL",
            parent=styles["SmallText"],
            alignment=TA_CENTER,
        ),
    )
)

story.append(PageBreak())


# ------------------------------------------------------------
# 2. E-R DIAGRAM
# ------------------------------------------------------------

story.append(
    Paragraph(
        "2. E-R Diagram",
        styles["MainHeading"],
    )
)

story.append(
    Paragraph(
        "The diagram uses Chen notation: rectangles represent entities, "
        "diamonds represent relationships, and ovals represent attributes. "
        "Key attributes are underlined. An arrow from an entity into a "
        "relationship marks a key constraint (the entity takes part at most "
        "once), a thick line marks total participation (at least once), and a "
        "thick arrow means exactly once. Foreign keys are represented by the "
        "relationships, so they are not drawn as attribute ovals.",
        styles["BodyTextCustom"],
    )
)

story.append(Spacer(1, 0.15 * inch))

image_width, image_height = PILImage.open(DIAGRAM).size

available_width = PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN
available_height = (
    PAGE_HEIGHT - TOP_MARGIN - BOTTOM_MARGIN - 1.25 * inch
)

scale = min(
    available_width / image_width,
    available_height / image_height,
)

diagram_image = Image(
    str(DIAGRAM),
    width=image_width * scale,
    height=image_height * scale,
)

diagram_image.hAlign = "CENTER"
story.append(diagram_image)

story.append(PageBreak())


# ------------------------------------------------------------
# 3. ENTITIES AND RELATIONSHIPS
# ------------------------------------------------------------

story.append(
    Paragraph(
        "3. Entities and Relationships",
        styles["MainHeading"],
    )
)

story.append(
    Paragraph(
        "The following descriptions summarize the purpose of each "
        "entity and the main constraints governing how the records "
        "are related.",
        styles["BodyTextCustom"],
    )
)

story.append(
    Paragraph(
        "Entity Definitions",
        styles["SubHeading"],
    )
)

add_two_column_section(entities)

story.append(Spacer(1, 0.12 * inch))

story.append(
    Paragraph(
        "Relationship Constraints",
        styles["SubHeading"],
    )
)

add_two_column_section(
    relationships,
    left_width=1.75 * inch,
)

story.append(PageBreak())


# ------------------------------------------------------------
# 4. RELATIONAL SCHEMA
# ------------------------------------------------------------

story.append(
    Paragraph(
        "4. Relational Schema",
        styles["MainHeading"],
    )
)

story.append(
    Paragraph(
        "The relations below are generated from the project's "
        "db/schema.sql file. PK identifies primary-key attributes; "
        "FK identifies foreign-key attributes and their referenced "
        "tables. The request_area view is identified separately "
        "because it is derived rather than a base table.",
        styles["BodyTextCustom"],
    )
)

sql_text = SQL_FILE.read_text(encoding="utf-8")
story.extend(build_relational_schema(sql_text))

story.append(PageBreak())


# ------------------------------------------------------------
# 5. ASSUMPTIONS
# ------------------------------------------------------------

story.append(
    Paragraph(
        "5. Assumptions and Design Decisions",
        styles["MainHeading"],
    )
)

story.append(
    Paragraph(
        "The following assumptions explain the business rules behind "
        "the database and distinguish database-enforced constraints "
        "from rules managed by the website.",
        styles["BodyTextCustom"],
    )
)

for heading, items in assumption_sections:
    story.append(
        Paragraph(
            xml.escape(heading),
            styles["SubHeading"],
        )
    )
    add_bullets(items)

story.append(
    Paragraph(
        "Real-World Flooring Observation",
        styles["SubHeading"],
    )
)

add_paragraph(xml.escape(real_world_observation))


# ------------------------------------------------------------
# GENERATE
# ------------------------------------------------------------

doc.build(
    story,
    onFirstPage=add_footer,
    onLaterPages=add_footer,
)

print(f"PDF successfully created: {OUTPUT}")
