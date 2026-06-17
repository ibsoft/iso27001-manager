import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-in-production-32chars!")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///../instance/isms.db")

    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith("sqlite"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace(
            "sqlite:///", "sqlite:///"
        )

    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600

    SESSION_TYPE = os.getenv("SESSION_TYPE", "filesystem")
    SESSION_REDIS = os.getenv("SESSION_REDIS")
    SESSION_PERMANENT = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.getenv("MAIL_PORT", 587))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "noreply@example.com")

    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "app", "static", "uploads")
    ALLOWED_EXTENSIONS = {"pdf", "doc", "docx", "xls", "xlsx", "png", "jpg", "jpeg"}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

    TOTP_ISSUER_NAME = os.getenv("TOTP_ISSUER_NAME", "ISO27001-Manager")
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@example.com")

    ACCOUNT_LOCKOUT_ATTEMPTS = 5
    ACCOUNT_LOCKOUT_MINUTES = 15
    PASSWORD_MIN_LENGTH = 12

    LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
    LOG_LEVEL = "INFO"
    LANGUAGES = {"en": "English", "el": "Ελληνικά"}
    BABEL_DEFAULT_LOCALE = "en"

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", "sqlite:///../instance/isms_dev.db"
    )
    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith("sqlite:///"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace(
            "sqlite:///", "sqlite:///"
        )


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = "Strict"
    TALISMAN_FORCE_HTTPS = True


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
