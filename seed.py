from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.location import Location
from app.models.product import Product
from app.models.inventory import Inventory
from app.models.transaction import Transaction
from app.models.category import Category

def seed_database():
    app = create_app()
    with app.app_context():
        # Create all tables in database
        print("Creating database tables...")
        db.create_all()

        # 1. Seed Locations
        print("Seeding locations...")
        godown = Location.query.filter_by(name="Main Godown").first()
        if not godown:
            godown = Location(name="Main Godown")
            db.session.add(godown)
            
        db.session.commit()

        # Reload locations from db to get IDs
        godown = Location.query.filter_by(name="Main Godown").first()

        # 1.5 Seed Categories
        print("Seeding categories...")
        default_categories = ['Cycle', 'Tyre', 'Tube', 'Rim', 'Spare Part', 'Accessory']
        for cat_name in default_categories:
            cat = Category.query.filter_by(name=cat_name).first()
            if not cat:
                cat = Category(name=cat_name)
                db.session.add(cat)
        db.session.commit()

        # 2. Seed Admin and Staff Users
        print("Seeding users...")
        admin = User.query.filter_by(username="admin").first()
        if not admin:
            admin = User(username="admin", role="ADMIN")
            admin.set_password("admin123")
            db.session.add(admin)

        staff = User.query.filter_by(username="staff").first()
        if not staff:
            staff = User(username="staff", role="STAFF")
            staff.set_password("staff123")
            db.session.add(staff)

        db.session.commit()

        # Reload users to get IDs
        admin = User.query.filter_by(username="admin").first()

        # 3. Seed Sample Products
        print("Seeding products and initial stock logs...")
        products_data = [
            {
                "product_code": "HERO-CYC-26",
                "name": "Hero Ranger Cycle 26\"",
                "brand": "Hero",
                "category": "Cycle",
                "size": "26 inches",
                "purchase_price": 120.00,
                "selling_price": 200.00,
                "minimum_stock": 5,
                "description": "Standard adult mountain terrain bike with dual suspension and steel frame.",
                "qty": 18
            },
            {
                "product_code": "MRF-TYR-26",
                "name": "MRF Nylon Grip Tyre 26\"",
                "brand": "MRF",
                "category": "Tyre",
                "size": "26 x 1.95",
                "purchase_price": 14.50,
                "selling_price": 25.00,
                "minimum_stock": 20,
                "description": "High-durability nylon threads with knobby tread design for wet grip.",
                "qty": 140
            },
            {
                "product_code": "DUN-TUB-26",
                "name": "Dunlop Inner Tube 26\"",
                "brand": "Dunlop",
                "category": "Tube",
                "size": "26 x 1.90-2.125",
                "purchase_price": 3.80,
                "selling_price": 7.50,
                "minimum_stock": 30,
                "description": "Butyl rubber leak-resistant tube with standard Schrader valve.",
                "qty": 225
            },
            {
                "product_code": "SHI-RIM-26",
                "name": "Shimano Alloy Rim 26\"",
                "brand": "Shimano",
                "category": "Rim",
                "size": "26\" - 36 Hole",
                "purchase_price": 22.00,
                "selling_price": 38.00,
                "minimum_stock": 10,
                "description": "Double-walled aluminum alloy rim with CNC sidewalls for brake grip.",
                "qty": 48
            },
            {
                "product_code": "SHI-BRK-SHO",
                "name": "Shimano V-Brake Shoes Set",
                "brand": "Shimano",
                "category": "Spare Part",
                "size": "70mm Standard",
                "purchase_price": 2.50,
                "selling_price": 5.00,
                "minimum_stock": 15,
                "description": "All-weather rubber V-brake shoe pads for aluminum rims.",
                "qty": 105
            },
            {
                "product_code": "CAT-CYC-COM",
                "name": "Cateye Wireless Speedometer",
                "brand": "Cateye",
                "category": "Accessory",
                "size": "Standard Pack",
                "purchase_price": 18.00,
                "selling_price": 32.00,
                "minimum_stock": 8,
                "description": "Wireless cycle computer tracking speed, distance, and calories.",
                "qty": 6  # Low stock test case: total stock 6 <= minimum 8
            }
        ]

        for p_data in products_data:
            prod = Product.query.filter_by(product_code=p_data["product_code"]).first()
            if not prod:
                prod = Product(
                    product_code=p_data["product_code"],
                    name=p_data["name"],
                    brand=p_data["brand"],
                    category=p_data["category"],
                    size=p_data["size"],
                    purchase_price=p_data["purchase_price"],
                    selling_price=p_data["selling_price"],
                    minimum_stock=p_data["minimum_stock"],
                    description=p_data["description"]
                )
                db.session.add(prod)
                db.session.commit()

                # Register inventories and create transaction logs to maintain audits consistency
                if p_data["qty"] > 0:
                    inv_g = Inventory(product_id=prod.id, location_id=godown.id, quantity=p_data["qty"])
                    db.session.add(inv_g)
                    txn_g = Transaction(
                        product_id=prod.id,
                        user_id=admin.id,
                        source_location_id=None,
                        destination_location_id=godown.id,
                        quantity=p_data["qty"],
                        transaction_type='STOCK_IN',
                        notes="Seed: Initial inventory import."
                    )
                    db.session.add(txn_g)
                
                db.session.commit()

        print("Database seeded successfully!")

if __name__ == '__main__':
    seed_database()
