from flask import Blueprint

excel_bp = Blueprint('excel', __name__)

from app.excel import routes
