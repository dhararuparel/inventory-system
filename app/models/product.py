from datetime import datetime
from app.extensions import db

class Product(db.Model):
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    product_code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    brand = db.Column(db.String(50))
    category = db.Column(db.String(50), nullable=False)  # Cycle, Tyre, Tube, Rim, Spare Part, Accessory
    size = db.Column(db.String(50))
    purchase_price = db.Column(db.Numeric(10, 2), nullable=False)
    selling_price = db.Column(db.Numeric(10, 2), nullable=False)
    minimum_stock = db.Column(db.Integer, default=10, nullable=False)
    description = db.Column(db.Text)
    image = db.Column(db.String(255))  # Stores image filename
    is_active = db.Column(db.Boolean, default=True, nullable=False)  # Soft delete
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    inventories = db.relationship('Inventory', back_populates='product', lazy='dynamic', cascade='all, delete-orphan')
    transactions = db.relationship('Transaction', back_populates='product', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def product_name(self):
        return self.name

    @product_name.setter
    def product_name(self, value):
        self.name = value

    def get_total_stock(self):
        return sum(inv.quantity for inv in self.inventories if inv.quantity > 0)

    def __repr__(self):
        return f'<Product {self.product_code} - {self.name}>'
