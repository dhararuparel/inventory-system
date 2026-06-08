from app.extensions import db

class Location(db.Model):
    __tablename__ = 'locations'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

    # Relationships
    inventories = db.relationship('Inventory', back_populates='location', lazy='dynamic', cascade='all, delete-orphan')
    
    # Relationships for transactions as source and destination
    source_transactions = db.relationship(
        'Transaction', 
        foreign_keys='Transaction.source_location_id',
        back_populates='source_location', 
        lazy='dynamic'
    )
    destination_transactions = db.relationship(
        'Transaction', 
        foreign_keys='Transaction.destination_location_id',
        back_populates='destination_location', 
        lazy='dynamic'
    )

    def __repr__(self):
        return self.name
