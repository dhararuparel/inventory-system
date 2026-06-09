import os
import uuid
from datetime import datetime
from flask import render_template, request, jsonify, current_app, Response, send_file, session
from flask_login import login_required, current_user
from sqlalchemy import func
from app.excel import excel_bp
from app.extensions import db
from app.models.product import Product
from app.models.inventory import Inventory
from app.models.location import Location
from app.models.category import Category
from app.services.inventory_service import InventoryService, InventoryException
from app.utils.decorators import admin_required
from app.excel.excel_handler import (
    generate_excel_file,
    parse_and_validate_products,
    parse_and_validate_inventory
)

# -------------------------------------------------------------
# RENDER TEMPLATES
# -------------------------------------------------------------

@excel_bp.route('/export-center', methods=['GET'])
@login_required
def export_center():
    return render_template('excel/export_center.html')

@excel_bp.route('/import-products', methods=['GET'])
@login_required
@admin_required
def import_products_page():
    return render_template('excel/import_products.html')

@excel_bp.route('/update-inventory', methods=['GET'])
@login_required
@admin_required
def update_inventory_page():
    return render_template('excel/update_inventory.html')


# -------------------------------------------------------------
# EXPORT API ENDPOINTS
# -------------------------------------------------------------

@excel_bp.route('/export/products', methods=['GET'])
@login_required
def export_products():
    """
    Export all active products directly to .xlsx sheet.
    """
    products = Product.query.filter_by(is_active=True).order_by(Product.product_code.asc()).all()
    
    headers = [
        'Product Code', 'Product Name', 'Brand', 'Category', 
        'Size', 'Purchase Price', 'Selling Price', 'Minimum Stock'
    ]
    
    rows = []
    for p in products:
        rows.append([
            p.product_code,
            p.name,
            p.brand or '',
            p.category or '',
            p.size or '',
            float(p.purchase_price) if p.purchase_price else 0.0,
            float(p.selling_price) if p.selling_price else 0.0,
            p.minimum_stock
        ])
        
    excel_bin = generate_excel_file(
        headers=headers,
        rows=rows,
        sheet_title='Products Catalog',
        report_name='Active Products Directory'
    )
    
    filename = f"products_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    return Response(
        excel_bin,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-disposition": f"attachment; filename={filename}"}
    )


@excel_bp.route('/export/inventory', methods=['GET'])
@login_required
def export_inventory():
    """
    Export total inventories per location to .xlsx sheet.
    """
    items = db.session.query(Inventory).join(Product).join(Location)\
        .filter(Product.is_active == True)\
        .order_by(Product.product_code.asc(), Location.name.asc()).all()
        
    headers = ['Product Code', 'Product Name', 'Current Quantity', 'Location', 'Last Updated']
    
    rows = []
    for item in items:
        # If product has no explicit updated_at, fallback to now
        last_up = item.product.updated_at.strftime('%Y-%m-%d %H:%M:%S') if item.product.updated_at else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        rows.append([
            item.product.product_code,
            item.product.name,
            item.quantity,
            item.location.name,
            last_up
        ])
        
    excel_bin = generate_excel_file(
        headers=headers,
        rows=rows,
        sheet_title='Inventory Stock Levels',
        report_name='Current Stock Quantities Report'
    )
    
    filename = f"inventory_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    return Response(
        excel_bin,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-disposition": f"attachment; filename={filename}"}
    )


@excel_bp.route('/export/low-stock', methods=['GET'])
@login_required
def export_low_stock():
    """
    Export products that are currently running below their minimum stock levels.
    """
    low_stock_query = db.session.query(
        Product.product_code,
        Product.name.label('product_name'),
        Product.minimum_stock,
        func.coalesce(func.sum(Inventory.quantity), 0).label('current_stock')
    ).outerjoin(Inventory, Inventory.product_id == Product.id)\
     .filter(Product.is_active == True)\
     .group_by(Product.id)\
     .having(func.coalesce(func.sum(Inventory.quantity), 0) <= Product.minimum_stock)
     
    results = low_stock_query.order_by(Product.product_code.asc()).all()
    
    headers = ['Product Code', 'Product Name', 'Current Stock', 'Minimum Stock', 'Shortage Quantity']
    
    rows = []
    for r in results:
        shortage = r.minimum_stock - r.current_stock
        rows.append([
            r.product_code,
            r.product_name,
            r.current_stock,
            r.minimum_stock,
            shortage if shortage > 0 else 0
        ])
        
    excel_bin = generate_excel_file(
        headers=headers,
        rows=rows,
        sheet_title='Low Stock Alerts',
        report_name='Low Stock Inventory Shortage Report'
    )
    
    filename = f"low_stock_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    return Response(
        excel_bin,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-disposition": f"attachment; filename={filename}"}
    )


