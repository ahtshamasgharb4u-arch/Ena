from flask import Flask

from .config import Settings
from .extensions import db, migrate
from .api.profiles import bp as profiles_bp
from .api.queries import bp as queries_bp
from .utils.errors import register_error_handlers


def create_app() -> Flask:
    app = Flask(__name__)
    settings = Settings.from_env()

    app.config["SECRET_KEY"] = settings.secret_key
    app.config["SQLALCHEMY_DATABASE_URI"] = settings.database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    migrate.init_app(app, db)

    app.register_blueprint(profiles_bp)
    app.register_blueprint(queries_bp)
    register_error_handlers(app)

    @app.get("/health")
    def health():
        return {"ok": True}

    return app

