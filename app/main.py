from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import os
from pathlib import Path

from app.config import settings
from app.database import Base, engine, get_db
from app.models import User, EmailVerificationToken, PasswordResetToken
from app.schemas import UserCreate, LoginRequest, PasswordReset, PasswordResetConfirm
from app.security import SecurityUtils
from app.email_service import EmailService

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.app_name, debug=settings.debug)

# Serve static files
TEMPLATES_DIR = Path(__file__).parent / "templates"
if TEMPLATES_DIR.exists():
    app.mount("/static", StaticFiles(directory=TEMPLATES_DIR), name="static")

@app.get("/", response_class=HTMLResponse)
async def login_page():
    """Login page"""
    return """<!DOCTYPE html>
    <html><head><title>Login</title></head><body>
    <form method='POST' action='/api/auth/login'>
    Email: <input name='email'><br>
    Password: <input name='password' type='password'><br>
    <button>Login</button><br>
    <a href='/register'>Register</a> | <a href='/forgot-password'>Forgot?</a>
    </form></body></html>"""

@app.get("/register", response_class=HTMLResponse)
async def register_page():
    """Registration page"""
    return """<!DOCTYPE html>
    <html><head><title>Register</title></head><body>
    <form method='POST' action='/api/auth/register'>
    Email: <input name='email'><br>
    Username: <input name='username'><br>
    Password: <input name='password' type='password'><br>
    <button>Register</button><br>
    <a href='/'>Login</a>
    </form></body></html>"""

@app.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page():
    """Forgot password page"""
    return """<!DOCTYPE html>
    <html><head><title>Forgot Password</title></head><body>
    <form method='POST' action='/api/auth/forgot-password'>
    Email: <input name='email'><br>
    <button>Reset Password</button><br>
    <a href='/'>Back to Login</a>
    </form></body></html>"""

@app.post("/api/auth/register")
async def register(email: str, username: str, password: str, db: Session = Depends(get_db)):
    existing = db.query(User).filter((User.email == email) | (User.username == username)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email or username already exists")
    
    user = User(email=email, username=username, hashed_password=SecurityUtils.hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    
    token = SecurityUtils.generate_token()
    expires_at = datetime.utcnow() + timedelta(hours=24)
    verify_token = EmailVerificationToken(user_id=user.id, token=token, expires_at=expires_at)
    db.add(verify_token)
    db.commit()
    
    await EmailService.send_verification_email(email, token)
    return {"message": "Check your email for verification link"}

@app.post("/api/auth/login")
async def login(email: str, password: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user or not SecurityUtils.verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_email_verified:
        raise HTTPException(status_code=403, detail="Verify email first")
    
    access_token = SecurityUtils.create_access_token(str(user.id))
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/auth/verify-email")
async def verify_email(token: str, db: Session = Depends(get_db)):
    verify_token = db.query(EmailVerificationToken).filter(EmailVerificationToken.token == token).first()
    if not verify_token or verify_token.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    
    user = db.query(User).filter(User.id == verify_token.user_id).first()
    user.is_email_verified = True
    db.delete(verify_token)
    db.commit()
    return {"message": "Email verified successfully"}

@app.post("/api/auth/forgot-password")
async def forgot_password(email: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return {"message": "If email exists, reset link sent"}
    
    token = SecurityUtils.generate_token()
    expires_at = datetime.utcnow() + timedelta(minutes=30)
    reset_token = PasswordResetToken(user_id=user.id, token=token, expires_at=expires_at)
    db.add(reset_token)
    db.commit()
    
    await EmailService.send_password_reset_email(email, token)
    return {"message": "Check your email for password reset link"}

@app.post("/api/auth/reset-password")
async def reset_password(token: str, new_password: str, db: Session = Depends(get_db)):
    reset_token = db.query(PasswordResetToken).filter(PasswordResetToken.token == token).first()
    if not reset_token or reset_token.expires_at < datetime.utcnow() or reset_token.is_used:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    
    user = db.query(User).filter(User.id == reset_token.user_id).first()
    user.hashed_password = SecurityUtils.hash_password(new_password)
    reset_token.is_used = True
    db.commit()
    return {"message": "Password reset successfully"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