# -------------------------------------------------------------
# PRODUCT IMPORT API ENDPOINTS
# -------------------------------------------------------------

@excel_bp.route('/import/products/upload', methods=['POST'])
@login_required
@admin_required
def upload_product_file():
    """
    Endpoint 1: Upload Product Import File.
    Saves file to temporary folder and returns a unique file identifier.
    """
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded."}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected."}), 400
        
    if not (file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
        return jsonify({"error": "Unsupported file format. Please upload an Excel file (.xlsx or .xls)."}), 400
        
    temp_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'excel_temp')
    os.makedirs(temp_dir, exist_ok=True)
    
    file_id = f"prod_{uuid.uuid4().hex}.xlsx"
    filepath = os.path.join(temp_dir, file_id)
    file.save(filepath)
    
    return jsonify({"file_id": file_id, "success": True})


@excel_bp.route('/import/products/validate', methods=['POST'])
@login_required
@admin_required
def validate_product_import():
    """
    Endpoint 2: Validate Product Import.
    Takes file_id and parses row validation logs.
    """
    data = request.get_json()
    if not data or 'file_id' not in data:
        return jsonify({"error": "file_id parameter is required."}), 400
        
    file_id = data['file_id']
    temp_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'excel_temp')
    filepath = os.path.join(temp_dir, file_id)
    
    if not os.path.exists(filepath):
        return jsonify({"error": "Temporary file not found or expired. Please upload the file again."}), 404
        
    success, rows, summary = parse_and_validate_products(filepath)
    if not success:
        return jsonify(summary), 400
        
    return jsonify({"rows": rows, "summary": summary, "success": True})


@excel_bp.route('/import/products/confirm', methods=['POST'])
@login_required
@admin_required
def confirm_product_import():
    """
    Endpoint 3: Confirm Product Import.
    Executes database insertions of valid data rows.
    """
    data = request.get_json()
    if not data or 'file_id' not in data:
        return jsonify({"error": "file_id parameter is required."}), 400
        
    file_id = data['file_id']
    temp_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'excel_temp')
    filepath = os.path.join(temp_dir, file_id)
    
    if not os.path.exists(filepath):
        return jsonify({"error": "Temporary file not found or expired. Please upload again."}), 404
        
    success, rows, summary = parse_and_validate_products(filepath)
    if not success:
        return jsonify(summary), 400
        
    if summary['has_errors']:
        return jsonify({"error": "Cannot import Excel sheet with validation errors. Please correct the sheet first."}), 400
        
    try:
        # Dynamic category registration list
        categories_to_ensure = {r['category'].strip() for r in rows if r['category']}
        for cat_name in categories_to_ensure:
            existing_cat = Category.query.filter(func.lower(Category.name) == cat_name.lower()).first()
            if not existing_cat:
                new_cat = Category(name=cat_name)
                db.session.add(new_cat)
        
        # Add products
        for r in rows:
            product = Product(
                product_code=r['product_code'],
                name=r['name'],
                brand=r['brand'] or None,
                category=r['category'],
                size=r['size'] or None,
                purchase_price=r['purchase_price'],
                selling_price=r['selling_price'],
                minimum_stock=r['minimum_stock'],
                is_active=True
            )
            db.session.add(product)
            
        db.session.commit()
        
        # Cleanup file
        if os.path.exists(filepath):
            os.remove(filepath)
            
        return jsonify({"success": True, "message": f"Successfully imported {summary['valid_rows']} products."})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Database commit failed: {str(e)}"}), 500


