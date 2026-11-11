"""Environment-driven configuration. Reads a .env file sitting next to app.py."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"))


class Config:
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "dev-only-change-me")

    DB_HOST = os.environ.get("DB_HOST", "localhost")
    DB_PORT = int(os.environ.get("DB_PORT", "3306"))
    DB_NAME = os.environ.get("DB_NAME", "scheduling_manager")
    DB_USER = os.environ.get("DB_USER", "scheduling_app")
    DB_PASSWORD = os.environ.get("DB_PASSWORD", "##########")

    # Temporary: pretend this user id is logged in until real auth lands.
    STUB_USER_ID = int(os.environ.get("STUB_USER_ID", "1"))

    SQLALCHEMY_URL = (
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}"
        f"@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
    )
