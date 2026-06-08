import csv
import io
from datetime import datetime, time
from flask import render_template, redirect, url_for, flash, request, Response
from flask_login import login_required, current_user
from app.transactions import transactions_bp
from app.extensions import db
from app.models.product import Product
from app.models.location import Location
from app.models.transaction import Transaction
from app.services.inventory_service import InventoryService, InventoryException
from app.forms import StockInForm, StockOutForm

@transactions_bp.route('/stock-in', methods=['GET', 'POST'])
@login_required
def stock_in():
    form = StockInForm()
    
    # Populate dynamic choices
    products = Product.query.filter_by(is_active=True).order_by(Product.product_code.asc()).all()
    form.product_id.choices = [(p.id, f"{p.product_code} - {p.name}") for p in products]

    if form.validate_on_submit():
        try:
            godown = Location.query.filter_by(name="Main Godown").first()
            if not godown:
                raise InventoryException("Main Godown location not found in the database. Please run seed script.")
                
            InventoryService.stock_in(
                product_id=form.product_id.data,
                location_id=godown.id,
                quantity=form.quantity.data,
                user_id=current_user.id,
                supplier_name=form.supplier_name.data,
                invoice_number=form.invoice_number.data,
                notes=form.notes.data
            )
            flash('Stock In processed successfully.', 'success')
            return redirect(url_for('inventory.list_inventory'))
        except InventoryException as e:
            flash(str(e), 'danger')

    return render_template('transactions/stock_in.html', form=form)

@transactions_bp.route('/stock-out', methods=['GET', 'POST'])
@login_required
def stock_out():
    form = StockOutForm()
    
    # Populate dynamic choices
    products = Product.query.filter_by(is_active=True).order_by(Product.product_code.asc()).all()
    form.product_id.choices = [(p.id, f"{p.product_code} - {p.name}") for p in products]

    if form.validate_on_submit():
        try:
            godown = Location.query.filter_by(name="Main Godown").first()
            if not godown:
                raise InventoryException("Main Godown location not found in the database. Please run seed script.")
                
            InventoryService.stock_out(
                product_id=form.product_id.data,
                location_id=godown.id,
                quantity=form.quantity.data,
                user_id=current_user.id,
                reason=form.reason.data,
                notes=form.notes.data
            )
            flash('Stock Out processed successfully.', 'success')
            return redirect(url_for('inventory.list_inventory'))
        except InventoryException as e:
            flash(str(e), 'danger')

    return render_template('transactions/stock_out.html', form=form)

@transactions_bp.route('/transactions')
@login_required
def history():
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('search', '', type=str)
    txn_type = request.args.get('type', '', type=str)
    
    query = Transaction.query.join(Product)

    # Filtering by Search (Product Name/Code or Notes)
    if search_query:
        query = query.filter(
            (Product.name.ilike(f'%{search_query}%')) |
            (Product.product_code.ilike(f'%{search_query}%')) |
            (Transaction.notes.ilike(f'%{search_query}%'))
        )

    # Filtering by Transaction Type
    if txn_type:
        query = query.filter(Transaction.transaction_type == txn_type)

    pagination = query.order_by(Transaction.created_at.desc()).paginate(
        page=page, per_page=15, error_out=False
    )
    transactions = pagination.items

    # Fetch options for filters
    types = ['STOCK_IN', 'STOCK_OUT']

    return render_template(
        'transactions/history.html',
        transactions=transactions,
        pagination=pagination,
        search_query=search_query,
        txn_type=txn_type,
        types=types
    )

@transactions_bp.route('/transactions/export-csv')
@login_required
def export_csv():
    search_query = request.args.get('search', '', type=str)
    txn_type = request.args.get('type', '', type=str)
    location_id = request.args.get('location_id', 0, type=int)
    
    query = Transaction.query.join(Product)

    if search_query:
        query = query.filter(
            (Product.name.ilike(f'%{search_query}%')) |
            (Product.product_code.ilike(f'%{search_query}%')) |
            (Transaction.notes.ilike(f'%{search_query}%'))
        )

    if txn_type:
        query = query.filter(Transaction.transaction_type == txn_type)

    if location_id > 0:
        query = query.filter(
            (Transaction.source_location_id == location_id) |
            (Transaction.destination_location_id == location_id)
        )

    transactions = query.order_by(Transaction.created_at.desc()).all()

    # Build CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        'ID', 'Date & Time', 'Product Code', 'Product Name', 'Quantity', 
        'Type', 'Source Location', 'Destination Location', 'User', 'Notes'
    ])
    
    # Write rows
    for txn in transactions:
        src = txn.source_location.name if txn.source_location else 'N/A'
        dest = txn.destination_location.name if txn.destination_location else 'N/A'
        writer.writerow([
            txn.id,
            txn.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            txn.product.product_code,
            txn.product.name,
            txn.quantity,
            txn.transaction_type,
            src,
            dest,
            txn.user.username,
            txn.notes
        ])
        
    output.seek(0)
    
    filename = f"transactions_export_{datetime.utcnow().strftime('%Y%md_%H%M%S')}.csv"
    
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename={filename}"}
    )
