import os
import random
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, status, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from backend.models import CandidateCreate, HRCreate, CandidateOut, HROut
from backend.utils.utils import (
    get_password_hash, 
    verify_password, 
    create_access_token,
    MAX_PASSWORD_LENGTH,
    decode_access_token ,
    get_current_user# ✅ Make sure this exists (see note below)
)
from backend.db import get_collection
from backend.config import settings
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from pydantic import BaseModel, EmailStr
from backend.utils.email_service import send_email

router = APIRouter(prefix="/auth", tags=["Authentication"])

RESET_CODE_EXPIRY_MINUTES = 15

# -----------------------------
# Pydantic Models
# -----------------------------
class ForgotPasswordRequest(BaseModel):
    email: EmailStr
    role: str  # candidate or hr

class VerifyCodeRequest(BaseModel):
    email: EmailStr
    role: str
    code: str

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    role: str
    code: str
    new_password: str
class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    role: str


# -----------------------------
# Helpers
# -----------------------------
def send_reset_email(to_email: str, code: str):
    """Send password reset code using SMTP"""
    subject = "Your Password Reset Code"
    html_content = f"""
        <h2>Password Reset Request</h2>
        <p>Your password reset code is:</p>
        <h3 style='color:#9D42D2FF'>{code}</h3>
        <p>This code will expire in {RESET_CODE_EXPIRY_MINUTES} minutes.</p>
    """
    send_email(to_email, subject, html_content)


def generate_code(length: int = 6) -> str:
    return ''.join([str(random.randint(0, 9)) for _ in range(length)])


def validate_password(password: str) -> tuple[bool, str]:
    """Validate password requirements"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if len(password) > 128:
        return False, "Password must not exceed 128 characters"
    return True, ""


# -----------------------------
# Registration Routes
# -----------------------------
@router.post("/register/candidate", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register_candidate(candidate: CandidateCreate):
    """Register a new candidate"""
    is_valid, error_msg = validate_password(candidate.password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    
    candidates_collection = get_collection("candidates")
    
    # Check if email already exists
    existing_user = candidates_collection.find_one({"email": candidate.email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Hash password
    hashed_password = get_password_hash(candidate.password)
    
    # Create candidate document
    candidate_dict = candidate.model_dump(exclude={"password"})
    candidate_dict["password"] = hashed_password
    
    # Insert into database
    result = candidates_collection.insert_one(candidate_dict)
    
    # Create access token
    access_token = create_access_token(
        data={"sub": candidate.email, "role": "candidate"}
    )
    
    return {
        "message": "Candidate registered successfully",
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": str(result.inserted_id)
    }

@router.post("/register/hr", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register_hr(hr: HRCreate):
    """Register a new HR recruiter"""
    is_valid, error_msg = validate_password(hr.password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    
    hr_collection = get_collection("hr_users")
    
    # Check if email already exists
    existing_user = hr_collection.find_one({"email": hr.email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Hash password
    hashed_password = get_password_hash(hr.password)
    
    # Create HR document
    hr_dict = hr.model_dump(exclude={"password"})
    hr_dict["password"] = hashed_password
    
    # Insert into database
    result = hr_collection.insert_one(hr_dict)
    
    # Create access token
    access_token = create_access_token(
        data={"sub": hr.email, "role": "hr"}
    )
    
    return {
        "message": "HR registered successfully",
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": str(result.inserted_id)
    }

# -----------------------------
# Login
# -----------------------------

@router.post("/login", response_model=dict)
async def login(request: LoginRequest):
    email = request.email
    password = request.password
    role = request.role

    collection_name = "candidates" if role == "candidate" else "hr_users"
    collection = get_collection(collection_name)

    user = collection.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect email")

    if not verify_password(password, user["password"]):
        raise HTTPException(status_code=401, detail="Incorrect password")

    access_token = create_access_token(data={"sub": email, "role": role, "name":    user.get("name", "")})
    return {"access_token": access_token, "token_type": "bearer", "role": role, "email": email, "name": user.get("name", "")}
# -----------------------------
# Forgot / Reset Password
# -----------------------------
@router.post("/forgot-password", response_model=dict)
async def forgot_password(data: ForgotPasswordRequest):
    """Send a reset code to the user's email"""
    collection_name = "candidates" if data.role == "candidate" else "hr_users"
    collection = get_collection(collection_name)

    user = collection.find_one({"email": data.email})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    code = generate_code()
    expiry = datetime.utcnow() + timedelta(minutes=RESET_CODE_EXPIRY_MINUTES)

    # Save code and expiry in DB
    collection.update_one(
        {"email": data.email},
        {"$set": {"reset_code": code, "reset_code_expiry": expiry}}
    )

    send_reset_email(data.email, code)
    return {"message": "Reset code sent to email"}


@router.post("/verify-reset-code", response_model=dict)
async def verify_reset_code(data: VerifyCodeRequest):
    """Verify the reset code"""
    collection_name = "candidates" if data.role == "candidate" else "hr_users"
    collection = get_collection(collection_name)

    user = collection.find_one({"email": data.email})
    if not user or "reset_code" not in user or "reset_code_expiry" not in user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No reset request found")

    if user["reset_code"] != data.code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid code")

    if datetime.utcnow() > user["reset_code_expiry"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Code expired")

    return {"message": "Code verified successfully"}


@router.post("/reset-password", response_model=dict)
async def reset_password(data: ResetPasswordRequest):
    """Reset password after verifying the code"""
    collection_name = "candidates" if data.role == "candidate" else "hr_users"
    collection = get_collection(collection_name)

    user = collection.find_one({"email": data.email})
    if not user or "reset_code" not in user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No reset request found")

    if user["reset_code"] != data.code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid code")

    if datetime.utcnow() > user["reset_code_expiry"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Code expired")

    # Validate new password
    is_valid, error_msg = validate_password(data.new_password)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)

    hashed_password = get_password_hash(data.new_password)

    # Update password and remove reset code
    collection.update_one(
        {"email": data.email},
        {"$set": {"password": hashed_password}, "$unset": {"reset_code": "", "reset_code_expiry": ""}}
    )

    return {"message": "Password reset successfully"}


# -----------------------------
# Logout (Token Blacklist)
# -----------------------------
def blacklist_token(token: str):
    """Store a JWT token in the blacklist collection."""
    collection = get_collection("blacklisted_tokens")
    if not collection.find_one({"token": token}):
        collection.insert_one({
            "token": token,
            "blacklisted_at": datetime.utcnow()
        })


def is_token_blacklisted(token: str) -> bool:
    """Check whether a token is blacklisted."""
    collection = get_collection("blacklisted_tokens")
    return collection.find_one({"token": token}) is not None


@router.post("/logout", response_model=dict)
async def logout(
    request: Request,
    current_user: dict = Depends(get_current_user)  # ✅ auto-extracts user & token
):
    """
    Logout the authenticated user.
    Requires `Authorization: Bearer <token>` header.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    token = auth_header.split(" ", 1)[1].strip()

    # Validate token (decode)
    try:
        decode_access_token(token)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid token: {str(e)}")

    # Check blacklist
    if is_token_blacklisted(token):
        return {"message": "Token already invalidated"}

    # Blacklist it
    blacklist_token(token)

    return {
        "message": f"Logout successful for {current_user.get('email', 'unknown user')}"
    }