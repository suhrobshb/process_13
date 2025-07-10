"""
Authentication and Authorization Module
--------------------------------------

This module provides JWT-based authentication and authorization for the AI Engine.
It includes utilities for:
- JWT token creation and validation
- Password hashing and verification
- OAuth2 password bearer scheme setup
- User authentication dependencies
- Role-based access control (RBAC)
- Tenant-aware authentication

Usage:
- Import the get_current_user or get_current_active_user dependencies in your route
- Use the RoleChecker dependency for role-based access control
- Use verify_tenant_access to ensure tenant isolation
"""

import os
from datetime import datetime, timedelta
from typing import Optional, List, Union, Dict, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, Field, ValidationError
from sqlmodel import Session, select

from .database import get_session
from .models.user import User

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# OAuth2 scheme setup
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="token",
    scopes={
        "admin": "Full access to all resources",
        "editor": "Create and edit resources",
        "viewer": "Read-only access to resources",
    },
)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# Models
class Token(BaseModel):
    """Token response model."""
    access_token: str
    token_type: str


class TokenData(BaseModel):
    """Data extracted from a token."""
    username: Optional[str] = None
    scopes: List[str] = []
    tenant_id: Optional[int] = None
    exp: Optional[datetime] = None


class UserInDB(BaseModel):
    """User model with hashed password."""
    id: int
    username: str
    email: str
    full_name: Optional[str] = None
    disabled: bool = False
    hashed_password: str
    roles: List[str] = ["viewer"]
    tenant_id: int


# Password utilities
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate a password hash."""
    return pwd_context.hash(password)


# JWT utilities
def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a new JWT access token.
    
    Args:
        data: Data to encode in the token
        expires_delta: Optional expiration time
        
    Returns:
        JWT token string
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> TokenData:
    """
    Decode and validate a JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        TokenData object with decoded information
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        token_scopes = payload.get("scopes", [])
        tenant_id = payload.get("tenant_id")
        exp = datetime.fromtimestamp(payload.get("exp")) if payload.get("exp") else None
        return TokenData(username=username, scopes=token_scopes, tenant_id=tenant_id, exp=exp)
    except (JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


# Authentication dependencies
async def get_current_user(
    security_scopes: SecurityScopes,
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session),
) -> User:
    """
    Get the current authenticated user from a JWT token.
    
    Args:
        security_scopes: Required security scopes for the endpoint
        token: JWT token from Authorization header
        session: Database session
        
    Returns:
        User object for the authenticated user
        
    Raises:
        HTTPException: If token is invalid or user doesn't have required scopes
    """
    if security_scopes.scopes:
        authenticate_value = f'Bearer scope="{security_scopes.scope_str}"'
    else:
        authenticate_value = "Bearer"
        
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": authenticate_value},
    )
    
    try:
        token_data = decode_token(token)
        if token_data.username is None:
            raise credentials_exception
    except (JWTError, ValidationError):
        raise credentials_exception
    
    # Check if the token has the required scopes
    for scope in security_scopes.scopes:
        if scope not in token_data.scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not enough permissions. Required: {scope}",
                headers={"WWW-Authenticate": authenticate_value},
            )
    
    # Get user from database
    user = session.exec(select(User).where(User.username == token_data.username)).first()
    if user is None:
        raise credentials_exception
        
    # Verify tenant access
    if token_data.tenant_id is not None and user.tenant_id != token_data.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant mismatch",
        )
        
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Get the current active user.
    
    Args:
        current_user: User object from get_current_user dependency
        
    Returns:
        User object if active
        
    Raises:
        HTTPException: If user is disabled
    """
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


# Role-based access control
class RoleChecker:
    """
    Dependency for checking user roles.
    
    Usage:
        @app.get("/admin-only")
        async def admin_route(user: User = Depends(RoleChecker(["admin"]))):
            return {"message": "Admin access granted"}
    """
    
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles
        
    async def __call__(
        self, user: User = Depends(get_current_active_user)
    ) -> User:
        # Use role_names property instead of direct roles access
        for role in self.allowed_roles:
            if role in user.role_names:
                return user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Not enough permissions. Required role: {self.allowed_roles}",
        )


# Tenant isolation utilities
def verify_tenant_access(user: User, tenant_id: int) -> bool:
    """
    Verify that a user has access to a specific tenant.
    
    Args:
        user: User object
        tenant_id: Tenant ID to check access for
        
    Returns:
        True if user has access, False otherwise
    """
    # Admin users can access all tenants
    if "admin" in user.role_names:
        return True
        
    # Regular users can only access their own tenant
    return user.tenant_id == tenant_id


# Authentication helpers
def authenticate_user(username: str, password: str, session: Session) -> Optional[User]:
    """
    Authenticate a user with username and password.
    
    Args:
        username: Username
        password: Plain text password
        session: Database session
        
    Returns:
        User object if authentication successful, None otherwise
    """
    user = session.exec(select(User).where(User.username == username)).first()
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def get_tenant_filter(user: User):
    """
    Get a filter expression for tenant isolation.
    
    Args:
        user: User object
        
    Returns:
        SQLAlchemy filter expression for tenant isolation
    """
    # Admin users can access all tenants
    if "admin" in user.role_names:
        return True
        
    # Regular users can only access their own tenant
    return User.tenant_id == user.tenant_id
