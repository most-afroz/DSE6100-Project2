# Project 2: Anna Johnson Flooring (DSE 6100)

Partners: Most Afroz (Access ID: ______) and Rifah Tasniya (Access ID: ______)

Demo video: PASTE YOUR VIDEO LINK HERE

This is a small web app for Anna Johnson's flooring business. Clients register, send a flooring request
with one or more rooms and up to 5 photos, then go back and forth with Anna on quotes until one is
accepted. An accepted quote turns into an order, and after the job Anna bills it. The client can pay or
dispute, and Anna can explain or send a revised bill. Every quote version and bill version is kept.
Anna also has a dashboard with the 10 required SQL reports.

## 1. Required software

- Python 3.10 or newer
- MySQL 8.0.16+ (or MariaDB 10.4+). CHECK constraints need at least these versions.
- A browser (I tested with Chrome)

Python packages are in `requirements.txt` (Flask, PyMySQL, Werkzeug).

## 2. Install

```bash
cd project2        # if you downloaded from GitHub the folder is DSE6100-Project2-main
python -m venv venv
# Windows: venv\Scripts\activate      Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
```

## 3. Database configuration and initialization

Log into MySQL as root and create a user for the app (you can use your own name/password,
just match it in step 4):

```sql
CREATE USER 'flooring_app'@'localhost' IDENTIFIED BY 'flooring_pw';
GRANT ALL ON flooring.* TO 'flooring_app'@'localhost';
```

Then build the tables and load the demo data:

```bash
mysql -u root -p < db/schema.sql     # drops and recreates database `flooring`
mysql -u root -p < db/seed.sql       # demo clients, quotes, orders, bills
```

Note: all demo dates are written relative to `NOW()`, so if you reload the seed on the day of the
recording the overdue bills and "this month" sales still line up. Reloading resets everything.

If you change the demo story, run `python db/make_seed.py` to rebuild `db/seed.sql`.

## 4. Start the application

The app reads the database settings from environment variables (defaults in brackets):
`DB_HOST` [localhost], `DB_PORT` [3306], `DB_USER` [root], `DB_PASSWORD` [empty], `DB_NAME` [flooring],
`SECRET_KEY`.

```bash
# Mac/Linux
export DB_USER=flooring_app DB_PASSWORD=flooring_pw
python app.py

# Windows PowerShell
$env:DB_USER="flooring_app"; $env:DB_PASSWORD="flooring_pw"
python app.py
```

## 5. Access the website

Open http://localhost:5000

| Who | Login page | Username | Password |
|---|---|---|---|
| Anna (contractor) | /anna/login | anna | anna123 |
| Any client | /login | first.last@example.com (e.g. maria.lopez@example.com) | password123 |

Demo clients and what they are there for:

| Client | Shows up in |
|---|---|
| Maria Lopez | Best customers, Excellent customers (2 projects, one negotiated) |
| James Carter | Largest project (1200 sq ft basement, box-priced LVP) |
| Priya Shah | Window shoppers (3 requests, none accepted) |
| Tom Nguyen | 2 requests, becomes a window shopper after one more |
| Linda Brooks, Kevin OBrien, Grace Lee | Inactive clients |
| Sarah Kim | Overdue bill (disputed), Problem customer |
| David Miller | Overdue bill, Problem customer until he pays |
| Emily Chen | Excellent customer, has a disputed then revised bill |
| Robert Wilson | Bill from 3 hours ago, not paid yet |
| Aisha Rahman | Material cost analysis (550 vs 620 sq ft oak) and a 1500 sq ft job in progress |
| Carlos Diaz | Accepted a quote this month |
| Nina Patel | Open quote v2 after a counterproposal |

## 6. Files

```
app.py            Flask routes (client side, Anna side, bills, reports)
pricing.py        Quote math: area x (1 + waste%), boxes rounded up
queries.py        The 10 dashboard queries (website runs these)
make_sqltxt.py    Writes sql.txt from queries.py
sql.txt           Dashboard SQL, labeled by query number
db/schema.sql     CREATE TABLE statements with all constraints
db/seed.sql       Demo data
db/make_seed.py   Generator for seed.sql
docs/er.png       E-R diagram (er.dot is the source)
templates/        HTML pages
static/style.css  Styling
uploads/          Client photos are saved here
```

## 7. Contribution

- Most Afroz: GitHub setup, E-R diagram, assumptions and schema (PDF report), client side
  pages (registration, requests, negotiation, paying and disputing bills), queries 1 to 5,
  final submission.
- Rifah Tasniya: setup testing on a second computer and README review, Anna's side (products,
  quotes, orders, bills and revisions), queries 6 to 10, PDF and sql.txt review, video upload.
- Both: full end to end test, recording the demo video together.
- Approximate hours worked together: ___ hours

(Edit the lines above so they match what each of us really did.)
