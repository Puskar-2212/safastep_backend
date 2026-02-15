"""
Admin Authentication Routes
Handles admin login and token validation
"""
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from datetime import datetime, timedelta
import jwt
import hashlib
import os
from typing import Optional

router = APIRouter()

# Admin credentials (in production, store in database with hashed passwords)
ADMIN_CREDENTIALS = {
    "admin": {
        "password_hash": hashlib.sha256("admin123".encode()).hexdigest(),
        "role": "super_admin"
    }
}

# JWT settings
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8 hours

class AdminLoginRequest(BaseModel):
    username: str
    password: str

class AdminLoginResponse(BaseModel):
    success: bool
    token: str
    username: str
    role: str
    message: str

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(authorization: str = Header(None)):
    """Verify JWT token from Authorization header"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    
    try:
        # Extract token from "Bearer <token>"
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authentication scheme")
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        return {"username": username, "role": payload.get("role")}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid authorization header format")

@router.post("/admin/login", response_model=AdminLoginResponse)
async def admin_login(credentials: AdminLoginRequest):
    """
    Admin login endpoint
    Returns JWT token on successful authentication
    """
    username = credentials.username
    password = credentials.password
    
    # Check if admin exists
    if username not in ADMIN_CREDENTIALS:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    # Verify password
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    if password_hash != ADMIN_CREDENTIALS[username]["password_hash"]:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    # Create access token
    access_token = create_access_token(
        data={
            "sub": username,
            "role": ADMIN_CREDENTIALS[username]["role"]
        }
    )
    
    return AdminLoginResponse(
        success=True,
        token=access_token,
        username=username,
        role=ADMIN_CREDENTIALS[username]["role"],
        message="Login successful"
    )

@router.get("/admin/verify")
async def verify_admin_token(user_data: dict = Depends(verify_token)):
    """
    Verify admin token
    Returns user data if token is valid
    """
    return {
        "success": True,
        "username": user_data["username"],
        "role": user_data["role"],
        "message": "Token is valid"
    }

@router.post("/admin/logout")
async def admin_logout(user_data: dict = Depends(verify_token)):
    """
    Admin logout endpoint
    (Token invalidation would be handled client-side by removing the token)
    """
    return {
        "success": True,
        "message": "Logged out successfully"
    }
