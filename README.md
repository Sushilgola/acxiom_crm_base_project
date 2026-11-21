# AcxiomCRM — Enterprise Role-Based CRM Platform

AcxiomCRM is a full-featured, role-based Customer Relationship Management (CRM) application built according to the company project specifications and implementation guidelines.

---

## 🛠 Technology Stack

- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap 5, Bootstrap Icons, Chart.js
- **Backend**: Python, Django 6.0, Django REST Framework (DRF)
- **Database**: MySQL (using `PyMySQL` driver with `utf8mb4_unicode_ci` collation) & SQLite portable fallback
- **Authentication & Security**: Django PBKDF2 adaptive password hashing, Anti-CSRF protection, 5-attempt account lockout, session management, append-only security audit trail

---

## 👥 Roles & Permissions Matrix

| Module | Admin | Manager | Sales Executive |
| :--- | :---: | :---: | :---: |
| **Dashboard** | Full Enterprise View | Team-wide Metrics | Assigned Records Only |
| **Customers** | All Customers | Team Customers | Assigned Customers |
| **Leads** | All Leads | Team Leads | Assigned Leads |
| **Opportunities** | All Deals | Team Deals | Assigned Deals |
| **Follow-Ups** | All Tasks | Team Tasks | Assigned Tasks |
| **Activities** | Full Log | Team Log | Assigned Activities |
| **Reporting Center** | All 7 Reports | All 7 Reports | Scoped Sales Reports |
| **User Administration** | Full CRUD & Unlock | No Access | No Access |
| **Audit Log** | Full Audit Trail | Limited CRM Trail | No Access |
| **REST APIs** | Authorized Endpoints | Authorized Endpoints | Scoped Endpoints |

---

## 🚀 Pre-Seeded Demo Accounts

The database comes pre-seeded with role-specific test credentials:

| Role | Email / Username | Password | Access Scope |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin@acxiom.com` / `admin` | `Admin@12345` | Full administration, user management, audit logs, all deals |
| **Manager** | `manager@acxiom.com` / `manager` | `Manager@12345` | Team pipeline, reports, SLA tracking, conversion analytics |
| **Sales Executive** | `sales1@acxiom.com` / `sales1` | `Sales@12345` | Assigned customers, leads, opportunities, follow-ups |
| **Sales Executive 2** | `sales2@acxiom.com` / `sales2` | `Sales@12345` | Assigned customers, leads, opportunities, follow-ups |

*(A one-click credential autofill is also available directly on the login screen for rapid demoing.)*

---

## 🔄 Core Sales Workflow

```
[ Prospective Lead ]
        │
        ▼ (Capture & Assign to Sales Executive)
[ Contact & Discovery ]
        │
        ▼ (Qualify Lead)
[ Convert Lead Workflow ] ──────────────┐
        │                               │
        ▼ (Creates)                     ▼ (Creates)
[ Master Customer Account ]      [ Active Sales Opportunity ]
        │                               │
        ▼                               ▼
[ Schedule Follow-Ups ] ───────► [ Move Pipeline Stage ]
(Call, Demo, Meeting)             (Amount > 0, Win Prob %)
        │                               │
        ▼                               ▼
[ Mark Completed / Log Activity ] [ Close Deal (Won / Lost) ]
        │                               │
        └───────────────────────────────┴────────► [ Dashboard & Reports Update ]
```

---

## ⚡ Quick Start & Installation

### 1. Configure MySQL Database
Open MySQL CLI or MySQL Workbench and execute the script `setup_mysql.sql`:
```bash
mysql -u root -p < setup_mysql.sql
```
Or create the database manually:
```sql
CREATE DATABASE IF NOT EXISTS acxiom_crm CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 2. Configure Environment (`.env`)
Verify the database connection variables in `.env`:
```env
DB_NAME=acxiom_crm
DB_USER=root
DB_PASSWORD=
DB_HOST=127.0.0.1
DB_PORT=3306
USE_SQLITE=False
```
*(If MySQL is not active on your machine, set `USE_SQLITE=True` for portable local development).*

### 3. Run Database Migrations
```bash
python manage.py migrate
```

### 4. Seed Roles, Demo Users, and Realistic CRM Data
```bash
python manage.py seed_crm_data
```

