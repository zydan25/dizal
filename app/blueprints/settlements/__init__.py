from flask import Blueprint
settlements_bp=Blueprint("settlements",__name__,url_prefix="/settlements")
from . import routes
