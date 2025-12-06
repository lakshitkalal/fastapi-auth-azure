import uuid
from app.config import settings

class SecurityUtils:
    @staticmethod
    def hash_password(password: str) -> str:
        return password  # Simplified for now
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return plain_password == hashed_password
    
    @staticmethod
    def create_access_token(user_id: str) -> str:
        return str(uuid.uuid4())
    
    @staticmethod
    def generate_token() -> str:
        return str(uuid.uuid4())
