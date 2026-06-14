# PandaCafe Deployment Guide

## Docker Deployment

### Prerequisites
- Docker 20.10+
- Docker Compose 2.0+
- 4GB RAM minimum
- 10GB disk space

### Quick Start

#### 1. Clone Repository
```bash
git clone <repo_url>
cd PandaCafe
```

#### 2. Configure Environment
```bash
cp docker/.env.example .env
# Edit .env with your values
```

#### 3. Generate SSL Certificates (Self-signed for development)
```bash
mkdir -p docker/ssl
openssl req -x509 -newkey rsa:4096 -keyout docker/ssl/key.pem \
  -out docker/ssl/cert.pem -days 365 -nodes
```

#### 4. Start Services
```bash
docker-compose -f docker/docker-compose.yml up -d
```

#### 5. Initialize Database
```bash
docker-compose -f docker/docker-compose.yml exec backend \
  python seed_db.py
```

#### 6. Access Applications
- **POS**: http://localhost:3000 (or https://localhost/pos/)
- **KDS**: http://localhost:3001 (or https://localhost/kds/)
- **API Docs**: http://localhost:8000/api/docs
- **API**: http://localhost:8000/api/v1

### Login Credentials (After Seed)
```
Username: admin
Password: Admin@123
```

### Docker Compose Services

```yaml
postgres     - PostgreSQL database
redis        - Redis cache
backend      - FastAPI backend
pos          - React POS app
kds          - React KDS app
nginx        - Reverse proxy & load balancer
```

### Scaling to Multiple Machines

#### Distributed Architecture
```
┌─────────────────┐
│   Load Balancer │
│    (nginx)      │
└────────┬────────┘
         │
    ┌────┴────┬─────────┐
    │          │         │
┌───▼───┐  ┌──▼───┐  ┌──▼───┐
│Backend│  │Backend│  │Backend│
│  #1   │  │  #2   │  │  #3   │
└───┬───┘  └──┬───┘  └──┬───┘
    └────┬────┴─────┬────┘
         │          │
    ┌────▼────┬────▼───┐
    │PostgreSQL         │
    │(Replication)      │
    └────────────────────┘
         │
    ┌────▼────┐
    │  Redis  │
    │ Cluster │
    └─────────┘
```

### Production Deployment

#### 1. Server Requirements
- **CPU**: 4+ cores
- **RAM**: 8GB+
- **Disk**: 100GB SSD
- **OS**: Linux (Ubuntu 22.04 LTS recommended)

#### 2. Environment Variables
```bash
# Database
DATABASE_URL=postgresql://user:password@postgres:5432/pandacafe
DATABASE_POOL_SIZE=30
DATABASE_MAX_OVERFLOW=20

# Redis
REDIS_URL=redis://redis:6379/0

# Security
SECRET_KEY=<random-32-char-string>
ALGORITHM=HS256

# Application
APP_ENV=production
DEBUG=False
LOG_LEVEL=INFO

# CORS
CORS_ORIGINS=["https://yourdomain.com"]

# Email (for bill sharing)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=<your-email>
SMTP_PASSWORD=<app-password>

# AWS S3 (for image storage)
AWS_ACCESS_KEY_ID=<your-key>
AWS_SECRET_ACCESS_KEY=<your-secret>
AWS_S3_BUCKET=pandacafe-prod
```

#### 3. SSL Certificate Setup
```bash
# Using Let's Encrypt with Certbot
docker run --rm -v /etc/letsencrypt:/etc/letsencrypt \
  -v /var/lib/letsencrypt:/var/lib/letsencrypt \
  certbot certbot certonly --standalone \
  -d yourdomain.com --agree-tos -m admin@yourdomain.com
```

#### 4. Database Backup
```bash
# Create backup directory
mkdir -p backups

# Backup PostgreSQL
docker-compose exec postgres pg_dump -U pandacafe pandacafe \
  > backups/pandacafe_$(date +%Y%m%d_%H%M%S).sql

# Automated backup (cron job)
0 2 * * * /path/to/backup.sh
```

#### 5. Monitoring Setup

##### Health Checks
```bash
# Check all services
curl http://localhost/health

# Backend health
curl http://localhost:8000/health

# Database health
docker-compose exec postgres pg_isready
```

##### Log Monitoring
```bash
# View logs
docker-compose logs -f backend

# View specific service logs
docker-compose logs -f postgres
```

##### Metrics (Optional - Prometheus)
```yaml
# Add to docker-compose.yml
prometheus:
  image: prom/prometheus
  volumes:
    - ./docker/prometheus.yml:/etc/prometheus/prometheus.yml
  ports:
    - "9090:9090"
```

#### 6. Upgrade Procedure

```bash
# Pull latest code
git pull origin main

# Build new images
docker-compose -f docker/docker-compose.yml build

# Stop current services
docker-compose -f docker/docker-compose.yml down

# Apply migrations
docker-compose -f docker/docker-compose.yml run backend \
  alembic upgrade head

# Start new services
docker-compose -f docker/docker-compose.yml up -d
```

### Troubleshooting

#### Services Won't Start
```bash
# Check logs
docker-compose logs -f

# Check specific service
docker-compose logs backend

# Rebuild images
docker-compose build --no-cache
```

#### Database Connection Issues
```bash
# Check PostgreSQL
docker-compose exec postgres psql -U pandacafe -d pandacafe -c "\dt"

# Reset database (CAUTION)
docker-compose down -v
docker-compose up -d
```

#### Port Conflicts
```bash
# Change ports in docker-compose.yml
# or use environment variable override
docker-compose -f docker/docker-compose.yml \
  -e BACKEND_PORT=8001 up -d
```

### Production Hardening Checklist

- [ ] Change default passwords
- [ ] Generate strong SECRET_KEY
- [ ] Enable HTTPS with valid certificate
- [ ] Configure firewall rules
- [ ] Set up automated backups
- [ ] Configure log aggregation
- [ ] Set up monitoring and alerts
- [ ] Enable rate limiting
- [ ] Set up WAF rules
- [ ] Configure CDN for static assets
- [ ] Regular security updates
- [ ] Database replication setup
- [ ] Load testing completed
- [ ] Disaster recovery plan in place

### Kubernetes Deployment (Advanced)

Create Kubernetes manifests:
```
k8s/
├── namespace.yaml
├── postgres.yaml
├── redis.yaml
├── backend.yaml
├── pos.yaml
├── kds.yaml
└── nginx-ingress.yaml
```

## Support

For deployment issues, check:
1. [DEVELOPMENT.md](DEVELOPMENT.md) - Development setup
2. [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture
3. Docker logs: `docker-compose logs -f`
4. Application logs: Check `/var/log/pandacafe/`
