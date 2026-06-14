# PandaCafe Database Schema

## Overview

Production-grade normalized schema with:
- Foreign key relationships
- Proper indexing
- Constraints
- Soft deletes for data preservation
- Audit columns

## Entity Relationship Diagram

```
┌─────────────┐
│    users    │────────┐
└─────────────┘        │
       │               │
       │         ┌─────┴──────────┐
       │         │                │
   ┌───▼────┐  ┌─▼────────────┐ ┌▼──────────┐
   │ shifts │  │   orders     │ │ audit_logs│
   └────────┘  └────┬─────────┘ └───────────┘
                    │
              ┌─────▼────────┐
              │ order_items  │
              ├──────────────┤
              │ - product_id │
              │ - quantity   │
              └──────────────┘
                    │
              ┌─────▼──────────┐
              │   products     │◄──────┐
              ├────────────────┤       │
              │ - category_id  │   ┌───┴──────────┐
              │ - price        │   │  categories  │
              └────────────────┘   └──────────────┘
                                           │
                    ┌──────────────────────┴──────┐
                    │                             │
              ┌─────▼──────────┐          ┌──────▼──────┐
              │  inventory     │          │   recipes   │
              │  _items        │          └─────────────┘
              └────────────────┘                │
                                          ┌─────▼────────────┐
                                          │ recipe_ingredients│
                                          └──────────────────┘

         ┌──────────────────────────────────────┐
         │          Other Core Tables           │
         ├──────────────────────────────────────┤
         │ - tables          (dine-in tables)   │
         │ - customers       (loyalty)          │
         │ - payments        (transactions)     │
         │ - discounts       (coupon system)    │
         │ - printers        (device setup)     │
         │ - notifications   (alerts)           │
         └──────────────────────────────────────┘
```

## Table Definitions

### 1. Users
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    phone_number VARCHAR(20),
    role_id UUID NOT NULL,
    status VARCHAR(20) DEFAULT 'active', -- active, inactive, suspended
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP NULL,
    FOREIGN KEY (role_id) REFERENCES roles(id)
);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
```

### 2. Roles
```sql
CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) UNIQUE NOT NULL, -- owner, manager, cashier, kitchen, waiter
    description TEXT,
    permissions JSONB DEFAULT '[]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 3. Categories
```sql
CREATE TABLE categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    image_url VARCHAR(500),
    display_order INT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP NULL,
    CONSTRAINT unique_category_name UNIQUE(name, deleted_at)
);
```

### 4. Products
```sql
CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sku VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(150) NOT NULL,
    description TEXT,
    category_id UUID NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    tax_percent DECIMAL(5, 2) DEFAULT 0,
    image_url VARCHAR(500),
    preparation_time_minutes INT DEFAULT 0,
    is_available BOOLEAN DEFAULT TRUE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP NULL,
    FOREIGN KEY (category_id) REFERENCES categories(id),
    CONSTRAINT unique_product_sku UNIQUE(sku, deleted_at)
);
CREATE INDEX idx_products_category_id ON products(category_id);
CREATE INDEX idx_products_is_available ON products(is_available);
```

### 5. Product Add-ons
```sql
CREATE TABLE product_addons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL,
    addon_name VARCHAR(100) NOT NULL,
    addon_price DECIMAL(10, 2) NOT NULL,
    is_available BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);
```

### 6. Tables
```sql
CREATE TABLE tables (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    table_number INT NOT NULL,
    capacity INT NOT NULL,
    location VARCHAR(100),
    status VARCHAR(20) DEFAULT 'available', -- available, occupied, reserved, cleaning
    current_order_id UUID,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP NULL,
    CONSTRAINT unique_table_number UNIQUE(table_number, deleted_at),
    FOREIGN KEY (current_order_id) REFERENCES orders(id) ON DELETE SET NULL
);
CREATE INDEX idx_tables_status ON tables(status);
```

### 7. Customers
```sql
CREATE TABLE customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone_number VARCHAR(20) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE,
    name VARCHAR(100) NOT NULL,
    loyalty_points INT DEFAULT 0,
    total_spent DECIMAL(15, 2) DEFAULT 0,
    visit_count INT DEFAULT 0,
    last_visit TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP NULL
);
CREATE INDEX idx_customers_phone ON customers(phone_number);
CREATE INDEX idx_customers_email ON customers(email);
```

