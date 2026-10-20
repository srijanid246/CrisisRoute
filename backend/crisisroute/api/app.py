from flask import Flask
from flask_cors import CORS

from .db import build_engine, build_session_factory, init_db
from .routes import api_bp

DEFAULT_DATABASE_URL = "sqlite:///crisisroute.db"


def create_app(database_url: str = DEFAULT_DATABASE_URL) -> Flask:
    app = Flask(__name__)
    CORS(app)

    engine = build_engine(database_url)
    init_db(engine)
    app.config["SESSION_FACTORY"] = build_session_factory(engine)
    app.config["DATABASE_URL"] = database_url

    app.register_blueprint(api_bp)

    return app
