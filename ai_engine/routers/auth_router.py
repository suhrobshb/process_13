"""
Authentication Router
-------------------

This module provides authentication and user management endpoints for the AI Engine.
It includes:
- Login (token endpoint)
- User registration
- User management (get current user, update user)
- Tenant management for admins
- Role management for admins
- Password change functionality
"""

# Fix import: need current UTC time for last_login
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select

from ..auth import (
    Token, get_password_hash, verify_password, create_access_token,
    get_current_user, get_current_active_user, RoleChecker, authenticate_user,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from ..database import get_session
from ..models.user import User, Role, Tenant, UserRole

# Create router
router = APIRouter(tags=["auth"])

# Models for request/response
from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    tenant_id: int


class UserRead(BaseModel):
    id: int
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    disabled: bool = False
    tenant_id: int
    roles: List[str] = []


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    disabled: Optional[bool] = None


class TenantCreate(BaseModel):
    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None


class TenantRead(BaseModel):
    id: int
    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    active: bool


class TenantUpdate(BaseModel):
    name: Optional[str] = None
    display_name: Optional[str] = None
    description: Optional[str] = None
    active: Optional[bool] = None


class RoleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    permissions: List[str] = []


class RoleRead(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    permissions: List[str] = []


class RoleUpdate(BaseModel):
    description: Optional[str] = None
    permissions: Optional[List[str]] = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


# Login endpoint
@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session)
):
    """
    OAuth2 compatible token login, get an access token for future requests.
    """
    user = authenticate_user(form_data.username, form_data.password, session)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update last login timestamp
    user.last_login = datetime.utcnow()
    session.add(user)
    session.commit()
    
    # Create access token with user information
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user.username,
            "scopes": [role.name for role in user.roles],
            "tenant_id": user.tenant_id
        },
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