# -------------------------------------------------------------
# INVENTORY UPDATE API ENDPOINTS
# -------------------------------------------------------------

@excel_bp.route('/import/inventory/upload', methods=['POST'])
@login_required
@admin_required
def upload_inventory_file():
    """
    Endpoint 1: Upload Inventory Update File.
    Saves file to temporary folder and returns a unique file identifier.
    """
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded."}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected."}), 400
        
    if not (file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
        return jsonify({"error": "Unsupported file format. Please upload an Excel file (.xlsx or .xls)."}), 400
        
    temp_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'excel_temp')
    os.makedirs(temp_dir, exist_ok=True)
    
    file_id = f"inv_{uuid.uuid4().hex}.xlsx"
    filepath = os.path.join(temp_dir, file_id)
    file.save(filepath)
    
    return jsonify({"file_id": file_id, "success": True})


@excel_bp.route('/import/inventory/validate', methods=['POST'])
@login_required
@admin_required
def validate_inventory_update():
    """
    Endpoint 2: Validate Inventory Update.
    Takes file_id and parses row validation logs.
    """
    data = request.get_json()
    if not data or 'file_id' not in data:
        return jsonify({"error": "file_id parameter is required."}), 400
        
    file_id = data['file_id']
    temp_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'excel_temp')
    filepath = os.path.join(temp_dir, file_id)
    
    if not os.path.exists(filepath):
        return jsonify({"error": "Temporary file not found or expired. Please upload the file again."}), 404
        
    success, rows, summary = parse_and_validate_inventory(filepath)
    if not success:
        return jsonify(summary), 400
        
    return jsonify({"rows": rows, "summary": summary, "success": True})


@excel_bp.route('/import/inventory/confirm', methods=['POST'])
@login_required
@admin_required
def confirm_inventory_update():
    """
    Endpoint 3: Confirm Inventory Update.
    Applies the quantity changes to inventory and creates history logs.
    """
    data = request.get_json()
    if not data or 'file_id' not in data:
        return jsonify({"error": "file_id parameter is required."}), 400
        
    file_id = data['file_id']
    temp_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'excel_temp')
    filepath = os.path.join(temp_dir, file_id)
    
    if not os.path.exists(filepath):
        return jsonify({"error": "Temporary file not found or expired. Please upload again."}), 404
        
    success, rows, summary = parse_and_validate_inventory(filepath)
    if not success:
        return jsonify(summary), 400
        
    if summary['has_errors']:
        return jsonify({"error": "Cannot apply stock updates with validation errors. Please correct the Excel sheet first."}), 400
        
    try:
        godown = Location.query.filter_by(name="Main Godown").first()
        if not godown:
            return jsonify({"error": "Main Godown location not found in the database. Please run seed script first."}), 500
            
        applied_count = 0
        for r in rows:
            diff = r['difference']
            product = Product.query.filter_by(product_code=r['product_code'], is_active=True).first()
            
            if not product or diff == 0:
                continue
                
            # Perform atomic update via InventoryService
            notes = f"Bulk Excel Import Update (Prev: {r['current_quantity']}, New: {r['new_quantity']})"
            if diff > 0:
                InventoryService.stock_in(
                    product_id=product.id,
                    location_id=godown.id,
                    quantity=diff,
                    user_id=current_user.id,
                    notes=notes
                )
            elif diff < 0:
                InventoryService.stock_out(
                    product_id=product.id,
                    location_id=godown.id,
                    quantity=abs(diff),
                    user_id=current_user.id,
                    reason="Adjustment via Excel Import",
                    notes=notes
                )
            applied_count += 1
            
        db.session.commit()
        
        # Cleanup file
        if os.path.exists(filepath):
            os.remove(filepath)
            
        return jsonify({"success": True, "message": f"Successfully updated inventory for {applied_count} products."})
        
    except InventoryException as ie:
        db.session.rollback()
        return jsonify({"error": f"Inventory Service violation: {str(ie)}"}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Database commit failed: {str(e)}"}), 500
