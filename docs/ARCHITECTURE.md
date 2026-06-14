# PandaCafe Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Client Layer                             │
├──────────────────────┬──────────────────────┬────────────────┤
│   POS Application    │   Kitchen Display    │   Admin Portal │
│   (React + TS)       │   (React + TS)       │   (React + TS) │
├──────────────────────┴──────────────────────┴────────────────┤
│                    API Layer (WebSocket/HTTP)                │
├─────────────────────────────────────────────────────────────┤
│              nginx (Reverse Proxy & Load Balancer)          │
├─────────────────────────────────────────────────────────────┤
│              FastAPI Backend (Python 3.13+)                 │
│  ├── Authentication Service                                 │
│  ├── Order Service                                           │
│  ├── Billing Service                                         │
│  ├── Inventory Service                                       │
│  ├── Kitchen Service                                         │
│  ├── Printer Service                                         │
│  ├── Report Service                                          │
│  └── Notification Service                                    │
├────────────────────┬──────────────────┬──────────────────────┤
│   PostgreSQL       │   Redis Cache    │   File Storage       │
│   (Primary DB)     │   (Sessions)     │   (Images, PDFs)     │
└────────────────────┴──────────────────┴──────────────────────┘
```

## Layered Architecture

### 1. **Presentation Layer**
- **POS Application**: React-based tablet/desktop interface for cashiers and waiters
- **Kitchen Display System**: Real-time order display for kitchen staff
- **Admin Portal**: Management and reporting dashboard

### 2. **API Layer**
- **FastAPI Framework**: RESTful APIs with OpenAPI documentation
- **WebSocket Support**: Real-time updates for KDS and order status
- **API Versioning**: /api/v1/ structure for future compatibility

### 3. **Business Logic Layer**

#### Service-Oriented Architecture:
```
AuthService
├── User authentication
├── JWT token management
├── Password management
└── Permission validation

OrderService
├── Order creation/modification
├── Order status tracking
├── Order history

BillingService
├── Cart management
├── Tax calculation
├── Discount application
├── Bill generation

PaymentService
├── Payment processing
├── Transaction recording
├── Split payments

InventoryService
├── Stock tracking
├── Recipe ingredient deduction
├── Low stock alerts

KitchenService
├── Order routing to kitchen
├── KOT generation
├── Order status updates

PrinterService
├── Thermal printer communication
├── Bill printing
├── KOT printing
├── Test printing

ReportService
├── Sales reports
├── Revenue analysis
├── Inventory reports
└── Employee reports

NotificationService
├── Real-time alerts
├── Email notifications
├── SMS/WhatsApp (optional)
└── Audit logging
```

### 4. **Data Access Layer**
- **SQLAlchemy ORM**: Database abstraction
- **Alembic**: Database migrations
- **Connection Pooling**: Efficient database connection management
- **Query Optimization**: Indexes and efficient queries

### 5. **Infrastructure Layer**
- **PostgreSQL**: Primary relational database
- **Redis**: Session management and caching
- **Docker**: Containerization
- **nginx**: Reverse proxy and load balancing

## Data Flow

### Order Creation Flow:
```
1. POS App → Backend API
   - Create order with items
2. Backend → Database
   - Save order, generate order ID
3. Backend → Kitchen Service
   - Generate KOT, route to printer/KDS
4. Backend → Redis Cache
   - Cache order status for quick lookup
5. Backend → WebSocket
   - Notify KDS about new order
```

### Billing Flow:
```
1. POS App → Billing Service
   - Submit cart items
2. Billing Service → Inventory Check
   - Verify product availability
3. Billing Service → Tax Calculator
   - Calculate taxes
4. Billing Service → Discount Processor
   - Apply discounts
5. Billing Service → Payment Service
   - Process payment
6. Billing Service → Printer Service
   - Print bill
7. Billing Service → Database
   - Record transaction
```

### KDS Real-time Updates:
```
1. Order Status Change
2. Backend → Redis Pub/Sub
3. Redis → All Connected KDS Clients
4. KDS Frontend Update Display
```

## Security Architecture

```
┌─────────────┐
│  Client     │
└──────┬──────┘
       │ HTTPS + CORS
┌──────▼──────────────────┐
│ API Endpoint            │
├─────────────────────────┤
│ Rate Limiting           │
│ JWT Validation          │
└──────┬──────────────────┘
       │
┌──────▼──────────────────┐
│ Authorization Layer     │
├─────────────────────────┤
│ Role-Based Access       │
│ Resource Ownership      │
└──────┬──────────────────┘
       │
┌──────▼──────────────────┐
│ Business Logic          │
├─────────────────────────┤
│ Input Validation        │
│ Data Sanitization       │
└──────┬──────────────────┘
       │
┌──────▼──────────────────┐
│ Database                │
├─────────────────────────┤
│ Parameterized Queries   │
│ Foreign Key Constraints │
└─────────────────────────┘

Parallel: Audit Logging at Each Step
```

## Deployment Architecture

```
┌────────────────────────────────────────────────┐
│         Docker Compose Network                │
├────────────────────────────────────────────────┤
│ ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│ │ Frontend │  │ Backend  │  │ nginx    │    │
│ │ Container│  │Container │  │Container │    │
│ └─────┬────┘  └────┬─────┘  └─────┬────┘    │
│       │            │              │          │
│ ┌─────▼─────────────▼──────────────▼─────┐  │
│ │    Shared Network (pos-net)            │  │
│ └───────────────────────────────────────┘  │
│ ┌──────────┐         ┌──────────┐         │
│ │PostgreSQL│         │ Redis    │         │
│ │Container │         │Container │         │
│ └──────────┘         └──────────┘         │
└────────────────────────────────────────────────┘
```

## Scalability Considerations

1. **Horizontal Scaling**:
   - Multiple backend instances behind load balancer
   - Redis for shared session management
   - Database replication for read scaling

2. **Caching Strategy**:
   - Product catalog in Redis
   - Order status in Redis
   - Session management in Redis

3. **Database Optimization**:
   - Connection pooling
   - Query indexing
   - Async operations where possible

4. **Frontend Optimization**:
   - Lazy loading
   - Code splitting
   - Image optimization

## Monitoring & Observability

- Application logs to centralized system
- Database query performance monitoring
- API response time tracking
- Error tracking and reporting
- User action audit logging
- System health checks

## Offline Support

```
┌─────────────┐
│  POS App    │ (No internet)
├─────────────┤
│ Local Queue │──┐
└─────────────┘  │
     │           │
     ├─ Orders  ─┼─→ Stored in IndexedDB
     ├─ Payments─┤
     └─ Logs    ─┘

When Online:
Sync Queue → Backend → Database
```

## Technology Rationale

| Component | Choice | Reason |
|-----------|--------|--------|
| Backend | FastAPI | Fast, async, automatic docs, type hints |
| Database | PostgreSQL | ACID compliance, complex queries, reliability |
| Caching | Redis | Session management, fast lookups, Pub/Sub |
| Frontend | React | Large ecosystem, reusable components, performance |
| State Management | Context API + Redux | Centralized state for complex app |
| Styling | TailwindCSS | Utility-first, fast development, customizable |
| Build Tool | Vite | Fast builds, modern ESM support |
| Deployment | Docker | Consistent environments, easy scaling |
| Migrations | Alembic | Version control for schema, rollback capability |
