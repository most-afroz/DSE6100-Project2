"""Writes sql.txt from queries.py so the file always matches what the website runs."""
from queries import QUERIES
with open("sql.txt", "w") as f:
    f.write("Project 2 - Anna Johnson Flooring - Dashboard SQL queries (MySQL 8 / MariaDB)\n")
    f.write("Query 3 takes two inputs from the web form: %(year)s and %(month)s\n\n")
    for n, q in QUERIES.items():
        f.write(f"-- =====================================================\n-- Query {n}: {q['title']}\n-- {q['desc']}\n")
        f.write(f"-- =====================================================\n{q['sql'].strip()};\n\n")
print("sql.txt written")
