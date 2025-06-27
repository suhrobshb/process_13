import os
from datetime import datetime, timedelta
from typing import List, Dict, Any

from sqlmodel import Session, select, SQLModel

from ai_engine.database import get_session, create_db_and_tables
from ai_engine.models.user import User, Role, Tenant
from ai_engine.auth import get_password_hash, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES

# Configuration for default entities
DEFAULT_TENANT_NAME = os.getenv("DEFAULT_TENANT_NAME", "default_tenant")
DEFAULT_TENANT_DISPLAY_NAME = os.getenv("DEFAULT_TENANT_DISPLAY_NAME", "Default Organization")

DEFAULT_ADMIN_USERNAME = os.getenv("DEFAULT_ADMIN_USERNAME", "admin")
DEFAULT_ADMIN_EMAIL = os.getenv("DEFAULT_ADMIN_EMAIL", "admin@example.com")
DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD", "adminpass")

# Define default roles and their permissions
DEFAULT_ROLES = [
    {
        "name": "admin",
        "description": "Administrator with full access",
        "permissions": ["all:all"],
    },
    {
        "name": "editor",
        "description": "Can create and edit workflows and tasks",
        "permissions": ["workflows:create", "workflows:edit", "tasks:create", "tasks:edit"],
    },
    {
        "name": "viewer",
        "description": "Read-only access to workflows and tasks",
        "permissions": ["workflows:view", "tasks:view"],
    },
]


def init_auth_data():
    """
    Initializes default authentication data:
    - Creates a default tenant if it doesn't exist.
    - Creates default roles (admin, editor, viewer) if they don't exist.
    - Creates a default admin user if it doesn't exist.
    """
    print("Initializing authentication data...")

    # Ensure tables are created
    create_db_and_tables()

    with next(get_session()) as session:
        # 1. Create Default Tenant
        tenant = session.exec(select(Tenant).where(Tenant.name == DEFAULT_TENANT_NAME)).first()
        if not tenant:
            tenant = Tenant(name=DEFAULT_TENANT_NAME, display_name=DEFAULT_TENANT_DISPLAY_NAME)
            session.add(tenant)
            session.commit()
            session.refresh(tenant)
            print(f"Created default tenant: {tenant.name} (ID: {tenant.id})")
        else:
            print(f"Default tenant '{tenant.name}' already exists (ID: {tenant.id})")

        # 2. Create Default Roles
        created_roles = {}
        for role_data in DEFAULT_ROLES:
            role = session.exec(select(Role).where(Role.name == role_data["name"])).first()
            if not role:
                role = Role(**role_data)
                session.add(role)
                session.commit()
                session.refresh(role)
                print(f"Created role: {role.name} (ID: {role.id})")
            else:
                print(f"Role '{role.name}' already exists (ID: {role.id})")
            created_roles[role.name] = role

        # 3. Create Default Admin User
        admin_user = session.exec(select(User).where(User.username == DEFAULT_ADMIN_USERNAME)).first()
        if not admin_user:
            hashed_password = get_password_hash(DEFAULT_ADMIN_PASSWORD)
            admin_user = User(
                username=DEFAULT_ADMIN_USERNAME,
                email=DEFAULT_ADMIN_EMAIL,
                hashed_password=hashed_password,
                full_name="Default Admin",
                tenant_id=tenant.id,
            )
            # Assign admin role
            if "admin" in created_roles:
                admin_user.roles.append(created_roles["admin"])
            session.add(admin_user)
            session.commit()
            session.refresh(admin_user)
            print(f"Created default admin user: {admin_user.username} (ID: {admin_user.id})")
            
            # Generate an access token for the newly created admin user
            access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = create_access_token(
                data={
                    "sub": admin_user.username,
                    "scopes": [role.name for role in admin_user.roles],
                    "tenant_id": admin_user.tenant_id
                },
                expires_delta=access_token_expires
            )
            print(f"Default admin user access token: {access_token}")

        else:
            print(f"Default admin user '{admin_user.username}' already exists (ID: {admin_user.id})")
            # If admin user exists, you might want to regenerate token or provide instructions
            # For now, just print a message
            print("If you need a new token for the existing admin user, log in via the /api/token endpoint.")

    print("Authentication data initialization complete.")


if __name__ == "__main__":
    init_auth_data()
