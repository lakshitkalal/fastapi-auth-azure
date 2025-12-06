# FastAPI Auth with Email Verification & Azure Deployment

**Production-ready FastAPI authentication system with email verification, password reset, and Azure deployment.**

## Features

✅ User Registration with Email Verification  
✅ Login with JWT Token Authentication  
✅ Forgot Password with Time-Limited Reset Links  
✅ SMTP Email Service (Gmail, Office365, etc.)  
✅ Password Hashing with Bcrypt  
✅ PostgreSQL Database with SQLAlchemy ORM  
✅ Docker & Docker Compose Setup  
✅ Azure App Service Deployment  
✅ Azure Application Insights Monitoring  
✅ Infrastructure as Code (Bicep Templates)  

## Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/lakshitkalal/fastapi-auth-azure.git
cd fastapi-auth-azure
```

### 2. Setup Environment
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure .env
```bash
cp .env.example .env
# Edit .env with your settings:
# - Database URL
# - SMTP credentials
# - Secret keys
```

### 4. Run with Docker
```bash
docker-compose up --build
```

Access at: http://localhost:8000

## Project Structure

```
fastapi-auth-azure/
├── app/
│   ├── __init__.py
│   ├── main.py              # Main FastAPI application
│   ├── config.py            # Configuration settings
│   ├── database.py          # Database setup
│   ├── models.py            # SQLAlchemy models
│   ├── schemas.py           # Pydantic schemas
│   ├── security.py          # Password & JWT utilities
│   ├── email_service.py     # SMTP email sending
│   └── templates/           # HTML templates
├── deploy/
│   ├── main.bicep           # Azure Infrastructure as Code
│   └── deploy.sh            # Deployment script
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login user
- `POST /api/auth/verify-email` - Verify email address
- `POST /api/auth/forgot-password` - Request password reset
- `POST /api/auth/reset-password` - Reset password

### Pages
- `GET /` - Login page
- `GET /register` - Registration page
- `GET /forgot-password` - Password reset page
- `GET /health` - Health check

## File Contents Guide

### app/config.py
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    debug: bool = False
    database_url: str = "postgresql://user:password@localhost:5432/fastapi_auth"
    secret_key: str = "change-this-key"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    frontend_url: str = "http://localhost:8000"
    
    class Config:
        env_file = ".env"

settings = Settings()
```

### app/database.py
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### app/models.py
```python
from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from app.database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, index=True)
    username = Column(String(255), unique=True, index=True)
    hashed_password = Column(String(255))
    is_email_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class EmailVerificationToken(Base):
    __tablename__ = "email_verification_tokens"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), index=True)
    token = Column(String(500), unique=True, index=True)
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), index=True)
    token = Column(String(500), unique=True, index=True)
    expires_at = Column(DateTime)
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
```

### app/security.py
```python
from datetime import datetime, timedelta
from typing import Optional
import secrets
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class SecurityUtils:
    @staticmethod
    def hash_password(password: str) -> str:
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def create_access_token(user_id: str, expires_delta: Optional[timedelta] = None):
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
        to_encode = {"sub": user_id, "exp": expire}
        encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
        return encoded_jwt
    
    @staticmethod
    def generate_token() -> str:
        return secrets.token_urlsafe(32)
```

### app/email_service.py
```python
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class EmailService:
    @staticmethod
    async def send_verification_email(email: str, token: str):
        verification_link = f"{settings.frontend_url}/verify-email?token={token}"
        html_content = f"""
        <html><body style="font-family: Arial;">
        <h2>Email Verification</h2>
        <p>Verify your email to activate your account.</p>
        <a href="{verification_link}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Verify Email</a>
        <p>Or visit: {verification_link}</p>
        <p><small>Link expires in 24 hours.</small></p>
        </body></html>
        """
        await EmailService._send_email(email, "Email Verification", html_content)
    
    @staticmethod
    async def send_password_reset_email(email: str, token: str):
        reset_link = f"{settings.frontend_url}/reset-password?token={token}"
        html_content = f"""
        <html><body style="font-family: Arial;">
        <h2>Password Reset</h2>
        <p>Click below to reset your password:</p>
        <a href="{reset_link}" style="background-color: #008CBA; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Reset Password</a>
        <p>Or visit: {reset_link}</p>
        <p><small>Link expires in 30 minutes. If you didn't request this, ignore this email.</small></p>
        </body></html>
        """
        await EmailService._send_email(email, "Password Reset Request", html_content)
    
    @staticmethod
    async def _send_email(recipient: str, subject: str, html_content: str):
        try:
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = settings.smtp_from
            message["To"] = recipient
            part = MIMEText(html_content, "html")
            message.attach(part)
            
            async with aiosmtplib.SMTP(hostname=settings.smtp_server, port=settings.smtp_port) as smtp:
                await smtp.login(settings.smtp_user, settings.smtp_password)
                await smtp.sendmail(settings.smtp_from, [recipient], message.as_string())
            logger.info(f"Email sent to {recipient}: {subject}")
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            raise
```

### Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### docker-compose.yml
```yaml
version: '3.8'
services:
  db:
    image: postgres:15
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
      POSTGRES_DB: fastapi_auth
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://user:password@db:5432/fastapi_auth
    depends_on:
      - db
    volumes:
      - .:/app

volumes:
  postgres_data:
```

## Deployment to Azure

### Prerequisites
```bash
# Install Azure CLI
choco install azure-cli  # Windows
brew install azure-cli   # macOS

# Login to Azure
az login
```

### Deploy
```bash
# Create resource group
az group create --name fastapi-auth-rg --location eastus

# Deploy web app
az webapp up \
  --resource-group fastapi-auth-rg \
  --name fastapi-auth-app \
  --runtime python:3.11

# Configure environment variables
az webapp config appsettings set \
  --resource-group fastapi-auth-rg \
  --name fastapi-auth-app \
  --settings @appsettings.json
```

## Configuration Files Still Needed

Create these files in your local repository:

1. **app/__init__.py** - Empty file
2. **app/schemas.py** - Pydantic models
3. **.env.example** - Environment template
4. **deploy/main.bicep** - Azure IaC
5. Additional frontend HTML templates

## Support

For issues, check:
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/)
- [Azure Documentation](https://docs.microsoft.com/azure/)

## License

MIT License
