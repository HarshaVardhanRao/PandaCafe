# Panda Cafe - POS & Kitchen Display System

A production-ready Point of Sale and Kitchen Display System built with Python/FastAPI, React, PostgreSQL, and Redis.

## 📋 Quick Start

### Prerequisites
- Python 3.13+
- Node.js 18+
- PostgreSQL 15+
- Redis 7+
- Docker & Docker Compose (optional)

### Installation

```bash
# Clone and setup
cd PandaCafe

# Backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head

# Frontend (POS)
cd ../frontend/pos
npm install
npm run dev

# Frontend (KDS)
cd ../frontend/kds
npm install
npm run dev

# Start Backend
cd backend
uvicorn app.main:app --reload
```

## 🏗 Architecture

```
PandaCafe/
├── backend/              # FastAPI application
├── frontend/
│   ├── pos/             # POS Application (React)
│   └── kds/             # Kitchen Display System (React)
├── docker/              # Docker configurations
└── docs/                # Architecture & documentation
```

## 🔐 Security

- JWT Authentication
- Role-Based Access Control (RBAC)
- Password Hashing with bcrypt
- API Rate Limiting
- Audit Logging
- Secure Secrets Management

## 📦 Core Features

- ✅ Authentication & Authorization
- ✅ Product Management
- ✅ Table Management
- ✅ Order Management
- ✅ POS Billing System
- ✅ Payment Processing
- ✅ Thermal Printer Integration
- ✅ Kitchen Display System
- ✅ Inventory Management
- ✅ Customer Management
- ✅ Reports & Analytics
- ✅ Shift Management
- ✅ Offline Support
- ✅ Real-time Notifications

## 🚀 Deployment

Docker-based deployment with:
- nginx (reverse proxy)
- PostgreSQL (database)
- Redis (caching/sessions)
- FastAPI backend
- React frontends

See [DEPLOYMENT.md](docs/DEPLOYMENT.md) for details.

## 📚 Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Database Schema](docs/DATABASE_SCHEMA.md)
- [API Documentation](docs/API.md)
- [Development Guide](docs/DEVELOPMENT.md)
- [Deployment Guide](docs/DEPLOYMENT.md)

## 📞 Support

For issues or questions, contact the development team.

## 📄 License

All rights reserved.
