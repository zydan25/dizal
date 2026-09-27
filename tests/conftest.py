import pytest
from app import create_app

@pytest.fixture()
def app():
    return create_app({"TESTING":True,"SQLALCHEMY_DATABASE_URI":"sqlite://","WTF_CSRF_ENABLED":False,"SECRET_KEY":"test","SECURITY_PASSWORD_SALT":"test"})
