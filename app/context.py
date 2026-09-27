from flask import request
from flask_login import current_user
from .models import ProjectSettings
from .navigation import build_navigation

def register_context(app):
    @app.context_processor
    def inject_context():
        settings=ProjectSettings.get()
        return {"project_settings":settings,"navigation":build_navigation(current_user),"request_path":request.path}