### 8. Orders
```sql
CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_number VARCHAR(20) UNIQUE NOT NULL,
    order_type VARCHAR(20) NOT NULL, -- dine_in, take_away, delivery
    table_id UUID,
    customer_id UUID,
    cashier_id UUID NOT NULL,
    status VARCHAR(20) DEFAULT 'pending', 
    -- pending, accepted, preparing, ready, served, completed, cancelled
    subtotal DECIMAL(15, 2) DEFAULT 0,
    tax_amount DECIMAL(15, 2) DEFAULT 0,
    discount_amount DECIMAL(15, 2) DEFAULT 0,
    total_amount DECIMAL(15, 2) DEFAULT 0,
    notes TEXT,
    is_hold BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    cancelled_at TIMESTAMP,
    FOREIGN KEY (table_id) REFERENCES tables(id) ON DELETE SET NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE SET NULL,
    FOREIGN KEY (cashier_id) REFERENCES users(id)
);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_table_id ON orders(table_id);
CREATE INDEX idx_orders_cashier_id ON orders(cashier_id);
CREATE INDEX idx_orders_created_at ON orders(created_at);
```

### 9. Order Items
```sql
CREATE TABLE order_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL,
    product_id UUID NOT NULL,
    quantity INT NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    tax_percent DECIMAL(5, 2) DEFAULT 0,
    item_total DECIMAL(15, 2) NOT NULL,
    special_notes TEXT,
    is_cancelled BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id)
);
CREATE INDEX idx_order_items_order_id ON order_items(order_id);
```

### 10. Payments
```sql
CREATE TABLE payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL,
    amount DECIMAL(15, 2) NOT NULL,
    payment_method VARCHAR(20) NOT NULL, -- cash, upi, card, split
    transaction_id VARCHAR(100),
    payment_status VARCHAR(20) DEFAULT 'completed', 
    -- pending, completed, failed, refunded
    reference_number VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
);
CREATE INDEX idx_payments_order_id ON payments(order_id);
CREATE INDEX idx_payments_created_at ON payments(created_at);
```

### 11. Inventory Items
```sql
CREATE TABLE inventory_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID UNIQUE,
    item_name VARCHAR(100) NOT NULL,
    unit VARCHAR(20) NOT NULL, -- ml, g, pieces, etc.
    current_quantity DECIMAL(10, 2) NOT NULL DEFAULT 0,
    reorder_level DECIMAL(10, 2) DEFAULT 0,
    reorder_quantity DECIMAL(10, 2) DEFAULT 0,
    unit_cost DECIMAL(10, 2),
    supplier_id UUID,
    last_stock_check TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE SET NULL
);
CREATE INDEX idx_inventory_product_id ON inventory_items(product_id);
```

### 12. Inventory Transactions
```sql
CREATE TABLE inventory_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    inventory_item_id UUID NOT NULL,
    transaction_type VARCHAR(20) NOT NULL, 
    -- stock_in, stock_out, purchase, waste, adjustment
    quantity DECIMAL(10, 2) NOT NULL,
    reference_type VARCHAR(50), -- order_id, purchase_id, manual
    reference_id UUID,
    notes TEXT,
    created_by UUID NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (inventory_item_id) REFERENCES inventory_items(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES users(id)
);
CREATE INDEX idx_inventory_transactions_item_id ON inventory_transactions(inventory_item_id);
CREATE INDEX idx_inventory_transactions_created_at ON inventory_transactions(created_at);
```

### 13. Recipes
```sql
CREATE TABLE recipes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);
```

### 14. Recipe Ingredients
```sql
CREATE TABLE recipe_ingredients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recipe_id UUID NOT NULL,
    inventory_item_id UUID NOT NULL,
    quantity_needed DECIMAL(10, 2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
    FOREIGN KEY (inventory_item_id) REFERENCES inventory_items(id)
);
```

