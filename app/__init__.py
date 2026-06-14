import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

from config import config

db = SQLAlchemy()
jwt = JWTManager()
login_manager = LoginManager()
csrf = CSRFProtect()


def create_app(config_name='development'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Initialize extensions
    db.init_app(app)
    jwt.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'

    # User loader for Flask-Login
    from app.models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Import and register blueprints
    from app.routes.auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.routes.dashboard import dashboard_bp
    app.register_blueprint(dashboard_bp)

    from app.routes.api_dashboard import api_dashboard_bp
    app.register_blueprint(api_dashboard_bp)

    from app.routes.predict import predict_bp
    app.register_blueprint(predict_bp)

    from app.routes.api_predict import api_predict_bp
    app.register_blueprint(api_predict_bp)

    from app.routes.search import search_bp
    app.register_blueprint(search_bp)

    from app.routes.api_search import api_search_bp
    app.register_blueprint(api_search_bp)

    from app.routes.reports import reports_bp
    app.register_blueprint(reports_bp)

    from app.routes.api_reports import api_reports_bp
    app.register_blueprint(api_reports_bp)

    from app.routes.admin import admin_bp
    app.register_blueprint(admin_bp)

    from app.routes.api_admin import api_admin_bp
    app.register_blueprint(api_admin_bp)

    # Exempt API blueprints from CSRF protection (they use JWT)
    csrf.exempt(auth_bp)
    csrf.exempt(api_dashboard_bp)
    csrf.exempt(api_predict_bp)
    csrf.exempt(api_search_bp)
    csrf.exempt(api_reports_bp)
    csrf.exempt(api_admin_bp)

    with app.app_context():
        from app.models import crime, user, prediction, report
        db.create_all()

    return app