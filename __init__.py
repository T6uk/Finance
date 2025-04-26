# __init__.py
from flask import Flask
from datetime import datetime
import os

from .extensions import db


def create_app():
    # Initialize Flask app
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your-secret-key'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///money_manager.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize extensions
    db.init_app(app)

    # Add context processor to make now() available in templates
    @app.context_processor
    def utility_processor():
        return {'now': datetime.now}

    # Register blueprints
    from .routes.auth import auth_bp
    from .routes.dashboard import dashboard_bp
    from .routes.expense import expense_bp
    from .routes.income import income_bp
    from .routes.budget import budget_bp
    from .routes.category import category_bp
    from .routes.recurring import recurring_bp
    from .routes.savings import savings_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(expense_bp)
    app.register_blueprint(income_bp)
    app.register_blueprint(budget_bp)
    app.register_blueprint(category_bp)
    app.register_blueprint(recurring_bp)
    app.register_blueprint(savings_bp)

    return app