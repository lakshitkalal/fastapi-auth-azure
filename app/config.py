import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    app_name: str = "FastAPI Auth"
    debug: bool = os.getenv("DEBUG", "False") == "True"
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./auth.db")
    secret_key: str = os.getenv("SECRET_KEY", "your-secret-key-here-change-in-production")
    smtp_server: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_user: str = os.getenv("SMTP_USER", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

settings = Settings()
