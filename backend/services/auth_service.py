"""Authentication service for JWT and password handling.

Passwords are never stored in plain text: they are hashed with bcrypt (one-way)
and only the hash is stored in users.password_hash. Use get_password_hash when
storing and verify_password when checking login.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from config import get_settings
from backend.utils import db, Roles, Messages
from backend.models import UserCreate, UserResponse, LoginResponse, TokenData

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[TokenData]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: int = payload.get("user_id")
        email: str = payload.get("email")
        role: str = payload.get("role")
        if user_id is None or email is None:
            return None
        return TokenData(user_id=user_id, email=email, role=role)
    except JWTError:
        return None


async def register_user(user_data: UserCreate) -> dict:
    """Register a new user. Email and phone must be unique; password is stored as bcrypt hash only."""
    existing = await db.fetch_one(
        "SELECT user_id FROM users WHERE email = $1",
        user_data.email
    )
    if existing:
        return {"success": False, "message": Messages.EMAIL_EXISTS}

    if user_data.phone:
        existing_phone = await db.fetch_one(
            "SELECT user_id FROM users WHERE phone = $1",
            user_data.phone
        )
        if existing_phone:
            return {"success": False, "message": Messages.PHONE_EXISTS}

    password_hash = get_password_hash(user_data.password)
    
    result = await db.fetch_one(
        """
        INSERT INTO users (full_name, email, phone, password_hash, role)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING user_id, full_name, email, phone, role, created_at
        """,
        user_data.full_name,
        user_data.email,
        user_data.phone,
        password_hash,
        Roles.USER
    )
    
    user = UserResponse(
        user_id=result['user_id'],
        full_name=result['full_name'],
        email=result['email'],
        phone=result['phone'],
        role=result['role'],
        created_at=result['created_at']
    )
    
    access_token = create_access_token({
        "user_id": user.user_id,
        "email": user.email,
        "role": user.role
    })
    
    return {
        "success": True,
        "message": Messages.REGISTER_SUCCESS,
        "data": LoginResponse(access_token=access_token, user=user)
    }


async def authenticate_user(email: str, password: str) -> dict:
    """Authenticate a user and return token."""
    user = await db.fetch_one(
        """
        SELECT user_id, full_name, email, phone, password_hash, role, created_at
        FROM users WHERE email = $1
        """,
        email
    )
    
    if not user:
        return {"success": False, "message": Messages.INVALID_CREDENTIALS}
    
    try:
        password_valid = verify_password(password, user['password_hash'])
    except Exception:
        return {"success": False, "message": Messages.INVALID_CREDENTIALS}
    
    if not password_valid:
        return {"success": False, "message": Messages.INVALID_CREDENTIALS}
    
    user_response = UserResponse(
        user_id=user['user_id'],
        full_name=user['full_name'],
        email=user['email'],
        phone=user['phone'],
        role=user['role'],
        created_at=user['created_at']
    )
    
    access_token = create_access_token({
        "user_id": user['user_id'],
        "email": user['email'],
        "role": user['role']
    })
    
    return {
        "success": True,
        "message": Messages.LOGIN_SUCCESS,
        "data": LoginResponse(access_token=access_token, user=user_response)
    }


async def get_user_by_id(user_id: int) -> Optional[UserResponse]:
    """Get user by ID."""
    user = await db.fetch_one(
        """
        SELECT user_id, full_name, email, phone, role, created_at
        FROM users WHERE user_id = $1
        """,
        user_id
    )
    
    if not user:
        return None
    
    return UserResponse(
        user_id=user['user_id'],
        full_name=user['full_name'],
        email=user['email'],
        phone=user['phone'],
        role=user['role'],
        created_at=user['created_at']
    )


async def update_user_profile(user_id: int, full_name: Optional[str] = None, phone: Optional[str] = None) -> dict:
    """Update user profile."""
    updates = []
    values = []
    param_count = 1
    
    if full_name:
        updates.append(f"full_name = ${param_count}")
        values.append(full_name)
        param_count += 1
    
    if phone:
        existing_phone = await db.fetch_one(
            "SELECT user_id FROM users WHERE phone = $1 AND user_id != $2",
            phone,
            user_id
        )
        if existing_phone:
            return {"success": False, "message": Messages.PHONE_EXISTS}
        updates.append(f"phone = ${param_count}")
        values.append(phone)
        param_count += 1

    if not updates:
        return {"success": False, "message": "No updates provided"}
    
    values.append(user_id)
    query = f"UPDATE users SET {', '.join(updates)} WHERE user_id = ${param_count} RETURNING user_id, full_name, email, phone, role, created_at"
    
    result = await db.fetch_one(query, *values)
    
    if not result:
        return {"success": False, "message": Messages.USER_NOT_FOUND}
    
    return {
        "success": True,
        "message": "Profile updated successfully",
        "data": UserResponse(**dict(result))
    }


async def is_admin(user_id: int) -> bool:
    """Check if user is an admin."""
    admin = await db.fetch_one(
        "SELECT admin_id FROM admins WHERE user_id = $1",
        user_id
    )
    return admin is not None
