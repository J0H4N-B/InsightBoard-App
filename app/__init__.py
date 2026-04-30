"""
app/__init__.py — Application Factory
=======================================
Para agregar un Blueprint:
  1. Créalo en app/blueprints/mi_modulo.py
  2. Impórtalo y regístralo aquí
"""
import os
from flask import Flask
from config import Config


def create_app(config_class=Config) -> Flask:
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), "..", "templates"),
        static_folder=os.path.join(os.path.dirname(__file__), "..", "static"),
    )
    app.config.from_object(config_class)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    from app.blueprints.main     import main_bp
    from app.blueprints.upload   import upload_bp
    from app.blueprints.dashboard import dashboard_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(upload_bp,   url_prefix="/api/upload")
    app.register_blueprint(dashboard_bp, url_prefix="/api/dashboard")

    return app
