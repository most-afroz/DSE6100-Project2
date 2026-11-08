# Project 2: Anna Johnson Flooring (DSE 6100 – Database Management and Modeling)

**Collaborators:** Most. Afroz and Rifah Tasniya

**Demo video:** PASTE YOUR VIDEO LINK HERE

This is a small web app for Anna Johnson's flooring business. Clients register, send a flooring request with one or more rooms and up to 5 photos, then go back and forth with Anna on quotes until one is accepted. An accepted quote turns into an order, and after the job Anna bills it. The client can pay or dispute, and Anna can explain or send a revised bill. Every quote version and bill version is kept. Anna also has a dashboard with the 10 required SQL reports.

## 1. Required software

- Python 3.10 or newer
- MySQL 8.0.16+ (or MariaDB 10.4+). CHECK constraints need at least these versions.
- A modern web browser
- Git (to clone the repository)

### Development environment

The project was developed and tested using the following tools:

- macOS (MacBook Pro) and Linux
- XAMPP for local MySQL database management
- Anaconda for Python environment and package management
- MacPorts Graphviz for generating the E-R diagram
- Visual Studio Code for editing and project development
- A PDF viewer extension in Visual Studio Code for viewing PDF files

Python packages are listed in `requirements.txt` (Flask, PyMySQL, Werkzeug, ReportLab, and Pillow). ReportLab and Pillow are also used by the project PDF-generation script.

## 2. Install

Clone the repository and open the project folder:

```bash
git clone https://github.com/most-afroz/DSE6100-Project2.git
cd DSE6100-Project2
```

Create and activate a virtual environment, then install the required packages:

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate

pip install -r requirements.txt
```

## 3. Database configuration and initialization

Log into MySQL as root and create a user for the app (you can use your own name/password, just match it in step 4):

```sql
CREATE USER 'flooring_app'@'localhost' IDENTIFIED BY 'flooring_pw';
GRANT ALL ON flooring.* TO 'flooring_app'@'localhost';
```

Then build the tables and load the demo data:

```bash
mysql -u root -p < db/schema.sql
mysql -u root -p < db/seed.sql
```

The schema script drops and recreates the database `flooring`. The seed script loads the demo clients, quotes, orders, bills, and other sample data.

### macOS with XAMPP

Start the MySQL service through the XAMPP control panel.

Open phpMyAdmin at [http://localhost/phpmyadmin/](http://localhost/phpmyadmin/).

You can use phpMyAdmin to create the database user and import the SQL setup files:

1. Open phpMyAdmin.
2. Log in to the local MySQL server.
3. Import `db/schema.sql` first to create the database and tables.
4. Import `db/seed.sql` to load the demo data.

The database connection settings in step 4 must match the MySQL username and password you create.

The local development environment used MySQL/MariaDB on port `3306`.

**Note:** All demo dates are written relative to `NOW()`, so if you reload the seed on the day of the recording the overdue bills and "this month's sales" still line up. Reloading resets everything.

If you change the demo story, run `python db/make_seed.py` to rebuild `db/seed.sql`.

## 4. Start the application

The app reads the database settings from environment variables (defaults in brackets):

`DB_HOST` [localhost], `DB_PORT` [3306], `DB_USER` [root], `DB_PASSWORD` [empty], `DB_NAME` [flooring], `SECRET_KEY`.

```bash
# Mac/Linux
export DB_USER=flooring_app DB_PASSWORD=flooring_pw
python app.py

# Windows PowerShell
$env:DB_USER="flooring_app"; $env:DB_PASSWORD="flooring_pw"
python app.py
```

If port `5000` is already in use, the application can be started on another port. For example, to run it on port `5001`:

```bash
python -c "from app import app; app.run(port=5001)"
```

## 5. Access the website

Open the application in a browser:

- Most's local application: `http://localhost:5000`
- Rifah's local application: `http://localhost:5001`

| Who | Login page | Username | Password |
|---|---|---|---|
| Anna (contractor) | `/anna/login` | `anna` | `anna123` |
| Any client | `/login` | `first.last@example.com` (e.g. `maria.lopez@example.com`) | `password123` |

### Demo clients and what they are there for

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

```text
app.py                         Flask routes (client side, Anna side, bills, reports)
pricing.py                     Quote math: area x (1 + waste%), boxes rounded up
queries.py                     The 10 dashboard queries (website runs these)
make_sqltxt.py                 Writes sql.txt from queries.py
sql.txt                        Dashboard SQL, labeled by query number
db/schema.sql                  CREATE TABLE statements with all constraints
db/seed.sql                     Demo data
db/make_seed.py                 Generator for seed.sql
docs/er-chen-layout-v2.dot      Chen E-R diagram source
docs/er-chen-layout-v2.png      Chen E-R diagram image
docs/er-chen-layout-v2.pdf      Chen E-R diagram PDF
docs/backup/                    Original E-R diagram files
docs/make_pdf.py                Project PDF-generation script
docs/Project2.pdf               Project report PDF
templates/                      HTML pages
static/style.css                Application styling
uploads/                        Client photos are saved here
```

## 7. Contributions

| Project Area | Most Afroz | Rifah Tasniya |
|---|---|---|
| **Part 1: Database Design & Documentation** | - Created the original E-R diagram and designed and implemented the relational database, including tables, schema, and constraints.<br>- Prepared the initial assumptions, relational-schema documentation, and PDF-generation script. | - Refined the E-R diagram using traditional Chen notation to align with course lectures and project requirements.<br>- Expanded the report with entity definitions, relationship constraints, and consolidated assumptions.<br>- Reworked the PDF-generation script, automated relational-schema extraction, and substantially improved report organization, layout, and presentation. |
| **Part 2: Application Development** | - Implemented contractor and client application functionality, including backend workflows for requests, products, quotes, negotiations, orders, billing, disputes, and payments. | - Redeveloped shared application styling and navigation, and redesigned contractor dashboard and client-facing request interfaces.<br>- Added flooring material texture previews, color/sample previews, and estimated material-cost calculations. |
| **Part 3: SQL & Dashboard Analytics** | - Authored all 10 required SQL queries and developed the SQL-driven dashboard business overview and KPI components. | - Led dashboard redevelopment, restructuring its layout and visual design and implementing four analytics charts with supporting data queries. |
| **Project Setup & Demonstration** | - Created and configured the GitHub repository and established the project structure.<br>- Uploaded the final project submission to Canvas. | - Tested application setup on a second laptop.<br>- Recorded and uploaded the project demonstration video to YouTube. |

### Contributions by Both Partners

- Project coordination and task review.
- End-to-end testing and final application review.
- README preparation and review.
- Collaborative demonstration preparation and recording.

--- add vid link to readme and pdf report before final submission ---

**Total time spent working together: 4.5 hours.**