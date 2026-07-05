import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()


def create_app():
    app = Flask(__name__)

    # ── Config ────────────────────────────────────────────────────────────────
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    # Default to SQLite for local dev — no Postgres install needed
    database_url = os.environ.get("DATABASE_URL") or "sqlite:///tutoraz_dev.db"
    # Render / Heroku supply postgres:// — SQLAlchemy needs postgresql://
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["MAX_CONTENT_LENGTH"] = 1000 * 1024 * 1024  # 4 MB upload limit

    # Stripe (test mode keys — get from dashboard.stripe.com/test/apikeys)
    app.config["STRIPE_SECRET_KEY"]      = os.environ.get("STRIPE_SECRET_KEY", "")
    app.config["STRIPE_PUBLISHABLE_KEY"] = os.environ.get("STRIPE_PUBLISHABLE_KEY", "")
    app.config["STRIPE_WEBHOOK_SECRET"]  = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    app.config["PLATFORM_FEE_PERCENT"]   = 10   # platform takes 10%, tutor gets 90%
    app.config["DOMAIN"] = os.environ.get("DOMAIN", "http://localhost:5000")

    import stripe
    stripe.api_key = app.config["STRIPE_SECRET_KEY"]

    # ── Extensions ────────────────────────────────────────────────────────────
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please sign in to continue."
    login_manager.login_message_category = "info"

    # ── Blueprints ────────────────────────────────────────────────────────────
    from app.routes.auth import auth_bp
    from app.routes.tutor import tutor_bp
    from app.routes.student import student_bp
    from app.routes.groups import groups_bp
    from app.routes.main import main_bp
    from app.routes.courses import courses_bp
    from app.routes.payments import payments_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(tutor_bp, url_prefix="/tutor")
    app.register_blueprint(student_bp, url_prefix="/search")
    app.register_blueprint(groups_bp, url_prefix="/groups")
    app.register_blueprint(courses_bp, url_prefix="/courses")
    app.register_blueprint(payments_bp, url_prefix="/payments")

    # ── User loader ───────────────────────────────────────────────────────────
    from app.models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    return app
