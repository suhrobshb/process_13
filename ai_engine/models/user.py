"""
User and Authentication Models
-----------------------------

This module defines the data models for users, tenants, and roles in the AI Engine.
These models support:
- User authentication
- Multi-tenancy
- Role-based access control (RBAC)
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel, Field, Relationship, Column, String, JSON

# Association table for many-to-many relationship between users and roles
class UserRole(SQLModel, table=True):
    """Association model for the many-to-many relationship between users and roles."""
    
    user_id: int = Field(foreign_key="user.id", primary_key=True)
    role_id: int = Field(foreign_key="role.id", primary_key=True)
    assigned_at: datetime = Field(default_factory=datetime.utcnow)
    assigned_by: Optional[str] = None


class Role(SQLModel, table=True):
    """Role model for role-based access control."""
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    description: Optional[str] = None
    permissions: List[str] = Field(default=[], sa_type=JSON)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    users: List["User"] = Relationship(back_populates="roles", link_model=UserRole)


class Tenant(SQLModel, table=True):
    """Tenant model for multi-tenancy support."""
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    display_name: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    settings: Dict[str, Any] = Field(default={}, sa_type=JSON)
    active: bool = Field(default=True)
    
    # Relationships
    users: List["User"] = Relationship(back_populates="tenant")


class User(SQLModel, table=True):
    """User model for authentication and authorization."""
    
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    email: str = Field(index=True, unique=True)
    hashed_password: str
    full_name: Optional[str] = None
    disabled: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    
    # Tenant relationship (many-to-one)
    tenant_id: int = Field(foreign_key="tenant.id")
    tenant: Tenant = Relationship(back_populates="users")
    
    # Roles relationship (many-to-many)
    roles: List[Role] = Relationship(back_populates="users", link_model=UserRole)
    
    # Additional metadata
    preferences: Dict[str, Any] = Field(default={}, sa_type=JSON)
    
    @property
    def is_active(self) -> bool:
        """Check if user is active."""
        return not self.disabled
    
    @property
    def role_names(self) -> List[str]:
        """Get list of role names for this user."""
        return [role.name for role in self.roles]
    
    def has_role(self, role_name: str) -> bool:
        """Check if user has a specific role."""
        return role_name in self.role_names
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission through any of their roles."""
        for role in self.roles:
            if permission in role.permissions:
                return True
        return False
