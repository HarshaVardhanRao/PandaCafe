# 🐼 Panda Cafe - POS & Kitchen Display System (KDS)

Panda Cafe is a production-ready Point of Sale (POS) and Kitchen Display System (KDS) designed for restaurant operations. The system is built using **FastAPI (Python)**, **React (TypeScript + Tailwind CSS + Zustand)**, **PostgreSQL**, and **Redis**.

---

## 🏗️ Project Architecture

```text
PandaCafe/
├── backend/              # FastAPI application (Python 3.12+)
│   ├── app/              # Application code (API, Core, DB, Middleware, Models, Schemas, Services)
│   ├── tests/            # Test suite (Unit & Integration tests)
│   ├── alembic/          # Database schema migrations
│   └── seed_db.py        # Seed script for initial catalog, roles, and admin users
├── frontend/
│   ├── pos/             # Cashier POS Client (React + TypeScript + Vite)
│   └── kds/             # Kitchen Order Display Client (React + TypeScript + Vite)
├── docker/              # Nginx reverse proxy & Docker Compose scripts
└── docs/                # Architectural diagrams & specifications
```

---

## 🛠️ Tech Stack & Requirements

* **Backend**: Python 3.12+ (FastAPI, SQLAlchemy ORM, Alembic migrations, ReportLab PDF, standard library `zoneinfo`)
* **POS Frontend**: React 18 (Vite, TypeScript, Tailwind CSS, Zustand state, Axios client)
* **KDS Frontend**: React 18 (Vite, TypeScript, Tailwind CSS, WebSockets)
* **Database**: SQLite (for fast local test rollbacks), PostgreSQL (for persistent production instances)
* **Cache & Real-time**: Redis (caching and notifications)

---

## 🚀 Local Quick Start Guide

### 1. Prerequisites
Ensure you have the following installed on your machine:
* Python 3.12 or higher
* Node.js 18 or higher (with npm)
* Git

### 2. Configure Environment Variables
Copy the configuration template to establish environment boundaries:
```bash
# From the PandaCafe root directory
cp backend/.env.example backend/.env
```
*(The default settings are pre-configured to run with local SQLite database file `test.db` and development credentials).*

---

### 3. Backend Setup

```bash
# Navigate to the backend directory
cd backend

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Windows (CMD):
.\venv\Scripts\activate
# Linux / macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run initial database migrations
alembic upgrade head

# Seed the database (creates default roles, users, and catalog products)
python seed_db.py

# Start the FastAPI reload server
uvicorn app.main:app --reload
```
The backend API is now running at **`http://localhost:8000`** with OpenAPI docs available at **`http://localhost:8000/api/docs`**.

---

### 4. POS Frontend Setup

The POS client allows cashiers to select tables, manage carts, apply loyalty points, process payments, and share simulated receipts.

```bash
# Navigate to the POS frontend folder
cd ../frontend/pos

# Install package dependencies
npm install

# Run the development server
npm run dev
```
The POS terminal will launch at **`http://localhost:5173`**.

---

### 5. KDS Frontend Setup

The KDS client broadcasts active kitchen orders in real-time using WebSockets.

```bash
# Navigate to the KDS frontend folder
cd ../frontend/kds

# Install package dependencies
npm install

# Run the development server
npm run dev
```
The KDS kitchen screen will launch at **`http://localhost:5174`** (or next available port).

---

## 🐳 Running with Docker

Alternatively, spin up the entire production stack (Nginx proxy, PostgreSQL, Redis, FastAPI, POS, KDS) using Docker Compose:

```bash
# From the PandaCafe root directory
docker-compose -f docker/docker-compose.yml up --build -d
```
* **POS Access**: `http://localhost:3000`
* **KDS Access**: `http://localhost:3001`
* **API Docs**: `http://localhost:8000/api/docs`

---

## 🔑 Default Login Credentials

Use the following seeded accounts to log in and check permissions:

| Username | Password | Role | Access Level |
|---|---|---|---|
| **admin** | `Admin@123` | **owner** | Full permissions, including Reports & Analytics |
| **cashier1** | `Cashier@123` | **cashier** | POS operations, Billing, Payments (blocked from Reports) |
| **kitchen1** | `Kitchen@123` | **kitchen** | KDS view operations |

---

## 🧪 Running Tests

A comprehensive integration test suite (115 unit & integration tests) is available to verify billing systems, loyalty points, QR code generations, inventory deductions, and reports arithmetic.

```bash
# Navigate to the backend directory and activate your venv
cd backend

# Run the full test suite
.\venv\Scripts\pytest
```

---

## 📦 Completed Modules Overview

1. **Authentication & Roles (Phase 1)**: JWT auth, hashed passwords (`bcrypt==4.0.1`), and role scopes (Owner, Manager, Cashier, Kitchen, Waiter).
2. **POS Billing & Payments (Phase 2)**: Dynamic tax, split/merge tables, item instructions, and multiple split checkout modes (Cash, Card, UPI).
3. **Kitchen Display System (Phase 3)**: Live websocket broadcasts for preparing, ready, and served order queues.
4. **Inventory Management (Phase 4)**: Raw ingredient recipes mapping, low-stock warnings, and automatic sale deductions.
5. **Customer Loyalty & Self-Order (Phase 5)**: 
   * Earn 1 point per 10 spent on `"completed"` orders; automatic reversions on order cancellations.
   * Quick cashier checkout customer lookups by phone.
   * Public QR code table self-ordering menu creation (`POST /api/v1/self-order`).
   * Simulated Receipt sharing (Email, SMS, and WhatsApp `wa.me` redirections) writing logs to `backend/email_simulation.txt`, `backend/whatsapp_simulation.txt`, and `backend/sms_simulation.txt`.
6. **Reports & Analytics (Phase 6)**: Daily sales reviews, revenue trends, product rankings (top and unsold items), stock movement audit lines, and cashiers shift summaries. Exports to Excel-compatible CSVs and branded PDFs using `reportlab`.
