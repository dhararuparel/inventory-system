from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, SelectField, IntegerField, DecimalField, TextAreaField, BooleanField
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError, NumberRange, Optional
from app.models.user import User
from app.models.product import Product

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Log In')


class UserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    password = PasswordField('Password', validators=[Optional(), Length(min=6, max=128)])
    role = SelectField('Role', choices=[('STAFF', 'Staff'), ('ADMIN', 'Admin')], validators=[DataRequired()])
    submit = SubmitField('Save User')

    def __init__(self, original_username=None, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)
        self.original_username = original_username

    def validate_username(self, username):
        if username.data != self.original_username:
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError('Username already exists. Please choose a different one.')


class ProductForm(FlaskForm):
    product_code = StringField('Product Code', validators=[DataRequired(), Length(max=50)])
    name = StringField('Product Name', validators=[DataRequired(), Length(max=100)])
    brand = StringField('Brand', validators=[Length(max=50)])
    category = SelectField('Category', validators=[DataRequired()])
    size = StringField('Size', validators=[Length(max=50)])
    purchase_price = DecimalField('Purchase Price', validators=[DataRequired(), NumberRange(min=0.0)])
    selling_price = DecimalField('Selling Price', validators=[DataRequired(), NumberRange(min=0.0)])
    minimum_stock = IntegerField('Minimum Stock Alert Level', validators=[DataRequired(), NumberRange(min=0)])
    description = TextAreaField('Description')
    image = FileField('Product Image', validators=[
        FileAllowed(['jpg', 'png', 'jpeg', 'webp', 'gif'], 'Only images allowed!')
    ])
    is_active = BooleanField('Active Status', default=True)
    submit = SubmitField('Save Product')

    def __init__(self, original_product_code=None, *args, **kwargs):
        super(ProductForm, self).__init__(*args, **kwargs)
        self.original_product_code = original_product_code

    def validate_product_code(self, product_code):
        if product_code.data != self.original_product_code:
            product = Product.query.filter_by(product_code=product_code.data).first()
            if product:
                raise ValidationError('Product Code already exists. Please use a unique code.')

    def validate_selling_price(self, selling_price):
        if self.purchase_price.data is not None and selling_price.data is not None:
            if selling_price.data < self.purchase_price.data:
                raise ValidationError('Selling price should be greater than or equal to purchase price.')


class StockInForm(FlaskForm):
    product_id = SelectField('Product', coerce=int, validators=[DataRequired()])
    quantity = IntegerField('Quantity', validators=[DataRequired(), NumberRange(min=1, message="Quantity must be at least 1")])
    supplier_name = StringField('Supplier Name', validators=[Length(max=100)])
    invoice_number = StringField('Invoice Number', validators=[Length(max=50)])
    notes = TextAreaField('Notes')
    submit = SubmitField('Process Stock In')


class StockOutForm(FlaskForm):
    product_id = SelectField('Product', coerce=int, validators=[DataRequired()])
    quantity = IntegerField('Quantity', validators=[DataRequired(), NumberRange(min=1, message="Quantity must be at least 1")])
    reason = SelectField('Reason', choices=[
        ('Sold', 'Sold / Customer Purchase'),
        ('Damaged', 'Damaged Stock'),
        ('Theft', 'Theft / Stolen'),
        ('Adjustment', 'Stock Adjustment (Deduction)'),
        ('Other', 'Other')
    ], validators=[DataRequired()])
    notes = TextAreaField('Notes')
    submit = SubmitField('Process Stock Out')


class CategoryForm(FlaskForm):
    name = StringField('Category Name', validators=[DataRequired(), Length(min=2, max=50)])
    submit = SubmitField('Add Category')

    def validate_name(self, name):
        from app.models.category import Category
        cat = Category.query.filter(Category.name.ilike(name.data)).first()
        if cat:
            raise ValidationError('Category already exists. Use a unique name.')
