from flask import render_template, request
from flask_login import login_required
from sqlalchemy import func
from app.inventory import inventory_bp
from app.extensions import db
from app.models.inventory import Inventory
from app.models.product import Product
from app.models.location import Location

@inventory_bp.route('/')
@inventory_bp.route('/inventory')
@login_required
def list_inventory():
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('search', '', type=str)
    location_id = request.args.get('location_id', 0, type=int)
    category_filter = request.args.get('category', '', type=str)
    alert_filter = request.args.get('alert', '', type=str) # 'low' for below minimum stock

    # Base query joining Inventory, Product, Location
    query = db.session.query(Inventory).join(Product).join(Location).filter(Product.is_active == True)

    # Search filter
    if search_query:
        query = query.filter(
            (Product.name.ilike(f'%{search_query}%')) |
            (Product.product_code.ilike(f'%{search_query}%')) |
            (Product.brand.ilike(f'%{search_query}%'))
        )

    # Location filter
    if location_id > 0:
        query = query.filter(Inventory.location_id == location_id)

    # Category filter
    if category_filter:
        query = query.filter(Product.category == category_filter)

    # Low Stock alert filter: displays rows where total stock for the product is low,
    # OR where this specific location's inventory is low. Let's filter items where Inventory.quantity <= Product.minimum_stock.
    if alert_filter == 'low':
        query = query.filter(Inventory.quantity <= Product.minimum_stock)

    # Paginate results
    pagination = query.order_by(Product.product_code.asc(), Location.name.asc()).paginate(
        page=page, per_page=15, error_out=False
    )
    inventory_items = pagination.items

    # Fetch options for filters
    locations = Location.query.order_by(Location.name.asc()).all()
    from app.models.category import Category
    categories = [c.name for c in Category.query.order_by(Category.name.asc()).all()]

    # Warning banner calculations (total number of low stock inventory items)
    low_stock_count = db.session.query(Inventory).join(Product)\
        .filter(Product.is_active == True, Inventory.quantity <= Product.minimum_stock).count()

    return render_template(
        'inventory/list.html',
        inventory_items=inventory_items,
        pagination=pagination,
        search_query=search_query,
        location_id=location_id,
        category_filter=category_filter,
        alert_filter=alert_filter,
        locations=locations,
        categories=categories,
        low_stock_count=low_stock_count
    )
