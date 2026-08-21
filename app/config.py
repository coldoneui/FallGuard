# Database Configuration
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    PORT = int(os.getenv("PORT", 4000))

    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", 3306))
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "fallguard")

    JWT_SECRET = os.getenv("JWT_SECRET", "dev_secret_change_me")
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRES_MINUTES = int(os.getenv("JWT_EXPIRES_MINUTES", 10080))

    CLIENT_ORIGIN = os.getenv("CLIENT_ORIGIN", "*")
    DEVICE_API_KEY = os.getenv("DEVICE_API_KEY", "change_this_device_key")


settings = Settings()
