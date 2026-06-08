from flask import Blueprint

transactions_bp = Blueprint('transactions', __name__)

from app.transactions import routes
