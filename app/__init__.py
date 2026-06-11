import os
from flask import Flask
from config import Config
from app.extensions import db, login_manager


def create_app():
    app = Flask(
    __name__,
    template_folder="../templates",
    static_folder="../static"
)
    app.config.from_object(Config)

    os.makedirs(app.config["OUTPUT_DIR"], exist_ok=True)
    os.makedirs(app.config["REPORT_DIR"], exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    from app.routes.auth import auth_bp
    from app.routes.admin import admin_bp
    from app.routes.public import public_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(public_bp)

    return app