from app.extensions import db
from app.models.inventory import Inventory
from app.models.transaction import Transaction
from app.models.product import Product
from app.models.location import Location
from sqlalchemy.exc import SQLAlchemyError

class InventoryException(Exception):
    """Custom exception class for Inventory violations."""
    pass

class InventoryService:
    @staticmethod
    def stock_in(product_id, location_id, quantity, user_id, supplier_name=None, invoice_number=None, notes=None):
        """
        Increases stock at location for a product and logs a transaction.
        """
        if quantity <= 0:
            raise InventoryException("Quantity must be greater than zero.")

        try:
            # Check if product and location exist
            product = Product.query.filter_by(id=product_id, is_active=True).first()
            if not product:
                raise InventoryException("Product does not exist or is inactive.")
            
            location = Location.query.get(location_id)
            if not location:
                raise InventoryException("Location does not exist.")

            # Get or create inventory record
            inventory = Inventory.query.filter_by(product_id=product_id, location_id=location_id).first()
            if not inventory:
                inventory = Inventory(product_id=product_id, location_id=location_id, quantity=0)
                db.session.add(inventory)

            # Atomically increment quantity
            inventory.quantity += quantity

            # Format notes with invoice and supplier
            invoice_notes = []
            if supplier_name:
                invoice_notes.append(f"Supplier: {supplier_name}")
            if invoice_number:
                invoice_notes.append(f"Invoice: {invoice_number}")
            if notes:
                invoice_notes.append(notes)
            combined_notes = " | ".join(invoice_notes)

            # Create transaction record
            txn = Transaction(
                product_id=product_id,
                user_id=user_id,
                source_location_id=None,
                destination_location_id=location_id,
                quantity=quantity,
                transaction_type='STOCK_IN',
                notes=combined_notes
            )
            db.session.add(txn)
            db.session.commit()
            return inventory
        except SQLAlchemyError as e:
            db.session.rollback()
            raise InventoryException(f"Database error during Stock In: {str(e)}")
        except Exception as e:
            db.session.rollback()
            raise InventoryException(str(e))

    @staticmethod
    def stock_out(product_id, location_id, quantity, user_id, reason=None, notes=None):
        """
        Decreases stock at location for a product and logs a transaction.
        Rejects operation if stock is insufficient.
        """
        if quantity <= 0:
            raise InventoryException("Quantity must be greater than zero.")

        try:
            # Check if product and location exist
            product = Product.query.filter_by(id=product_id, is_active=True).first()
            if not product:
                raise InventoryException("Product does not exist or is inactive.")
            
            location = Location.query.get(location_id)
            if not location:
                raise InventoryException("Location does not exist.")

            # Get inventory record
            inventory = Inventory.query.filter_by(product_id=product_id, location_id=location_id).first()
            if not inventory or inventory.quantity < quantity:
                available = inventory.quantity if inventory else 0
                raise InventoryException(
                    f"Insufficient stock. Requested: {quantity}, Available at {location.name}: {available}."
                )

            # Atomically decrement quantity
            inventory.quantity -= quantity

            # Format notes with reason
            txn_notes = f"Reason: {reason or 'Not Specified'}"
            if notes:
                txn_notes += f" | Notes: {notes}"

            # Create transaction record
            txn = Transaction(
                product_id=product_id,
                user_id=user_id,
                source_location_id=location_id,
                destination_location_id=None,
                quantity=quantity,
                transaction_type='STOCK_OUT',
                notes=txn_notes
            )
            db.session.add(txn)
            db.session.commit()
            return inventory
        except SQLAlchemyError as e:
            db.session.rollback()
            raise InventoryException(f"Database error during Stock Out: {str(e)}")
        except Exception as e:
            db.session.rollback()
            raise InventoryException(str(e))


