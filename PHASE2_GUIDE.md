# Phase 2: POS Billing System - Getting Started

This guide explains how to continue building the POS Billing System based on Phase 1 foundation.

## What's Already in Place (Phase 1)

✅ Authentication system with JWT tokens  
✅ Product catalog management  
✅ Database models for orders, tables, customers, payments  
✅ Service-oriented architecture pattern  
✅ API endpoint structure  
✅ Testing framework  
✅ Docker environment  

## Phase 2 Deliverables

### 1. Order Management API

```python
# Orders Endpoints to implement:
POST   /api/v1/orders              - Create order
GET    /api/v1/orders              - List orders (with filters)
GET    /api/v1/orders/{id}         - Get order details
PATCH  /api/v1/orders/{id}         - Update order
DELETE /api/v1/orders/{id}         - Cancel order
PATCH  /api/v1/orders/{id}/hold    - Hold order
PATCH  /api/v1/orders/{id}/resume  - Resume order
POST   /api/v1/orders/{id}/items   - Add item to order
DELETE /api/v1/orders/{id}/items/{item_id} - Remove item
```

### 2. Billing Service

**BillingService** to implement:
- Add items to cart
- Calculate subtotal
- Apply tax calculation
- Apply discounts
- Calculate final total
- Generate bill summary
- Handle split payments

### 3. Payment Processing

**PaymentService** to implement:
- Process cash payment
- Process UPI payment
- Process card payment
- Split payment handling
- Payment status tracking
- Transaction recording

### 4. Table Management

**TableService** to implement:
- Create/update tables
- Set table status (available, occupied, reserved, cleaning)
- Link tables to orders
- Merge tables
- Split tables

### 5. Bill Printing

**PrinterService** integration:
- Generate bill in ESC/POS format
- Send to thermal printer
- Handle printer errors
- Reprint functionality

## Step-by-Step Implementation Plan

### Step 1: Create Billing Schemas

Create `app/schemas/order.py`:
```python
# OrderCreateRequest
# OrderItemAddRequest
# OrderResponse
# BillingResponse
# PaymentRequest
```

### Step 2: Implement OrderService

Create `app/services/order_service.py`:
```python
class OrderService:
    @staticmethod
    def create_order(db, request) -> Order:
        # Generate order number
        # Create order
        # Return order
    
    @staticmethod
    def add_item_to_order(db, order_id, product_id, quantity) -> OrderItem:
        # Add item
        # Update order totals
    
    # ... other methods
```

### Step 3: Implement BillingService

Create `app/services/billing_service.py`:
```python
class BillingService:
    @staticmethod
    def calculate_totals(order) -> dict:
        # Calculate subtotal
        # Calculate tax
        # Apply discounts
        # Return totals
    
    @staticmethod
    def generate_bill(order) -> dict:
        # Format bill data
        # Return bill
```

### Step 4: Implement PaymentService

Create `app/services/payment_service.py`:
```python
class PaymentService:
    @staticmethod
    def process_payment(db, order_id, request) -> Payment:
        # Process payment
        # Update order status
        # Record transaction
        # Return payment
```

### Step 5: Create API Endpoints

Create `app/api/v1/endpoints/order.py`:
```python
# Implement order endpoints
# Use services for business logic
# Return appropriate responses
```

### Step 6: Create Tests

Create `tests/test_order_service.py`:
```python
# Test order creation
# Test item addition
# Test billing calculation
# Test payment processing
```

### Step 7: Database Migration

Update `alembic/versions/002_phase2_orders.py`:
```python
# Create tables for Phase 2 if not already present
# All tables are already created in Phase 1
```

### Step 8: Frontend Integration

In `frontend/pos/src/`:
- Create order form component
- Create cart component
- Create billing display
- Create payment interface

## Code Structure to Follow

```
app/
├── schemas/
│   ├── order.py          (new)
│   ├── payment.py        (new)
│   └── billing.py        (new)
├── services/
│   ├── order_service.py        (new)
│   ├── payment_service.py       (new)
│   ├── billing_service.py       (new)
│   └── table_service.py         (new)
├── api/v1/endpoints/
│   ├── order.py          (new)
│   ├── payment.py        (new)
│   └── billing.py        (new)
└── models/
    └── __init__.py       (models already exist)
```

## Running Phase 2 Development

```bash
# Start backend
cd backend
uvicorn app.main:app --reload

# In another terminal, run tests
pytest tests/ -v

# Development cycle:
# 1. Write test
# 2. Implement service
# 3. Create schema
# 4. Add endpoint
# 5. Test API with http://localhost:8000/api/docs
```

## Database Tables Already Created

Phase 1 created all necessary tables:
- ✅ `tables` - Restaurant tables
- ✅ `orders` - Order records
- ✅ `order_items` - Line items
- ✅ `customers` - Customer data
- ✅ `payments` - Payment records
- ✅ `discounts` - Discount system
- ✅ `inventory_items` - Stock tracking
- ✅ `recipes` - Recipe definitions

No new migrations needed, just use existing models.

## Estimated Time

- Services: 3 days
- Schemas & Validation: 1 day
- API Endpoints: 2 days
- Testing: 2 days
- Frontend: 3 days
- **Total: 1-2 weeks**

## Tips

1. **Reuse Patterns**: Follow same service/endpoint structure as Phase 1
2. **Test First**: Write tests before implementation
3. **Use Models**: All SQLAlchemy models already exist
4. **Type Hints**: Keep full type annotations
5. **Documentation**: Keep docstrings updated
6. **Error Handling**: Follow Phase 1 error patterns

## Integration Points

Phase 2 connects to:
- Phase 1: Authentication & Products (✅ done)
- Phase 3: Kitchen Display (order routing)
- Phase 4: Inventory (auto-deduction)
- Phase 7: Printer (bill printing)

## Common Patterns

```python
# Service method pattern
@staticmethod
def create_order(db: Session, request: OrderCreateRequest) -> Order:
    """Create a new order."""
    # Validation
    if not product:
        raise ValueError("Product not found")
    
    # Create object
    order = Order(...)
    db.add(order)
    db.commit()
    
    logger.info(f"Order created: {order.id}")
    return order

# Endpoint pattern
@router.post("", response_model=OrderResponse, status_code=201)
def create_order(request: OrderCreateRequest, db: Session = Depends(get_db)):
    """Create a new order."""
    try:
        order = OrderService.create_order(db, request)
        return order
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

## Debugging

- **Check logs**: `docker-compose logs -f backend`
- **Check tests**: `pytest tests/ -v`
- **API Docs**: http://localhost:8000/api/docs
- **Database**: `docker-compose exec postgres psql -U pandacafe -d pandacafe`

## Next Phase After Phase 2

Once billing is complete:
- Phase 3: Kitchen Display System (WebSocket)
- Order routing to kitchen
- Real-time status updates
- KOT printing

---

**Ready to start?** Create the first service file and write tests!
