# PandaCafe Quick Reference Guide

## 🚀 Start Here

### Choose Your Setup

**Option A: Docker (Recommended - 2 minutes)**
```bash
cd c:\Users\HVIJA\Downloads\PandaCafe
docker-compose -f docker/docker-compose.yml up -d
# Wait 30 seconds for database initialization
# Access: http://localhost (or http://localhost:3000 for POS)
```

**Option B: Local Development (10 minutes)**
```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
python seed_db.py
uvicorn app.main:app --reload
```

### Login
```
Username: admin
Password: Admin@123
```

## 📍 Where Everything Is

| What | Where |
|------|-------|
| Source Code | `c:\Users\HVIJA\Downloads\PandaCafe\` |
| Backend API | http://localhost:8000/api/v1 |
| API Documentation | http://localhost:8000/api/docs |
| POS Application | http://localhost:3000 |
| KDS Application | http://localhost:3001 |

## 📚 Reading Order

1. **First Time?** → [README.md](README.md)
2. **Want Details?** → [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)
3. **Finding Files?** → [PROJECT_INDEX.md](PROJECT_INDEX.md)
4. **Development Setup?** → [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)
5. **Going to Production?** → [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
6. **Architecture?** → [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
7. **Database Design?** → [docs/DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md)
8. **Build Phase 2?** → [PHASE2_GUIDE.md](PHASE2_GUIDE.md)

## 🔧 Common Tasks

### Start Development
```bash
# Backend
cd backend && uvicorn app.main:app --reload

# POS Frontend
cd frontend/pos && npm install && npm run dev

# KDS Frontend
cd frontend/kds && npm install && npm run dev
```

### Run Tests
```bash
cd backend
pytest tests/ -v              # All tests
pytest tests/test_auth_service.py -v  # Auth tests only
pytest --cov=app             # With coverage
```

### Database
```bash
cd backend
python seed_db.py            # Seed initial data
alembic upgrade head         # Apply migrations
alembic revision --autogenerate -m "description"  # Create migration
```

### Docker
```bash
# Start all services
docker-compose -f docker/docker-compose.yml up -d

# Stop all services
docker-compose -f docker/docker-compose.yml down

# View logs
docker-compose logs -f

# Restart specific service
docker-compose restart backend
```

### Code Quality
```bash
cd backend
black app/                   # Format code
flake8 app/                  # Lint
mypy app/                    # Type check
isort app/                   # Sort imports
```

## 🏗️ Project Structure (Quick View)

```
PandaCafe/
├── backend/                 # FastAPI backend
│   ├── app/api/            # REST endpoints
│   ├── app/models/         # Database models
│   ├── app/services/       # Business logic
│   ├── app/schemas/        # Data validation
│   ├── tests/              # Unit tests
│   └── seed_db.py          # Database seeding
├── frontend/
│   ├── pos/                # POS application
│   └── kds/                # Kitchen display
├── docker/                 # Docker files
├── docs/                   # Documentation
└── alembic/                # Database migrations
```

## 📊 API Endpoints

### Authentication
```
POST   /auth/register          - Register user
POST   /auth/login             - Login
POST   /auth/refresh           - Refresh token
```

### Products
```
POST   /products               - Create product
GET    /products               - List products
GET    /products/{id}          - Get product
PUT    /products/{id}          - Update product
DELETE /products/{id}          - Delete product
```

### Categories
```
POST   /products/categories    - Create category
GET    /products/categories    - List categories
GET    /products/categories/{id} - Get category
PUT    /products/categories/{id} - Update category
DELETE /products/categories/{id} - Delete category
```

[See docs/ARCHITECTURE.md for complete endpoint list]

## 🔐 Default Credentials

```
Username: admin
Password: Admin@123
Role: Owner (full access)
```

## 📋 What's Implemented (Phase 1)

✅ User authentication with JWT  
✅ Role-based access control  
✅ Product catalog management  
✅ Category management  
✅ Product add-ons  
✅ Database schema (20+ tables)  
✅ API documentation  
✅ Unit tests  
✅ Docker setup  
✅ Database migrations  
✅ Input validation  
✅ Error handling  
✅ Logging  

## 📋 What's Next (Phase 2)

📋 Order management  
📋 Billing system  
📋 Payment processing  
📋 Table management  
📋 Thermal printer integration  

[See PHASE2_GUIDE.md for details]

## 🐛 Troubleshooting

### Port Already in Use
```bash
# Find and kill process
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### Database Issues
```bash
# Reset database in Docker
docker-compose -f docker/docker-compose.yml down -v
docker-compose -f docker/docker-compose.yml up -d
```

### Module Not Found
```bash
cd backend
pip install -r requirements.txt
```

### Tests Failing
```bash
cd backend
pytest --tb=short  # Show detailed error
```

## 📞 Quick Help

| Issue | Solution |
|-------|----------|
| 404 Not Found | Check API path in docs |
| 401 Unauthorized | Use valid JWT token |
| Port 8000 in use | Kill process or change port |
| Database error | Run `python seed_db.py` |
| Import error | Run `pip install -r requirements.txt` |
| Test failure | Check database connection |

## 🔗 Important Files

| File | Purpose |
|------|---------|
| `backend/app/main.py` | FastAPI app |
| `backend/app/models/__init__.py` | Database models |
| `backend/app/services/auth_service.py` | Auth logic |
| `backend/app/services/product_service.py` | Product logic |
| `docker-compose.yml` | Docker setup |
| `docs/ARCHITECTURE.md` | System design |

## 📈 Code Statistics

- **Python Code**: 3000+ lines
- **Tests**: 500+ lines  
- **Documentation**: 2000+ lines
- **Configuration**: 500+ lines

## 🎯 Success Criteria

- ✅ Code compiles/runs without errors
- ✅ 80%+ test coverage achieved
- ✅ All API endpoints documented
- ✅ Docker deployment working
- ✅ Database migrations clean
- ✅ Production-ready code structure

## 💡 Pro Tips

1. **Use API Docs** - http://localhost:8000/api/docs for testing
2. **Check Logs** - `docker-compose logs backend` for debugging
3. **Run Tests** - `pytest -v` before committing
4. **Follow Patterns** - Check Phase 1 for code examples
5. **Read Docstrings** - All functions have detailed documentation

## 🚀 Next Steps

1. **Get running**: Choose Docker or Local setup above
2. **Test it**: Visit API docs, try endpoints
3. **Understand it**: Read ARCHITECTURE.md
4. **Continue building**: Follow PHASE2_GUIDE.md

## 📞 Support

- **API Docs**: http://localhost:8000/api/docs
- **Code Examples**: Check `backend/tests/` for test examples
- **Architecture**: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- **Troubleshooting**: [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md#troubleshooting)

---

**Questions?** Check the documentation files above first!  
**Ready to code?** Follow PHASE2_GUIDE.md to continue.  
**Going live?** See DEPLOYMENT.md for production setup.
