"""
config.py — Configuración centralizada
"""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY: str         = os.getenv("SECRET_KEY", "dev-secret-change-in-prod")
    UPLOAD_FOLDER: str      = os.getenv("UPLOAD_FOLDER", "data/uploads")
    ALLOWED_EXTENSIONS: set = {"csv"}
    MAX_CONTENT_LENGTH: int = int(os.getenv("MAX_CONTENT_LENGTH", 5 * 1024 * 1024))
    DEBUG: bool             = os.getenv("FLASK_ENV", "development") == "development"
