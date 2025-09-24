import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_login import LoginManager

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()

app = Flask(__name__)
# Ensure session secret is available in production
session_secret = os.environ.get("SESSION_SECRET")
if not session_secret:
    if os.environ.get("ENVIRONMENT") == "production":
        raise RuntimeError("SESSION_SECRET environment variable is required in production")
    session_secret = "dev-secret-key"  # Only for development
app.secret_key = session_secret

# Build database URL from individual components for security
db_user = os.environ.get("DB_USERNAME")
db_password = os.environ.get("DB_PASSWORD") 
db_host = os.environ.get("DB_HOST")
db_port = os.environ.get("DB_PORT", "5432")
db_name = os.environ.get("DB_NAME")

if all([db_user, db_password, db_host, db_name]):
    # URL-encode password to handle special characters
    from urllib.parse import quote_plus
    encoded_password = quote_plus(db_password)
    database_url = f"postgresql://{db_user}:{encoded_password}@{db_host}:{db_port}/{db_name}"
else:
    # Fallback to DATABASE_URL if individual components not available
    database_url = os.environ.get("DATABASE_URL", "postgresql://user:pass@localhost/tracetrack")

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'login'  # type: ignore

with app.app_context():
    import models
    try:
        db.create_all()
    except Exception as e:
        print(f"Database setup warning: {e}")

# Add user_loader function for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))
