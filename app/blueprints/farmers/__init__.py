from flask import Blueprint
farmers_bp=Blueprint("farmers",__name__,url_prefix="/farmers")
from . import routes
