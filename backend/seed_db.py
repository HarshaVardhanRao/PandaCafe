"""
Seed script to create initial roles and test data.
"""

from sqlalchemy.orm import Session
from app.db.database import SessionLocal, Base, engine
from app.models import Role, User, Category, Product
from app.core.security import get_password_hash


def seed_roles(db: Session):
    """Create default roles."""
    roles_data = [
        {
            "name": "owner",
            "description": "Full system access",
            "permissions": ["*"],
        },
        {
            "name": "manager",
            "description": "Operational management",
            "permissions": ["orders:*", "inventory:*", "reports:*", "staff:read"],
        },
        {
            "name": "cashier",
            "description": "Billing and order handling",
            "permissions": ["orders:create", "orders:read", "orders:update", "billing:*", "payments:*"],
        },
        {
            "name": "kitchen",
            "description": "Kitchen display system only",
            "permissions": ["orders:read", "orders:update_status"],
        },
        {
            "name": "waiter",
            "description": "Order creation and management",
            "permissions": ["orders:create", "orders:read", "customers:read"],
        },
    ]

    for role_data in roles_data:
        existing = db.query(Role).filter(Role.name == role_data["name"]).first()
        if not existing:
            role = Role(**role_data)
            db.add(role)
            print(f"Created role: {role_data['name']}")

    db.commit()


def seed_admin_user(db: Session):
    """Create admin user."""
    # Get owner role
    owner_role = db.query(Role).filter(Role.name == "owner").first()

    if owner_role:
        existing_admin = db.query(User).filter(User.username == "admin").first()
        if not existing_admin:
            admin = User(
                username="admin",
                email="admin@pandacafe.com",
                password_hash=get_password_hash("Admin@123"),
                full_name="System Administrator",
                phone_number="+91-9999999999",
                role_id=owner_role.id,
                status="active",
            )
            db.add(admin)
            db.commit()
            print("Created admin user: admin / Admin@123")


def seed_categories(db: Session):
    """Create sample categories."""
    categories_data = [
        {"name": "Coffee", "description": "Coffee beverages"},
        {"name": "Tea", "description": "Tea varieties"},
        {"name": "Snacks", "description": "Light snacks and pastries"},
        {"name": "Desserts", "description": "Desserts and sweets"},
        {"name": "Beverages", "description": "Non-alcoholic beverages"},
    ]

    for cat_data in categories_data:
        existing = db.query(Category).filter(Category.name == cat_data["name"], Category.deleted_at.is_(None)).first()
        if not existing:
            category = Category(**cat_data, is_active=True, display_order=0)
            db.add(category)
            print(f"Created category: {cat_data['name']}")

    db.commit()


def seed_products(db: Session):
    """Create sample products."""
    coffee_category = db.query(Category).filter(Category.name == "Coffee").first()

    if coffee_category:
        products_data = [
            {
                "sku": "COFFEE-001",
                "name": "Espresso",
                "category_id": coffee_category.id,
                "price": 60.00,
                "tax_percent": 5.0,
                "preparation_time_minutes": 2,
            },
            {
                "sku": "COFFEE-002",
                "name": "Americano",
                "category_id": coffee_category.id,
                "price": 70.00,
                "tax_percent": 5.0,
                "preparation_time_minutes": 3,
            },
            {
                "sku": "COFFEE-003",
                "name": "Cappuccino",
                "category_id": coffee_category.id,
                "price": 90.00,
                "tax_percent": 5.0,
                "preparation_time_minutes": 5,
            },
            {
                "sku": "COFFEE-004",
                "name": "Latte",
                "category_id": coffee_category.id,
                "price": 100.00,
                "tax_percent": 5.0,
                "preparation_time_minutes": 5,
            },
        ]

        for prod_data in products_data:
            existing = db.query(Product).filter(Product.sku == prod_data["sku"], Product.deleted_at.is_(None)).first()
            if not existing:
                product = Product(**prod_data, is_available=True, is_active=True)
                db.add(product)
                print(f"Created product: {prod_data['name']}")

        db.commit()


def main():
    """Run all seed functions."""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        print("\nSeeding roles...")
        seed_roles(db)

        print("\nSeeding admin user...")
        seed_admin_user(db)

        print("\nSeeding categories...")
        seed_categories(db)

        print("\nSeeding products...")
        seed_products(db)

        print("\n✅ Database seeding completed successfully!")
    except Exception as e:
        print(f"❌ Error during seeding: {str(e)}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
