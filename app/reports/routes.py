import io
from datetime import datetime, date, time, timedelta
from flask import render_template, request, Response, flash, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy import func
from sqlalchemy.orm import aliased
import pandas as pd

from app.reports import reports_bp
from app.extensions import db
from app.models.product import Product
from app.models.location import Location
from app.models.inventory import Inventory
from app.models.transaction import Transaction
from app.models.user import User

# ReportLab Imports for PDF Generation
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def parse_date(date_str, is_end=False):
    if not date_str:
        return None
    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        if is_end:
            return datetime.combine(dt.date(), time.max)
        return datetime.combine(dt.date(), time.min)
    except ValueError:
        return None

def get_report_data(report_type, start_date=None, end_date=None, product_id=None, category=None, transaction_type=None):
    """
    Core function to fetch and format report data based on parameters.
    """
    if report_type == 'inventory':
        query = db.session.query(
            Product.product_code,
            Product.name.label('product_name'),
            Product.category,
            Inventory.quantity,
            Product.purchase_price,
            (Inventory.quantity * Product.purchase_price).label('value')
        ).join(Inventory, Inventory.product_id == Product.id)\
         .filter(Product.is_active == True)

        if product_id:
            query = query.filter(Product.id == product_id)
        if category:
            query = query.filter(Product.category == category)

        results = query.order_by(Product.product_code.asc()).all()
        
        headers = ['Product Code', 'Product Name', 'Category', 'Quantity', 'Purchase Price', 'Inventory Value']
        rows = [[r.product_code, r.product_name, r.category, r.quantity, float(r.purchase_price), float(r.value)] for r in results]
        return headers, rows

    elif report_type == 'low_stock':
        query = db.session.query(
            Product.product_code,
            Product.name.label('product_name'),
            Product.category,
            Product.minimum_stock,
            func.coalesce(func.sum(Inventory.quantity), 0).label('current_stock')
        ).outerjoin(Inventory, Inventory.product_id == Product.id)\
         .filter(Product.is_active == True)\
         .group_by(Product.id)\
         .having(func.coalesce(func.sum(Inventory.quantity), 0) <= Product.minimum_stock)

        if product_id:
            query = query.filter(Product.id == product_id)
        if category:
            query = query.filter(Product.category == category)

        results = query.order_by(Product.product_code.asc()).all()
        
        headers = ['Product Code', 'Product Name', 'Category', 'Minimum Stock Alert Level', 'Current Stock']
        rows = [[r.product_code, r.product_name, r.category, r.minimum_stock, r.current_stock] for r in results]
        return headers, rows

    elif report_type == 'movement':
        query = db.session.query(
            Transaction.created_at,
            Product.product_code,
            Product.name.label('product_name'),
            Transaction.transaction_type,
            Transaction.quantity,
            User.username
        ).join(Product, Transaction.product_id == Product.id)\
         .join(User, Transaction.user_id == User.id)

        if start_date:
            query = query.filter(Transaction.created_at >= start_date)
        if end_date:
            query = query.filter(Transaction.created_at <= end_date)
        if product_id:
            query = query.filter(Transaction.product_id == product_id)
        if category:
            query = query.filter(Product.category == category)
        if transaction_type:
            query = query.filter(Transaction.transaction_type == transaction_type)

        results = query.order_by(Transaction.created_at.desc()).all()
        
        headers = ['Date & Time', 'Product Code', 'Product Name', 'Type', 'Quantity', 'User']
        rows = [[
            r.created_at.strftime('%Y-%m-%d %H:%M:%S'), 
            r.product_code, 
            r.product_name, 
            r.transaction_type, 
            r.quantity, 
            r.username
        ] for r in results]
        return headers, rows

    return [], []

@reports_bp.route('/reports')
@login_required
def index():
    report_type = request.args.get('report_type', '', type=str)
    start_date_str = request.args.get('start_date', '', type=str)
    end_date_str = request.args.get('end_date', '', type=str)
    product_id = request.args.get('product_id', 0, type=int)
    category = request.args.get('category', '', type=str)
    transaction_type = request.args.get('transaction_type', '', type=str)

    start_date = parse_date(start_date_str)
    end_date = parse_date(end_date_str, is_end=True)

    headers, rows = [], []
    if report_type:
        headers, rows = get_report_data(
            report_type=report_type,
            start_date=start_date,
            end_date=end_date,
            product_id=product_id if product_id > 0 else None,
            category=category if category else None,
            transaction_type=transaction_type if transaction_type else None
        )

    # Dynamic filter selections
    products = Product.query.filter_by(is_active=True).order_by(Product.product_code.asc()).all()
    from app.models.category import Category
    categories = [c.name for c in Category.query.order_by(Category.name.asc()).all()]

    return render_template(
        'reports/index.html',
        report_type=report_type,
        start_date_str=start_date_str,
        end_date_str=end_date_str,
        product_id=product_id,
        category_filter=category,
        transaction_type=transaction_type,
        products=products,
        categories=categories,
        headers=headers,
        rows=rows[:50],  # Show preview of first 50 rows
        total_rows=len(rows)
    )

