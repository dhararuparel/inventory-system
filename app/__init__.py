import os
from flask import Flask
from flask_admin import Admin
from config import Config
from app.extensions import db, migrate, login_manager, csrf

# Import models to register them with Alembic/SQLAlchemy
from app.models.user import User
from app.models.product import Product
from app.models.location import Location
from app.models.inventory import Inventory
from app.models.transaction import Transaction

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Configure Login Manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Create upload folder directory if not exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Register blueprints
    from app.auth import auth_bp
    from app.dashboard import dashboard_bp
    from app.products import products_bp
    from app.inventory import inventory_bp
    from app.transactions import transactions_bp
    from app.reports import reports_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(transactions_bp, url_prefix='/')  # Registered at root to serve /stock-in, /stock-out, /transfers, /transactions
    app.register_blueprint(reports_bp)

    # Setup Flask-Admin
    from app.admin.views import (
        SecureAdminIndexView, UserAdminView, ProductAdminView,
        LocationAdminView, InventoryAdminView, TransactionAdminView,
        CategoryAdminView
    )
    from app.models.category import Category
    
    admin = Admin(
        app, 
        name='Store Admin Panel', 
        template_mode='bootstrap4',
        index_view=SecureAdminIndexView(template='admin/custom_index.html')
    )
    admin.add_view(UserAdminView(User, db.session, name='Users', category='System', endpoint='admin_user'))
    admin.add_view(LocationAdminView(Location, db.session, name='Locations', category='Inventory', endpoint='admin_location'))
    admin.add_view(CategoryAdminView(Category, db.session, name='Categories', category='Inventory', endpoint='admin_category'))
    admin.add_view(ProductAdminView(Product, db.session, name='Products', category='Inventory', endpoint='admin_product'))
    admin.add_view(InventoryAdminView(Inventory, db.session, name='Stock Levels', category='Inventory', endpoint='admin_inventory'))
    admin.add_view(TransactionAdminView(Transaction, db.session, name='Audit History', category='System', endpoint='admin_transaction'))

    # Context processor to inject global variables in templates (e.g. low stock alerts count)
    @app.context_processor
    def inject_low_stock():
        from flask_login import current_user
        if current_user.is_authenticated:
            try:
                # Count products where total stock <= minimum_stock
                low_stock_count = db.session.query(Product).outerjoin(Inventory)\
                    .filter(Product.is_active == True)\
                    .group_by(Product.id)\
                    .having(db.func.coalesce(db.func.sum(Inventory.quantity), 0) <= Product.minimum_stock)\
                    .count()
                return dict(global_low_stock_count=low_stock_count)
            except Exception:
                return dict(global_low_stock_count=0)
        return dict(global_low_stock_count=0)

    return app
