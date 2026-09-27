from flask import Blueprint
cashbox_bp=Blueprint("cashbox",__name__,url_prefix="/cashbox")
from . import routes
