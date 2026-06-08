# Gokul Cycle & Tyre - Inventory Management System

A production-ready, secure, and responsive Inventory Management System built for Gokul Cycle & Tyre. This system tracks stock in the Main Godown, prevents negative stock, logs a comprehensive audit trail of movements, creates charts, and exports reports to CSV, Excel, or PDF.

---

## 🚀 Key Features

* **Role-Based Access Control (RBAC):** Separate permissions for Administrator (full database control, staff management, catalog deactivation, Flask-Admin panel access) and Staff (view catalog, log stock movements, view transfers, view history logs).
* **Multi-Location Support:** Track separate stock quantities for Godown, Shop, or custom physical locations.
* **Negative Stock Prevention:** Real-time checking and database constraints block transactions from going below zero.
* **Atomic Movements:** Stock-In, Stock-Out, and Stock-Transfers run inside unified database transactions with rollback on failure.
* **Reports Center:** Custom reports for Current Inventory, Low Stock alerts, and Movement logs, exportable to CSV, Excel (XLSX), or PDF.
* **Analytics Dashboard:** Chart.js graphs monitoring weekly trends, value by category, and monthly transactional volume.
* **Flask-Admin Panel:** High-performance, protected console to inspect database tables.

---

## 🛠️ Tech Stack

* **Frontend:** HTML5, CSS3, Bootstrap 5, Vanilla JavaScript, Chart.js
* **Backend:** Python 3.12+, Flask
* **Database:** PostgreSQL (with SQLite fallback for local development)
* **ORM:** SQLAlchemy (Flask-SQLAlchemy)
* **Migrations:** Flask-Migrate (Alembic)
* **Authentication:** Flask-Login
* **Hashed Credentials:** Werkzeug Security
* **Form Validation:** Flask-WTF / WTForms
* **Reporting:** Pandas, Openpyxl, ReportLab

---

## 👥 Seeding & Development User Accounts

When the database is seeded, two default accounts are generated for evaluation and testing:

| Role | Username | Password | Permissions |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin` | `admin123` | Full control, Admin Console, manage staff users, deactivate products |
| **Staff** | `staff` | `staff123` | Log stock movements, transfers, view catalog, view history |

---

## ⚙️ Local Setup Guide

### 1. Prerequisite Environments
Make sure you have **Python 3.12+** installed on your operating system.

### 2. Install Dependencies
Initialize a virtual environment and run the package installations:
```bash
# Create and activate virtual environment
python -m venv venv
source venv/Scripts/activate # On Windows: venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

### 3. Initialize & Seed Database
In development mode, the application automatically creates a local SQLite `project.db` database inside the workspace directory if no PostgreSQL `DATABASE_URL` is set in the environment.

Run the seed script to compile tables, register locations, add users, and import mock products with audit logs:
```bash
python seed.py
```

### 4. Run Application Server
Start the development server:
```bash
python run.py
```
Open [http://localhost:5000](http://localhost:5000) in your browser.

---

## 🐳 Docker Deployment

To spin up the multi-container stack (Flask + PostgreSQL database) with volumes mapping for persistent data:

```bash
# Build images and start containers
docker-compose up --build -d
```

Access the application on port **5000** ([http://localhost:5000](http://localhost:5000)).

---

## ☁️ Production Deployment Guide

### Option 1: Railway / Render (Platform as a Service)
1. Link your GitHub repository.
2. Spin up a **PostgreSQL Database** service.
3. Spin up a **Web Service** linking the database service.
4. Set the environment variables:
   * `SECRET_KEY`: Long, random secret key.
   * `DATABASE_URL`: Connection string provided by the PostgreSQL database.
5. In Render, set the build command to `pip install -r requirements.txt` and start command to `gunicorn run:app`.
6. Run migrations or run `python seed.py` once in the console to seed default users.

### Option 2: Linux VPS (Virtual Private Server)
1. Clone the repository onto your VPS.
2. Use **Docker Compose** to start the app (`docker-compose up -d`).
3. Setup **Nginx** as a reverse proxy pointing to `http://localhost:5000`.
4. Configure an **SSL Certificate** using Let's Encrypt / Certbot (`sudo certbot --nginx`).
