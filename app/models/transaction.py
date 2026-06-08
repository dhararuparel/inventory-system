from datetime import datetime
from app.extensions import db

class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    source_location_id = db.Column(db.Integer, db.ForeignKey('locations.id'), nullable=True)
    destination_location_id = db.Column(db.Integer, db.ForeignKey('locations.id'), nullable=True)
    quantity = db.Column(db.Integer, nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)  # 'STOCK_IN', 'STOCK_OUT', 'TRANSFER', 'ADJUSTMENT'
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relations
    product = db.relationship('Product', back_populates='transactions')
    user = db.relationship('User', back_populates='transactions')
    source_location = db.relationship('Location', foreign_keys=[source_location_id], back_populates='source_transactions')
    destination_location = db.relationship('Location', foreign_keys=[destination_location_id], back_populates='destination_transactions')

    def __repr__(self):
        return f'<Transaction {self.transaction_type} of {self.quantity} x Product {self.product_id}>'
