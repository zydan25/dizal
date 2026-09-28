import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "change-this-in-production")
    SECURITY_PASSWORD_SALT = os.getenv("SECURITY_PASSWORD_SALT", "change-this-too")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///dizal-dev.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    WTF_CSRF_ENABLED = True
    WTF_CSRF_CHECK_DEFAULT = False
    WTF_CSRF_TIME_LIMIT = None
    SECURITY_PASSWORD_HASH = "argon2"
    SECURITY_USERNAME_ENABLE = True
    SECURITY_REGISTERABLE = False
    SECURITY_RECOVERABLE = False
    SECURITY_CONFIRMABLE = False
    SECURITY_TRACKABLE = True
    SECURITY_CHANGEABLE = True
    SECURITY_FLASH_MESSAGES = False
    SECURITY_CSRF_PROTECT_MECHANISMS = ["session"]
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "instance/uploads")
    PROJECT_TIMEZONE = os.getenv("PROJECT_TIMEZONE", "Asia/Aden")
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024
