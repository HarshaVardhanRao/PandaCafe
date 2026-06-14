# PandaCafe Development Guide

## Backend Development

### Prerequisites

- Python 3.13+
- PostgreSQL 15+
- Redis 7+
- Git

### Local Setup

#### 1. Clone Repository
```bash
cd PandaCafe/backend
```

#### 2. Create Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

#### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

#### 4. Configure Environment
```bash
# Copy example env
cp .env.example .env

# Edit .env with your database credentials
DATABASE_URL=postgresql://user:password@localhost:5432/pandacafe
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-secret-key-min-32-chars
```

#### 5. Database Setup

```bash
# Create PostgreSQL database
createdb pandacafe

# Run migrations
alembic upgrade head

# Seed initial data
python seed_db.py
```

#### 6. Run Development Server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Visit `http://localhost:8000/api/docs` for interactive API documentation.

### Running Tests

```bash
# Run all tests with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_auth.py

# Run with verbose output
pytest -v

# Run specific test
pytest tests/test_auth.py::test_user_registration -v
```

### Project Structure

```
backend/
├── app/
│   ├── api/v1/
│   │   └── endpoints/
│   │       ├── auth.py
│   │       ├── product.py
│   │       └── ...
│   ├── core/
│   │   ├── config.py          # Settings
│   │   └── security.py         # JWT & passwords
│   ├── db/
│   │   └── database.py        # Database connection
│   ├── middleware/
│   │   └── auth.py            # Auth middleware
│   ├── models/
│   │   └── __init__.py        # SQLAlchemy models
│   ├── schemas/
│   │   ├── auth.py            # Pydantic schemas
│   │   └── product.py
│   ├── services/
│   │   ├── auth_service.py
│   │   └── product_service.py
│   └── main.py                # FastAPI app
├── alembic/                   # Database migrations
├── tests/                     # Test suite
├── requirements.txt           # Dependencies
├── .env.example              # Environment variables
└── seed_db.py                # Initial data seeding
```

### Code Standards

#### Naming Conventions
- **Models**: PascalCase (e.g., `User`, `Product`)
- **Functions**: snake_case (e.g., `get_user_by_id`)
- **Constants**: UPPER_SNAKE_CASE
- **Database**: snake_case

#### Type Hints
All functions should have type hints:
```python
def get_user(user_id: UUID, db: Session) -> Optional[User]:
    """Get user by ID."""
    return db.query(User).filter(User.id == user_id).first()
```

#### Docstrings
Use Google-style docstrings:
```python
def create_product(db: Session, request: ProductCreateRequest) -> Product:
    """
    Create a new product.
    
    Args:
        db: Database session
        request: Product creation request data
        
    Returns:
        Created product
        
    Raises:
        ValueError: If SKU already exists
    """
```

#### Error Handling
```python
try:
    # Do something
    pass
except ValueError as e:
    logger.error(f"Validation error: {str(e)}")
    raise HTTPException(status_code=400, detail=str(e))
except Exception as e:
    logger.error(f"Unexpected error: {str(e)}")
    raise HTTPException(status_code=500, detail="Internal server error")
```

### API Design Patterns

#### Endpoints
- **GET** `/resource` - List resources
- **GET** `/resource/{id}` - Get single resource
- **POST** `/resource` - Create resource
- **PUT** `/resource/{id}` - Full update
- **PATCH** `/resource/{id}` - Partial update
- **DELETE** `/resource/{id}` - Delete resource

#### Response Codes
- `200 OK` - Successful GET/PUT/PATCH
- `201 Created` - Successful POST
- `204 No Content` - Successful DELETE
- `400 Bad Request` - Invalid input
- `401 Unauthorized` - Missing/invalid auth
- `403 Forbidden` - Permission denied
- `404 Not Found` - Resource not found
- `500 Internal Server Error`

#### Error Response Format
```json
{
    "detail": "Error message describing what went wrong"
}
```

### Database Conventions

#### Timestamps
All tables should include:
```python
created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
```

#### Soft Deletes
Instead of hard delete:
```python
deleted_at = Column(DateTime(timezone=True), nullable=True)

# In queries
query = db.query(Model).filter(Model.deleted_at.is_(None))
```

#### Foreign Keys
```python
user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
user = relationship("User", back_populates="orders")
```

### Git Workflow

#### Branch Naming
- `feature/feature-name` - New features
- `fix/bug-name` - Bug fixes
- `docs/doc-name` - Documentation
- `refactor/refactor-name` - Code refactoring

#### Commit Messages
```
type: subject line (max 50 chars)

body (max 72 chars per line)

Fixes #issue_number
```

Types: feat, fix, docs, style, refactor, perf, test

### Common Commands

```bash
# Format code
black app/

# Lint code
flake8 app/

# Type checking
mypy app/

# Sort imports
isort app/

# Run server with auto-reload
uvicorn app.main:app --reload

# Run tests with coverage
pytest --cov=app

# Generate new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback last migration
alembic downgrade -1
```

## Frontend Development

### Prerequisites
- Node.js 18+
- npm or yarn

### POS Application Setup

```bash
cd frontend/pos
npm install
npm run dev
```

Visit `http://localhost:3000`

### KDS Application Setup

```bash
cd frontend/kds
npm install
npm run dev
```

Visit `http://localhost:3001`

### Build for Production

```bash
# POS
cd frontend/pos
npm run build

# KDS
cd frontend/kds
npm run build
```

## Troubleshooting

### Database Connection Issues
```bash
# Check PostgreSQL is running
psql -U pandacafe -d pandacafe

# Check tables exist
\dt
```

### Alembic Issues
```bash
# Downgrade to specific revision
alembic downgrade <revision_id>

# Check current migration status
alembic current

# View migration history
alembic history
```

### Port Already in Use
```bash
# Find and kill process on port 8000
lsof -i :8000
kill -9 <PID>
```

## Performance Tips

1. **Database Queries**
   - Use `lazy=False` for relationships you always need
   - Add indexes on frequently queried columns
   - Use pagination for large result sets

2. **Caching**
   - Cache product catalog in Redis
   - Cache frequently accessed settings
   - Use TTL for temporary data

3. **API Performance**
   - Return only needed fields
   - Implement pagination
   - Use appropriate HTTP status codes

4. **Frontend**
   - Code splitting
   - Lazy loading
   - Image optimization
   - Minimize bundle size

## Security Checklist

- [ ] Change SECRET_KEY in production
- [ ] Use strong database passwords
- [ ] Enable HTTPS
- [ ] Set secure CORS origins
- [ ] Enable rate limiting
- [ ] Regular dependency updates
- [ ] Input validation on all endpoints
- [ ] SQL injection prevention (using ORM)
- [ ] CSRF protection
- [ ] Secure password storage

## Support & Documentation

- API Docs: http://localhost:8000/api/docs
- OpenAPI Schema: http://localhost:8000/api/openapi.json
- Architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- Database Schema: [docs/DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md)
