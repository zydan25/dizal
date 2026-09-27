from flask_login import current_user
from .models import ProjectSettings,Notification
from .navigation import build_navigation

def register_context(app):
    @app.context_processor
    def inject():
        settings=ProjectSettings.get()
        unread=0
        navigation=[]
        if current_user.is_authenticated:
            unread=Notification.query.filter_by(user_id=current_user.id,read_at=None).count()
            navigation=build_navigation(current_user)
        return {"project_settings":settings,"navigation":navigation,"unread_notifications":unread}