@reports_bp.route('/reports/export')
@login_required
def export():
    report_type = request.args.get('report_type', '', type=str)
    export_format = request.args.get('format', 'csv', type=str)
    start_date_str = request.args.get('start_date', '', type=str)
    end_date_str = request.args.get('end_date', '', type=str)
    product_id = request.args.get('product_id', 0, type=int)
    category = request.args.get('category', '', type=str)
    transaction_type = request.args.get('transaction_type', '', type=str)

    start_date = parse_date(start_date_str)
    end_date = parse_date(end_date_str, is_end=True)

    if not report_type:
        flash('Report type is required for exporting.', 'danger')
        return redirect(url_for('reports.index'))

    headers, rows = get_report_data(
        report_type=report_type,
        start_date=start_date,
        end_date=end_date,
        product_id=product_id if product_id > 0 else None,
        category=category if category else None,
        transaction_type=transaction_type if transaction_type else None
    )

    timestamp = datetime.utcnow().strftime('%Y%md_%H%M%S')
    filename_base = f"{report_type}_report_{timestamp}"

    # 1. EXPORT TO CSV
    if export_format == 'csv':
        output = io.StringIO()
        import csv
        writer = csv.writer(output)
        writer.writerow(headers)
        writer.writerows(rows)
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-disposition": f"attachment; filename={filename_base}.csv"}
        )

    # 2. EXPORT TO EXCEL
    elif export_format == 'excel':
        df = pd.DataFrame(rows, columns=headers)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Report')
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-disposition": f"attachment; filename={filename_base}.xlsx"}
        )

    # 3. EXPORT TO PDF
    elif export_format == 'pdf':
        output = io.BytesIO()
        doc = SimpleDocTemplate(output, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
        story = []
        
        styles = getSampleStyleSheet()
        # Create a clean layout style
        title_style = ParagraphStyle(
            'ReportTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=18,
            leading=22,
            textColor=colors.HexColor('#1e293b'),
            spaceAfter=15
        )
        meta_style = ParagraphStyle(
            'ReportMeta',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            textColor=colors.HexColor('#64748b'),
            spaceAfter=20
        )
        cell_style = ParagraphStyle(
            'ReportCell',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8,
            leading=10
        )
        header_cell_style = ParagraphStyle(
            'ReportHeaderCell',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8,
            leading=10,
            textColor=colors.white
        )

        title_map = {
            'inventory': 'Current Inventory Report',
            'low_stock': 'Low Stock Alert Report',
            'movement': 'Inventory Movement Report'
        }
        
        # Add Title
        story.append(Paragraph(title_map.get(report_type, 'Inventory Report'), title_style))
        
        # Add Metadata
        meta_info = f"Generated on: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')} | Total Records: {len(rows)}"
        story.append(Paragraph(meta_info, meta_style))
        story.append(Spacer(1, 10))

        # Format Table Content
        pdf_data = []
        # Header Row
        pdf_data.append([Paragraph(h, header_cell_style) for h in headers])
        
        # Data Rows
        for r in rows:
            formatted_row = []
            for item in r:
                # Format float/decimals as currency where appropriate
                if isinstance(item, float):
                    val_str = f"Rs. {item:,.2f}"
                else:
                    val_str = str(item)
                formatted_row.append(Paragraph(val_str, cell_style))
            pdf_data.append(formatted_row)

        # Set page-width proportions dynamically
        col_widths = None
        if report_type == 'inventory':
            col_widths = [80, 160, 100, 60, 70, 70]
        elif report_type == 'low_stock':
            col_widths = [80, 160, 100, 100, 100]
        elif report_type == 'movement':
            col_widths = [100, 70, 170, 80, 60, 60]

        table = Table(pdf_data, colWidths=col_widths, repeatRows=1)
        
        # Table Styling
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f172a')), # Dark Slate background
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ]))
        
        story.append(table)
        doc.build(story)
        output.seek(0)
        
        return Response(
            output.getvalue(),
            mimetype="application/pdf",
            headers={"Content-disposition": f"attachment; filename={filename_base}.pdf"}
        )

    flash('Invalid export format requested.', 'danger')
    return redirect(url_for('reports.index'))
