import os
from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.products import products_bp
from app.extensions import db
from app.models.product import Product
from app.models.inventory import Inventory
from app.models.category import Category
from app.forms import ProductForm, CategoryForm
from app.utils.decorators import admin_required

# Helper to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

@products_bp.route('/')
@products_bp.route('/products')
@login_required
def list_products():
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('search', '', type=str)
    category_filter = request.args.get('category', '', type=str)
    status_filter = request.args.get('status', 'active', type=str)  # active, inactive, all

    query = Product.query

    # Apply search filter (matches name, code, brand, size)
    if search_query:
        query = query.filter(
            (Product.name.ilike(f'%{search_query}%')) |
            (Product.product_code.ilike(f'%{search_query}%')) |
            (Product.brand.ilike(f'%{search_query}%')) |
            (Product.size.ilike(f'%{search_query}%'))
        )

    # Apply category filter
    if category_filter:
        query = query.filter(Product.category == category_filter)

    # Apply active status filter
    if status_filter == 'active':
        query = query.filter(Product.is_active == True)
    elif status_filter == 'inactive':
        query = query.filter(Product.is_active == False)
    # If 'all', do not apply is_active filter (displays deleted as well)

    # Paginate products
    pagination = query.order_by(Product.product_code.asc()).paginate(
        page=page, per_page=10, error_out=False
    )
    products = pagination.items

    # Fetch product categories dynamically
    categories = [c.name for c in Category.query.order_by(Category.name.asc()).all()]

    return render_template(
        'products/list.html',
        products=products,
        pagination=pagination,
        search_query=search_query,
        category_filter=category_filter,
        status_filter=status_filter,
        categories=categories
    )

@products_bp.route('/product/<int:id>')
@login_required
def view_product(id):
    product = Product.query.get_or_404(id)
    # Get inventories for this product across all locations
    inventories = product.inventories.all()
    return render_template('products/view.html', product=product, inventories=inventories)

@products_bp.route('/products/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_product():
    form = ProductForm()
    # Populate dynamic choices
    categories_list = Category.query.order_by(Category.name.asc()).all()
    form.category.choices = [(c.name, c.name) for c in categories_list]
    if form.validate_on_submit():
        filename = None
        # Handle file upload
        if form.image.data:
            file = form.image.data
            if allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Ensure filename is unique by prefixing time/random if needed, or simple name
                # Create upload directory if it doesn't exist
                os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
                file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            else:
                flash('Invalid file extension. Please upload an image (png, jpg, jpeg, webp, gif).', 'danger')
                return render_template('products/product_form.html', form=form, title='Add Product')

        product = Product(
            product_code=form.product_code.data.upper(),
            name=form.name.data,
            brand=form.brand.data,
            category=form.category.data,
            size=form.size.data,
            purchase_price=form.purchase_price.data,
            selling_price=form.selling_price.data,
            minimum_stock=form.minimum_stock.data,
            description=form.description.data,
            image=filename,
            is_active=form.is_active.data
        )

        db.session.add(product)
        db.session.commit()
        flash(f'Product "{product.name}" created successfully.', 'success')
        return redirect(url_for('products.list_products'))

    return render_template('products/product_form.html', form=form, title='Add Product')

@products_bp.route('/products/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_product(id):
    product = Product.query.get_or_404(id)
    form = ProductForm(original_product_code=product.product_code)
    # Populate dynamic choices
    categories_list = Category.query.order_by(Category.name.asc()).all()
    form.category.choices = [(c.name, c.name) for c in categories_list]

    if form.validate_on_submit():
        # Handle image upload if a new file is provided
        if form.image.data:
            file = form.image.data
            if allowed_file(file.filename):
                filename = secure_filename(file.filename)
                os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
                file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                product.image = filename
            else:
                flash('Invalid file extension. Please upload an image.', 'danger')
                return render_template('products/product_form.html', form=form, title='Edit Product', product=product)

        product.product_code = form.product_code.data.upper()
        product.name = form.name.data
        product.brand = form.brand.data
        product.category = form.category.data
        product.size = form.size.data
        product.purchase_price = form.purchase_price.data
        product.selling_price = form.selling_price.data
        product.minimum_stock = form.minimum_stock.data
        product.description = form.description.data
        product.is_active = form.is_active.data

        db.session.commit()
        flash(f'Product "{product.name}" updated successfully.', 'success')
        return redirect(url_for('products.list_products'))

    elif request.method == 'GET':
        form.product_code.data = product.product_code
        form.name.data = product.name
        form.brand.data = product.brand
        form.category.data = product.category
        form.size.data = product.size
        form.purchase_price.data = product.purchase_price
        form.selling_price.data = product.selling_price
        form.minimum_stock.data = product.minimum_stock
        form.description.data = product.description
        form.is_active.data = product.is_active

    return render_template('products/product_form.html', form=form, title='Edit Product', product=product)

@products_bp.route('/products/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_product(id):
    product = Product.query.get_or_404(id)
    # Soft delete product
    product.is_active = False
    db.session.commit()
    flash(f'Product "{product.name}" soft deleted successfully.', 'success')
    return redirect(url_for('products.list_products'))

@products_bp.route('/products/restore/<int:id>', methods=['POST'])
@login_required
@admin_required
def restore_product(id):
    product = Product.query.get_or_404(id)
    product.is_active = True
    db.session.commit()
    flash(f'Product "{product.name}" restored successfully.', 'success')
    return redirect(url_for('products.list_products'))

@products_bp.route('/products/purge/<int:id>', methods=['POST'])
@login_required
@admin_required
def purge_product(id):
    product = Product.query.get_or_404(id)
    name = product.name
    db.session.delete(product)
    db.session.commit()
    flash(f'Product "{name}" permanently deleted from system.', 'success')
    return redirect(url_for('products.list_products'))


@products_bp.route('/products/categories', methods=['GET', 'POST'])
@login_required
@admin_required
def list_categories():
    form = CategoryForm()
    if form.validate_on_submit():
        category = Category(name=form.name.data.strip())
        db.session.add(category)
        db.session.commit()
        flash(f'Category "{category.name}" added successfully.', 'success')
        return redirect(url_for('products.list_categories'))
    
    categories = Category.query.order_by(Category.name.asc()).all()
    return render_template('products/categories.html', categories=categories, form=form)


@products_bp.route('/products/categories/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_category(id):
    category = Category.query.get_or_404(id)
    # Check if there are any products using this category
    product_count = Product.query.filter_by(category=category.name).count()
    if product_count > 0:
        flash(f'Cannot delete category "{category.name}" because it is currently assigned to {product_count} product(s).', 'danger')
        return redirect(url_for('products.list_categories'))

    name = category.name
    db.session.delete(category)
    db.session.commit()
    flash(f'Category "{name}" deleted successfully.', 'success')
    return redirect(url_for('products.list_categories'))
