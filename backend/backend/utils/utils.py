from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from backend.config import settings
import hashlib
from jose import jwt

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

security = HTTPBearer()

MAX_PASSWORD_LENGTH = 72

def get_password_hash(password: str) -> str:
    """Hash a password with bcrypt 72-byte limit handling"""
    # Truncate password to 72 bytes if necessary
    if len(password.encode('utf-8')) > MAX_PASSWORD_LENGTH:
        # Pre-hash long passwords using SHA256 to ensure consistent 64-byte hash
        password = hashlib.sha256(password.encode('utf-8')).hexdigest()
    
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password"""
    # Apply same pre-hashing logic for long passwords
    if len(plain_password.encode('utf-8')) > MAX_PASSWORD_LENGTH:
        plain_password = hashlib.sha256(plain_password.encode('utf-8')).hexdigest()
    
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str):
    """Decode and verify a JWT token and return email, name, and role"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        name: str = payload.get("name")
        role: str = payload.get("role")
        if not email:
            return None
        return {"email": email, "name": name, "role": role}
    except JWTError:
        return None


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get the current authenticated user from token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token = credentials.credentials
    user_data = decode_access_token(token)
    if user_data is None:
        raise credentials_exception
    
    return user_data

async def get_current_candidate(current_user: dict = Depends(get_current_user)):
    """Ensure the current user is a candidate"""
    if current_user.get("role") != "candidate":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized. Candidate access required."
        )
    return current_user

async def get_current_hr(current_user: dict = Depends(get_current_user)):
    """Ensure the current user is HR"""
    if current_user.get("role") != "hr":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized. HR access required."
        )
    return current_user

