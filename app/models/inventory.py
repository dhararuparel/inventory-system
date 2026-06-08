from app.extensions import db

class Inventory(db.Model):
    __tablename__ = 'inventory'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey('locations.id'), nullable=False)
    quantity = db.Column(db.Integer, default=0, nullable=False)

    # Relations
    product = db.relationship('Product', back_populates='inventories')
    location = db.relationship('Location', back_populates='inventories')

    # Unique constraint: product_id + location_id
    __table_args__ = (
        db.UniqueConstraint('product_id', 'location_id', name='uq_product_location'),
        db.CheckConstraint('quantity >= 0', name='ck_inventory_quantity_nonnegative'),
    )

    def __repr__(self):
        return f'<Inventory Product {self.product_id} @ Location {self.location_id}: {self.quantity}>'