# User registration
@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_create: UserCreate,
    session: Session = Depends(get_session)
):
    """
    Register a new user.
    """
    # Check if username already exists
    db_user = session.exec(select(User).where(User.username == user_create.username)).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Check if email already exists
    db_user = session.exec(select(User).where(User.email == user_create.email)).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Check if tenant exists
    tenant = session.get(Tenant, user_create.tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant not found"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_create.password)
    db_user = User(
        username=user_create.username,
        email=user_create.email,
        hashed_password=hashed_password,
        full_name=user_create.full_name,
        tenant_id=user_create.tenant_id
    )
    
    # Add default viewer role
    viewer_role = session.exec(select(Role).where(Role.name == "viewer")).first()
    if viewer_role:
        db_user.roles.append(viewer_role)
    
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    
    return UserRead(
        id=db_user.id,
        username=db_user.username,
        email=db_user.email,
        full_name=db_user.full_name,
        disabled=db_user.disabled,
        tenant_id=db_user.tenant_id,
        roles=[role.name for role in db_user.roles]
    )


# User management
@router.get("/users/me", response_model=UserRead)
async def read_users_me(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current user information.
    """
    return UserRead(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        disabled=current_user.disabled,
        tenant_id=current_user.tenant_id,
        roles=[role.name for role in current_user.roles]
    )


@router.put("/users/me", response_model=UserRead)
async def update_user_me(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Update current user information.
    """
    # Update user fields if provided
    if user_update.email is not None:
        # Check if email already exists
        db_user = session.exec(
            select(User).where(User.email == user_update.email, User.id != current_user.id)
        ).first()
        if db_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        current_user.email = user_update.email
    
    if user_update.full_name is not None:
        current_user.full_name = user_update.full_name
    
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    
    return UserRead(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        disabled=current_user.disabled,
        tenant_id=current_user.tenant_id,
        roles=[role.name for role in current_user.roles]
    )


@router.post("/users/me/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    password_change: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Change current user's password.
    """
    # Verify current password
    if not verify_password(password_change.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect password"
        )
    
    # Update password
    current_user.hashed_password = get_password_hash(password_change.new_password)
    session.add(current_user)
    session.commit()
    
    return {"message": "Password updated successfully"}


# Admin endpoints for user management
@router.get("/users", response_model=List[UserRead])
async def read_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(RoleChecker(["admin"])),
    session: Session = Depends(get_session)
):
    """
    Get all users (admin only).
    """
    users = session.exec(select(User).offset(skip).limit(limit)).all()
    return [
        UserRead(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            disabled=user.disabled,
            tenant_id=user.tenant_id,
            roles=[role.name for role in user.roles]
        )
        for user in users
    ]


@router.get("/users/{user_id}", response_model=UserRead)
async def read_user(
    user_id: int,
    current_user: User = Depends(RoleChecker(["admin"])),
    session: Session = Depends(get_session)
):
    """
    Get user by ID (admin only).
    """
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserRead(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        disabled=user.disabled,
        tenant_id=user.tenant_id,
        roles=[role.name for role in user.roles]
    )


@router.put("/users/{user_id}", response_model=UserRead)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: User = Depends(RoleChecker(["admin"])),
    session: Session = Depends(get_session)
):
    """
    Update user by ID (admin only).
    """
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update user fields if provided
    if user_update.email is not None:
        # Check if email already exists
        db_user = session.exec(
            select(User).where(User.email == user_update.email, User.id != user_id)
        ).first()
        if db_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        user.email = user_update.email
    
    if user_update.full_name is not None:
        user.full_name = user_update.full_name
    
    if user_update.disabled is not None:
        user.disabled = user_update.disabled
    
    session.add(user)
    session.commit()
    session.refresh(user)
    
    return UserRead(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        disabled=user.disabled,
        tenant_id=user.tenant_id,
        roles=[role.name for role in user.roles]
    )


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    current_user: User = Depends(RoleChecker(["admin"])),
    session: Session = Depends(get_session)
):
    """
    Delete user by ID (admin only).
    """
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent deleting yourself
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own user account"
        )
    
    session.delete(user)
    session.commit()
    
    return None


# Tenant management (admin only)
@router.post("/tenants", response_model=TenantRead, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    tenant_create: TenantCreate,
    current_user: User = Depends(RoleChecker(["admin"])),
    session: Session = Depends(get_session)
):
    """
    Create a new tenant (admin only).
    """
    # Check if tenant name already exists
    db_tenant = session.exec(select(Tenant).where(Tenant.name == tenant_create.name)).first()
    if db_tenant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant name already exists"
        )
    
    # Create new tenant
    db_tenant = Tenant(
        name=tenant_create.name,
        display_name=tenant_create.display_name,
        description=tenant_create.description
    )
    
    session.add(db_tenant)
    session.commit()
    session.refresh(db_tenant)
    
    return TenantRead(
        id=db_tenant.id,
        name=db_tenant.name,
        display_name=db_tenant.display_name,
        description=db_tenant.description,
        active=db_tenant.active
    )


@router.get("/tenants", response_model=List[TenantRead])
async def read_tenants(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(RoleChecker(["admin"])),
    session: Session = Depends(get_session)
):
    """
    Get all tenants (admin only).
    """
    tenants = session.exec(select(Tenant).offset(skip).limit(limit)).all()
    return [
        TenantRead(
            id=tenant.id,
            name=tenant.name,
            display_name=tenant.display_name,
            description=tenant.description,
            active=tenant.active
        )
        for tenant in tenants
    ]


@router.get("/tenants/{tenant_id}", response_model=TenantRead)
async def read_tenant(
    tenant_id: int,
    current_user: User = Depends(RoleChecker(["admin"])),
    session: Session = Depends(get_session)
):
    """
    Get tenant by ID (admin only).
    """
    tenant = session.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    return TenantRead(
        id=tenant.id,
        name=tenant.name,
        display_name=tenant.display_name,
        description=tenant.description,
        active=tenant.active
    )


@router.put("/tenants/{tenant_id}", response_model=TenantRead)
async def update_tenant(
    tenant_id: int,
    tenant_update: TenantUpdate,
    current_user: User = Depends(RoleChecker(["admin"])),
    session: Session = Depends(get_session)
):
    """
    Update tenant by ID (admin only).
    """
    tenant = session.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    # Update tenant fields if provided
    if tenant_update.name is not None:
        # Check if name already exists
        db_tenant = session.exec(
            select(Tenant).where(Tenant.name == tenant_update.name, Tenant.id != tenant_id)
        ).first()
        if db_tenant:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant name already exists"
            )
        tenant.name = tenant_update.name
    
    if tenant_update.display_name is not None:
        tenant.display_name = tenant_update.display_name
    
    if tenant_update.description is not None:
        tenant.description = tenant_update.description
    
    if tenant_update.active is not None:
        tenant.active = tenant_update.active
    
    session.add(tenant)
    session.commit()
    session.refresh(tenant)
    
    return TenantRead(
        id=tenant.id,
        name=tenant.name,
        display_name=tenant.display_name,
        description=tenant.description,
        active=tenant.active
    )


@router.delete("/tenants/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(
    tenant_id: int,
    current_user: User = Depends(RoleChecker(["admin"])),
    session: Session = Depends(get_session)
):
    """
    Delete tenant by ID (admin only).
    """
    tenant = session.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    # Check if tenant has users
    users = session.exec(select(User).where(User.tenant_id == tenant_id)).all()
    if users:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete tenant with users"
        )
    
    session.delete(tenant)
    session.commit()
    
    return None


# Role management (admin only)
@router.post("/roles", response_model=RoleRead, status_code=status.HTTP_201_CREATED)
async def create_role(
    role_create: RoleCreate,
    current_user: User = Depends(RoleChecker(["admin"])),
    session: Session = Depends(get_session)
):
    """
    Create a new role (admin only).
    """
    # Check if role name already exists
    db_role = session.exec(select(Role).where(Role.name == role_create.name)).first()
    if db_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role name already exists"
        )
    
    # Create new role
    db_role = Role(
        name=role_create.name,
        description=role_create.description,
        permissions=role_create.permissions
    )
    
    session.add(db_role)
    session.commit()
    session.refresh(db_role)
    
    return RoleRead(
        id=db_role.id,
        name=db_role.name,
        description=db_role.description,
        permissions=db_role.permissions
    )


@router.get("/roles", response_model=List[RoleRead])
async def read_roles(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(RoleChecker(["admin"])),
    session: Session = Depends(get_session)
):
    """
    Get all roles (admin only).
    """
    roles = session.exec(select(Role).offset(skip).limit(limit)).all()
    return [
        RoleRead(
            id=role.id,
            name=role.name,
            description=role.description,
            permissions=role.permissions
        )
        for role in roles
    ]


@router.get("/roles/{role_id}", response_model=RoleRead)
async def read_role(
    role_id: int,
    current_user: User = Depends(RoleChecker(["admin"])),
    session: Session = Depends(get_session)
):
    """
    Get role by ID (admin only).
    """
    role = session.get(Role, role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    return RoleRead(
        id=role.id,
        name=role.name,
        description=role.description,
        permissions=role.permissions
    )


@router.put("/roles/{role_id}", response_model=RoleRead)
async def update_role(
    role_id: int,
    role_update: RoleUpdate,
    current_user: User = Depends(RoleChecker(["admin"])),
    session: Session = Depends(get_session)
):
    """
    Update role by ID (admin only).
    """
    role = session.get(Role, role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    # Prevent updating built-in roles
    if role.name in ["admin", "editor", "viewer"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify built-in roles"
        )
    
    # Update role fields if provided
    if role_update.description is not None:
        role.description = role_update.description
    
    if role_update.permissions is not None:
        role.permissions = role_update.permissions
    
    session.add(role)
    session.commit()
    session.refresh(role)
    
    return RoleRead(
        id=role.id,
        name=role.name,
        description=role.description,
        permissions=role.permissions
    )


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: int,
    current_user: User = Depends(RoleChecker(["admin"])),
    session: Session = Depends(get_session)
):
    """
    Delete role by ID (admin only).
    """
    role = session.get(Role, role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    # Prevent deleting built-in roles
    if role.name in ["admin", "editor", "viewer"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete built-in roles"
        )
    
    # Remove role from users
    user_roles = session.exec(select(UserRole).where(UserRole.role_id == role_id)).all()
    for user_role in user_roles:
        session.delete(user_role)
    
    session.delete(role)
    session.commit()
    
    return None


# User role management (admin only)
@router.post("/users/{user_id}/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def assign_role_to_user(
    user_id: int,
    role_id: int,
    current_user: User = Depends(RoleChecker(["admin"])),
    session: Session = Depends(get_session)
):
    """
    Assign a role to a user (admin only).
    """
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    role = session.get(Role, role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    # Check if user already has this role
    user_role = session.exec(
        select(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.role_id == role_id
        )
    ).first()
    
    if not user_role:
        # Create new user-role association
        user_role = UserRole(
            user_id=user_id,
            role_id=role_id,
            assigned_by=current_user.username
        )
        session.add(user_role)
        session.commit()
    
    return None


@router.delete("/users/{user_id}/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_role_from_user(
    user_id: int,
    role_id: int,
    current_user: User = Depends(RoleChecker(["admin"])),
    session: Session = Depends(get_session)
):
    """
    Remove a role from a user (admin only).
    """
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    role = session.get(Role, role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    # Check if role is "admin" and this is the last admin user
    if role.name == "admin":
        admin_users = session.exec(
            select(User)
            .join(UserRole, User.id == UserRole.user_id)
            .join(Role, UserRole.role_id == Role.id)
            .where(Role.name == "admin")
        ).all()
        
        if len(admin_users) == 1 and admin_users[0].id == user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove admin role from the last admin user"
            )
    
    # Get user-role association
    user_role = session.exec(
        select(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.role_id == role_id
        )
    ).first()
    
    if user_role:
        session.delete(user_role)
        session.commit()
    
    return None