### 15. Discounts
```sql
CREATE TABLE discounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(50) UNIQUE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    discount_type VARCHAR(20) NOT NULL, -- percentage, fixed_amount, bogo
    discount_value DECIMAL(10, 2) NOT NULL,
    max_discount_amount DECIMAL(15, 2),
    min_order_amount DECIMAL(15, 2) DEFAULT 0,
    max_usage INT,
    usage_count INT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    starts_at TIMESTAMP,
    expires_at TIMESTAMP,
    requires_approval BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP NULL
);
```

### 16. Printers
```sql
CREATE TABLE printers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    printer_type VARCHAR(50) NOT NULL, -- usb, network, bluetooth
    model VARCHAR(100),
    connection_string VARCHAR(500), -- COM port or IP address
    is_active BOOLEAN DEFAULT TRUE,
    printer_location VARCHAR(100), -- bill, kitchen, etc.
    status VARCHAR(20) DEFAULT 'offline', -- online, offline, error
    last_test_time TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 17. Shifts
```sql
CREATE TABLE shifts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cashier_id UUID NOT NULL,
    shift_date DATE NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    opening_cash DECIMAL(15, 2),
    expected_cash DECIMAL(15, 2),
    actual_cash DECIMAL(15, 2),
    cash_difference DECIMAL(15, 2),
    total_sales DECIMAL(15, 2) DEFAULT 0,
    notes TEXT,
    status VARCHAR(20) DEFAULT 'open', -- open, closed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cashier_id) REFERENCES users(id)
);
CREATE INDEX idx_shifts_cashier_id ON shifts(cashier_id);
CREATE INDEX idx_shifts_shift_date ON shifts(shift_date);
```

### 18. Notifications
```sql
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    notification_type VARCHAR(50) NOT NULL, 
    -- order_ready, low_stock, printer_offline, payment_failed
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    related_order_id UUID,
    related_product_id UUID,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    read_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (related_order_id) REFERENCES orders(id) ON DELETE SET NULL,
    FOREIGN KEY (related_product_id) REFERENCES products(id) ON DELETE SET NULL
);
CREATE INDEX idx_notifications_user_id ON notifications(user_id);
CREATE INDEX idx_notifications_is_read ON notifications(is_read);
```

### 19. Audit Logs
```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    entity_type VARCHAR(50) NOT NULL, 
    -- users, products, orders, payments, etc.
    entity_id UUID NOT NULL,
    action VARCHAR(20) NOT NULL, -- create, update, delete
    changes JSONB, -- field_name: {old_value, new_value}
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);
```

### 20. Settings
```sql
CREATE TABLE settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    setting_key VARCHAR(100) UNIQUE NOT NULL,
    setting_value TEXT,
    setting_type VARCHAR(20), -- string, number, boolean, json
    description TEXT,
    is_system BOOLEAN DEFAULT FALSE,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by UUID,
    FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE SET NULL
);
```

## Indexing Strategy

| Table | Index | Reason |
|-------|-------|--------|
| users | email, username | Fast user lookups during login |
| products | category_id, is_available | Filtering by category and availability |
| orders | status, table_id, created_at | Quick order status queries and time-based reports |
| order_items | order_id | Fast order detail retrieval |
| payments | order_id, created_at | Payment reconciliation |
| inventory_transactions | inventory_item_id, created_at | Stock tracking and audit |
| audit_logs | user_id, entity_type, created_at | Audit trail queries |
| notifications | user_id, is_read | Notification center queries |

## Constraints & Validations

- **Referential Integrity**: Foreign keys enforce data consistency
- **Unique Constraints**: SKUs, usernames, emails are unique
- **Not Null Constraints**: Critical fields cannot be null
- **Check Constraints**: Quantities > 0, amounts >= 0
- **Decimal Precision**: Financial amounts use DECIMAL(15,2)

## Data Retention & Soft Deletes

- **Soft Delete Pattern**: deleted_at column for audit trail
- **Historical Data**: Audit logs retained indefinitely
- **Order History**: Maintained for reporting and reconciliation
- **Old Records**: Archive strategy for aged data (e.g., > 2 years)

## Performance Optimizations

1. **Connection Pooling**: Configured at application level
2. **Query Optimization**: Indexes on frequently queried columns
3. **Materialized Views**: For complex reports (future)
4. **Partitioning**: Orders/transactions by date (future scaling)
5. **Read Replicas**: For reporting queries (future)
