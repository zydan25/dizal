from flask import Blueprint
capital_bp=Blueprint("capital",__name__,url_prefix="/capital")
from . import routes
