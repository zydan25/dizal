from flask import Blueprint
assets_bp=Blueprint("assets",__name__,url_prefix="/assets")
from . import routes
