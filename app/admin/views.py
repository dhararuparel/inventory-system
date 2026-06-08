from flask import redirect, url_for, flash, request
from flask_admin.contrib.sqla import ModelView
from flask_admin import AdminIndexView, expose
from flask_login import current_user
from app.models.user import User
from app.models.product import Product
from app.models.location import Location
from app.models.inventory import Inventory
from app.models.transaction import Transaction
from app.models.category import Category
from wtforms import SelectField

class SecureModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_admin()

    def inaccessible_callback(self, name, **kwargs):
        flash("You do not have permission to access the admin panel.", "danger")
        return redirect(url_for('auth.login', next=request.url))


class SecureAdminIndexView(AdminIndexView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_admin()

    def inaccessible_callback(self, name, **kwargs):
        flash("You do not have permission to access the admin panel.", "danger")
        return redirect(url_for('auth.login', next=request.url))

    @expose('/')
    def index(self):
        stats = {
            'users_count': User.query.count(),
            'products_count': Product.query.filter_by(is_active=True).count(),
            'locations_count': Location.query.count(),
            'inventory_records': Inventory.query.count(),
            'transactions_count': Transaction.query.count()
        }
        return self.render('admin/custom_index.html', stats=stats)


class UserAdminView(SecureModelView):
    column_list = ('id', 'username', 'role', 'created_at')
    column_searchable_list = ('username', 'role')
    column_filters = ('role', 'created_at')
    form_choices = {
        'role': [('ADMIN', 'Admin'), ('STAFF', 'Staff')]
    }
    # Hash password if edited or created through admin view
    def on_model_change(self, form, model, is_created):
        if form.password_hash.data:
            # Note: password_hash field in form will contain raw password entered by admin
            model.set_password(form.password_hash.data)


class ProductAdminView(SecureModelView):
    column_list = ('id', 'product_code', 'name', 'brand', 'category', 'size', 'purchase_price', 'selling_price', 'minimum_stock', 'is_active')
    column_searchable_list = ('product_code', 'name', 'brand', 'category')
    column_filters = ('category', 'is_active', 'brand')
    form_overrides = {
        'category': SelectField
    }

    def edit_form(self, obj=None):
        form = super(ProductAdminView, self).edit_form(obj)
        form.category.choices = [(c.name, c.name) for c in Category.query.order_by(Category.name.asc()).all()]
        return form

    def create_form(self, obj=None):
        form = super(ProductAdminView, self).create_form(obj)
        form.category.choices = [(c.name, c.name) for c in Category.query.order_by(Category.name.asc()).all()]
        return form


class LocationAdminView(SecureModelView):
    column_list = ('id', 'name')
    column_searchable_list = ('name',)


class InventoryAdminView(SecureModelView):
    column_list = ('id', 'product.product_code', 'product.name', 'location.name', 'quantity')
    column_searchable_list = ('product.product_code', 'product.name', 'location.name')
    column_filters = ('location.name', 'product.category')
    
    # Staff/Admins shouldn't be editing quantity directly inside database tables
    # without registering transactions. However, we allow Admins under secure control.
    form_columns = ('product', 'location', 'quantity')


class TransactionAdminView(SecureModelView):
    # Transactions should only be audited (Read-only)
    can_create = False
    can_edit = False
    can_delete = False
    
    column_list = ('id', 'created_at', 'product.product_code', 'transaction_type', 'quantity', 'source_location.name', 'destination_location.name', 'user.username', 'notes')
    column_searchable_list = ('product.product_code', 'product.name', 'transaction_type', 'notes')
    column_filters = ('transaction_type', 'created_at', 'source_location.name', 'destination_location.name')
    column_sortable_list = ('id', 'created_at', 'quantity')
    column_default_sort = ('created_at', True)


class CategoryAdminView(SecureModelView):
    column_list = ('id', 'name')
    column_searchable_list = ('name',)

