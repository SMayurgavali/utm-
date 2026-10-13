import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_name: str = "AI-Powered UTM Cloud Hub"
    app_env: str = os.getenv("UTM_ENV", "development")
    secret_key: str = os.getenv("UTM_SECRET_KEY", "change-this-secret-key-in-production")
    database_path: str = os.getenv("UTM_DB_PATH", "utm_client_data.db")
    session_ttl_seconds: int = int(os.getenv("UTM_SESSION_TTL_SECONDS", "28800"))
    admin_email: str = os.getenv("UTM_BOOTSTRAP_ADMIN_EMAIL", "mayurgavali4444@gmail.com")
    admin_password: str = os.getenv("UTM_BOOTSTRAP_ADMIN_PASSWORD", "Software@123")
    device_token: str = os.getenv("UTM_DEVICE_TOKEN", "")
    enable_reference_curves: bool = os.getenv("UTM_ENABLE_REFERENCE_CURVES", "0") == "1"


settings = Settings()
