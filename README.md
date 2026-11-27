# AdventureWorks Reporting System

A role-based Django web application that reports on the **AdventureWorks2019** sample database (SQL Server).
It provides four report modules and a dashboard, with department-scoped access control and an audit log.

> Group 1 DATAOPT · Benilde SMIT · Instructor: Engr. Bob Mathew D. Sunga

## Modules
| Module | What it shows |
|---|---|
| Sales | Sales by year, territory, product category |
| Customer Profile | Top customers, customer type, orders and sales |
| Revenue & Loss | Revenue vs. estimated cost and profit/loss per year |
| Cost | COGS, purchasing spend, manufacturing cost, top vendors/products |

Each module has KPI cards, a year-range filter, charts (Chart.js), searchable/sortable tables (DataTables) and PDF export.

## Roles (RBAC)
| Role | Access |
|---|---|
| Administrator | All modules, all users, audit log for all departments |
| Manager | Own department's module, manages own team (create/edit/deactivate), audit log of own department |
| Supervisor | Own department's module, read-only view of own team |
| Employee | Own department's module only |

Access is enforced in the backend (class-based view mixins), not only by hiding menu items. Unauthorized requests return a 403 page and are written to the audit log.

## Requirements
- Python 3.13
- SQL Server (Express is fine) with the **AdventureWorks2019** database restored
- Microsoft **ODBC Driver 18 for SQL Server**
- A read-only SQL login for the app (e.g. `aw_reader` with the `db_datareader` role)
- *(Optional, for PDF export on Windows)* GTK/Pango runtime for WeasyPrint

## Setup
```bash
# 1. Clone and enter the project
git clone https://github.com/jvnebenilde/awreports.git
cd awreports
git checkout Gbranch

# 2. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

# 3. Install dependencies
pip install -r requirements.txt
pip install weasyprint          # needed for PDF export

# 4. Configure environment variables
copy .env.example .env          # Windows  (cp .env.example .env on macOS/Linux)
# then edit .env with your own values

# 5. Create Django's own tables (SQLite) and an admin account
python manage.py migrate
python manage.py createsuperuser

# 6. Run
python manage.py runserver
```
Open http://127.0.0.1:8000/ and sign in.

### `.env` settings
| Key | Meaning |
|---|---|
| `SECRET_KEY` | Django secret key (generate your own, never reuse) |
| `DEBUG` | `True` for local development, `False` otherwise |
| `AW_DB_NAME` | `AdventureWorks2019` |
| `AW_DB_USER` / `AW_DB_PASSWORD` | Read-only SQL login |
| `AW_DB_HOST` | e.g. `localhost\SQLEXPRESS` |
| `AW_DB_PORT` | Leave empty for a named instance |

Generate a secret key:
```bash
python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"
```

### Creating users
Sign in at `/admin/` as the superuser to create accounts, or use **My team** (Manager) to add employees and supervisors to the manager's own department. Each non-admin user needs a **role** and a **department** (sales, customer, revenue, cost).

### PDF export on Windows
WeasyPrint needs the GTK/Pango libraries. Install [MSYS2](https://www.msys2.org/), then in the MSYS2 terminal:
```bash
pacman -S mingw-w64-x86_64-pango
```
and in PowerShell: `setx WEASYPRINT_DLL_DIRECTORIES "C:\msys64\mingw64\bin"`, then restart the terminal/IDE.

## Architecture
- **Two databases:** AdventureWorks (SQL Server, read-only, via `mssql-django`) for report data; SQLite for Django's own tables (users, sessions, audit events). A database router prevents migrations from touching AdventureWorks.
- **Apps:** `accounts` (users, roles, permissions, team management), `reports` (views + `services/` with the SQL for each module), `audit` (append-only event log, signals, middleware).
- **Audit events:** login, logout, failed login, report viewed, report printed, access denied, user created/deactivated/reactivated.

## Tests
```bash
python manage.py test accounts -v 2
```
Covers login, role-based module access, year filter, team management and audit logging (26 tests).

## Known limitations
- 2011 and 2014 are partial years in AdventureWorks, so year-over-year comparisons for those years are incomplete.
- Estimated profit uses `LineTotal − StandardCost × OrderQty`; it is an estimate, not accounting profit.
- Many uncategorized products have $0 cost and price; they are non-sold parts, not zero-profit items.

## Security notes
- Never commit `.env` or `db.sqlite3`.
- Use a read-only SQL login for the app.