### 5. Launch the Development Server
```bash
python manage.py runserver
```
Open **[http://127.0.0.1:8000/](http://127.0.0.1:8000/)** in your browser.

---

## 🧪 Automated Testing Checklist (All 11 Passed)

To execute the automated verification test suite:
```bash
python manage.py test crm
```

The test suite validates every item specified on Page 6 of the project guide:
1. **Authentication**: Valid login succeeds; invalid credentials are rejected with remaining attempt count; logout terminates session safely.
2. **Anonymous Protection**: Unauthenticated users cannot open protected CRM pages or REST API endpoints.
3. **Role-Based Authorization**: Sales Executives are prevented on the server from accessing user administration or audit logs.
4. **Customer CRUD**: Customer creation, editing, searching, and deactivation work end-to-end.
5. **Duplicate Prevention**: Duplicate customer email and phone number are rejected with validation feedback.
6. **Lead Conversion**: Leads move through `New -> Contacted -> Qualified`, and conversion creates linked Customer & Opportunity records with status marked `Converted`.
7. **Opportunity Business Validations**: Rejects `amount <= 0`, `probability > 100` or `< 0`, and rejects past close date for active deals.
8. **Follow-Up Date Validation**: Rejects follow-up dates earlier than today for new/planned activities.
9. **Dashboard Totals**: Dynamic KPI cards and Chart.js charts reflect database updates in real time.
10. **REST APIs**: Endpoints return standard HTTP status codes (`200`, `201`, `400`, `401`, `403`, `404`) and do not leak passwords or hashes.
11. **Audit Trail**: Append-only log captures `LOGIN`, `FAILED_LOGIN`, `CREATE`, `UPDATE`, `STATUS_CHANGE`, `LEAD_CONVERSION`, and `DELETE`.

---

## 📡 REST API Reference

Interactive API testing and documentation are accessible at **`/api/docs/`**.

| Method | Endpoint | Description | Expected Status |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/auth/login` | Authenticate user, returns session/user DTO | `200` / `400` / `401` / `403` |
| `POST` | `/api/auth/logout` | Terminate session & log audit event | `200` |
| `GET` | `/api/customers` | List & search customers (`?q=term`) | `200` |
| `POST` | `/api/customers` | Create customer with server validation | `201` / `400` |
| `GET` | `/api/customers/{id}` | Retrieve single customer details | `200` / `403` / `404` |
| `PUT` | `/api/customers/{id}` | Update customer record | `200` / `400` / `403` |
| `DELETE` | `/api/customers/{id}` | Delete or deactivate customer | `200` / `403` |
| `GET` | `/api/leads` | List & search prospective leads | `200` |
| `POST` | `/api/leads` | Create prospective lead | `201` / `400` |
| `GET` | `/api/opportunities` | List sales opportunities | `200` |
| `POST` | `/api/opportunities` | Create deal (`Amount > 0`, `CloseDate >= Today`) | `201` / `400` |
| `GET` | `/api/followups` | List scheduled follow-ups & reminders | `200` |
| `POST` | `/api/followups` | Create follow-up task | `201` / `400` |
| `GET` | `/api/reports/pipeline` | Aggregated pipeline metrics & owner breakdown | `200` |

---

## 🎬 Company Demonstration Script (Step-by-Step)

1. **Sign In**: Navigate to `http://127.0.0.1:8000/auth/login/` and click the **Admin** button (`admin@acxiom.com` / `Admin@12345`).
2. **Dashboard Overview**: Show the 8 KPI cards, date filters, and the 3 live Chart.js charts (Pipeline Stages, Lead Status, Monthly Won Revenue).
3. **Capture a Lead**: Go to **Leads -> Capture Lead**, enter contact details, and save.
4. **Qualify & Convert Lead**: In the Lead details view, click **Convert to Customer**. Fill out the customer details and enable "Create an active sales opportunity deal". Save to demonstrate the atomic workflow.
5. **Customer Roster**: View the newly created customer with linked Opportunity and code `CUST-XXXX`.
6. **Schedule Follow-Up**: Schedule a call or demo. Attempt setting a date in the past to demonstrate both **client-side** and **server-side** rejection. Set a valid future date, then click **Complete** to log meeting minutes.
7. **Check Audit Logs**: Navigate to **Administration -> Audit Logs** to show the append-only trail recording logins, creation events, lead conversion, and status changes.
8. **REST API & Postman**: Navigate to **REST APIs (`/api/docs/`)** and use the interactive test console to execute live `GET /api/customers` and `GET /api/reports/pipeline` requests.
