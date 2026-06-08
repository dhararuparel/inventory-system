from datetime import datetime, time, timedelta
from flask import render_template
from flask_login import login_required
from sqlalchemy import func
from app.dashboard import dashboard_bp
from app.models.product import Product
from app.models.inventory import Inventory
from app.models.transaction import Transaction
from app.extensions import db

@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@login_required
def index():
    # 1. Total active products
    total_products = Product.query.filter_by(is_active=True).count()

    # 2. Total inventory quantity
    total_inventory_qty = db.session.query(func.sum(Inventory.quantity))\
        .join(Product)\
        .filter(Product.is_active == True)\
        .scalar() or 0

    # 3. Total inventory asset value (based on purchase price)
    total_inventory_value = db.session.query(
        func.sum(Inventory.quantity * Product.purchase_price)
    ).join(Product).filter(Product.is_active == True).scalar() or 0

    # 4. Low stock products count & list (Total quantity <= minimum_stock)
    # Group inventories by product, filtering those below minimum stock
    low_stock_query = db.session.query(
        Product,
        func.coalesce(func.sum(Inventory.quantity), 0).label('total_stock')
    ).outerjoin(Inventory)\
     .filter(Product.is_active == True)\
     .group_by(Product.id)\
     .having(func.coalesce(func.sum(Inventory.quantity), 0) <= Product.minimum_stock)

    low_stock_count = low_stock_query.count()
    low_stock_list = [
        {
            'product': prod,
            'total_stock': stock,
            'minimum_stock': prod.minimum_stock
        }
        for prod, stock in low_stock_query.limit(5).all()
    ]

    # 5. Today's movements
    today_start = datetime.combine(datetime.utcnow().date(), time.min)
    
    today_stock_in = db.session.query(func.sum(Transaction.quantity))\
        .filter(Transaction.transaction_type == 'STOCK_IN', Transaction.created_at >= today_start)\
        .scalar() or 0
        
    today_stock_out = db.session.query(func.sum(Transaction.quantity))\
        .filter(Transaction.transaction_type == 'STOCK_OUT', Transaction.created_at >= today_start)\
        .scalar() or 0

    # 6. Recent Transactions (last 5)
    recent_transactions = Transaction.query.order_by(Transaction.created_at.desc()).limit(5).all()

    # --- CHART DATA PREPARATION ---

    # A. Inventory Value by Category
    category_val_query = db.session.query(
        Product.category,
        func.sum(Inventory.quantity * Product.purchase_price)
    ).join(Inventory).filter(Product.is_active == True).group_by(Product.category).all()
    
    category_labels = [row[0] for row in category_val_query]
    category_values = [float(row[1] or 0) for row in category_val_query]

    # B. Stock In vs Stock Out (Last 7 Days)
    days_labels = []
    stock_in_trend = []
    stock_out_trend = []
    
    for i in range(6, -1, -1):
        day_date = datetime.utcnow().date() - timedelta(days=i)
        day_start = datetime.combine(day_date, time.min)
        day_end = datetime.combine(day_date, time.max)
        
        days_labels.append(day_date.strftime('%b %d'))
        
        in_qty = db.session.query(func.sum(Transaction.quantity))\
            .filter(Transaction.transaction_type == 'STOCK_IN', 
                    Transaction.created_at >= day_start, 
                    Transaction.created_at <= day_end)\
            .scalar() or 0
        stock_in_trend.append(int(in_qty))

        out_qty = db.session.query(func.sum(Transaction.quantity))\
            .filter(Transaction.transaction_type == 'STOCK_OUT', 
                    Transaction.created_at >= day_start, 
                    Transaction.created_at <= day_end)\
            .scalar() or 0
        stock_out_trend.append(int(out_qty))

    # C. Monthly Transactions Count (Last 6 Months)
    monthly_labels = []
    monthly_counts = []
    
    # We will generate months dynamically
    for i in range(5, -1, -1):
        # Approximate month subtraction (using 30 days increments)
        target_date = datetime.utcnow().date() - timedelta(days=i*30)
        month_start = datetime(target_date.year, target_date.month, 1)
        if target_date.month == 12:
            month_end = datetime(target_date.year + 1, 1, 1) - timedelta(seconds=1)
        else:
            month_end = datetime(target_date.year, target_date.month + 1, 1) - timedelta(seconds=1)
            
        monthly_labels.append(month_start.strftime('%B %Y'))
        
        txn_count = Transaction.query.filter(
            Transaction.created_at >= month_start,
            Transaction.created_at <= month_end
        ).count()
        monthly_counts.append(txn_count)

    return render_template(
        'dashboard/index.html',
        total_products=total_products,
        total_inventory_qty=total_inventory_qty,
        total_inventory_value=total_inventory_value,
        low_stock_count=low_stock_count,
        low_stock_list=low_stock_list,
        today_stock_in=today_stock_in,
        today_stock_out=today_stock_out,
        recent_transactions=recent_transactions,
        category_labels=category_labels,
        category_values=category_values,
        days_labels=days_labels,
        stock_in_trend=stock_in_trend,
        stock_out_trend=stock_out_trend,
        monthly_labels=monthly_labels,
        monthly_counts=monthly_counts
    )

@dashboard_bp.route('/downloads')
def downloads():
    return render_template('dashboard/downloads.html')

