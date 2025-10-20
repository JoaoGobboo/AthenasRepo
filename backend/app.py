import os
from datetime import timedelta
import logging
import time

from dotenv import load_dotenv
from flask import Flask, jsonify, g
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from sqlalchemy.exc import OperationalError
from sqlalchemy import text

from src.models import Base
from src.routes.auth_routes import auth_bp
from src.routes.election_routes import election_bp
from src.routes.vote_routes import vote_bp
from src.utils.db import get_engine, get_session, init_engine, remove_session


def create_app() -> Flask:
    """Application factory used by Flask CLI and tests."""
    load_dotenv()
    app = Flask(__name__)

    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "change-me")
    app.config["JWT_SECRET_KEY"] = app.config["SECRET_KEY"]
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=1)

    database_uri = os.getenv("DATABASE_URI")
    if not database_uri:
        raise RuntimeError("DATABASE_URI environment variable is required")
    init_engine(database_uri)
    wait_for_database()
    Base.metadata.create_all(bind=get_engine())

    CORS(app, resources={r"/api/*": {"origins": "*"}})
    jwt = JWTManager(app)
    register_jwt_callbacks(jwt)

    @app.before_request
    def create_session():
        g.db = get_session()

    @app.teardown_appcontext
    def close_session(exception=None):
        remove_session()

    @app.route("/api/v1/health", methods=["GET"])
    def health_check():
        return jsonify({"status": "ok"}), 200

    register_blueprints(app)
    configure_logging()

    return app


def register_blueprints(app: Flask) -> None:
    app.register_blueprint(auth_bp, url_prefix="/api/v1/auth")
    app.register_blueprint(election_bp, url_prefix="/api/v1/elections")
    app.register_blueprint(vote_bp, url_prefix="/api/v1")


def configure_logging() -> None:
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def register_jwt_callbacks(jwt: JWTManager) -> None:
    @jwt.invalid_token_loader
    def invalid_token_callback(error: str):
        logging.warning("JWT invalido: %s", error)
        return jsonify({"message": "Token invalido"}), 401

    @jwt.unauthorized_loader
    def missing_token_callback(error: str):
        logging.warning("JWT ausente: %s", error)
        return jsonify({"message": "Autenticacao necessaria"}), 401

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        logging.info("JWT expirado para identidade %s", jwt_payload.get("sub"))
        return jsonify({"message": "Token expirado"}), 401


def wait_for_database(max_attempts: int = 10, interval_seconds: int = 2) -> None:
    engine = get_engine()
    for attempt in range(1, max_attempts + 1):
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return
        except OperationalError as exc:
            logging.warning(
                "Banco de dados indisponivel (tentativa %s/%s): %s",
                attempt,
                max_attempts,
                exc,
            )
            time.sleep(interval_seconds)
    raise RuntimeError("Banco de dados nao respondeu dentro do tempo limite.")


if __name__ == "__main__":
    application = create_app()
    application.run(host="0.0.0.0", port=5000)
