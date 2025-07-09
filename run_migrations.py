#!/usr/bin/env python3
"""
Database Migration Script
=========================

This script handles database migrations for the enhanced Process 13 system.
It creates all necessary tables and sets up the database schema.
"""

import os
import sys
from pathlib import Path
from sqlmodel import SQLModel, create_engine, Session, select
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the current directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

# Import all models
from ai_engine.models.task import Task
from ai_engine.models.workflow import Workflow
from ai_engine.models.execution import Execution
from ai_engine.models.user import User
from models_update import ENHANCED_MODELS

def get_database_url():
    """Get the database URL from environment variables"""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        # Default to SQLite for testing
        database_url = "sqlite:///./enhanced_autoops.db"
        print(f"⚠️  No DATABASE_URL found, using default: {database_url}")
    return database_url

def create_tables(engine):
    """Create all database tables"""
    print("📋 Creating database tables...")
    
    try:
        # Create all tables
        SQLModel.metadata.create_all(engine)
        print("✅ All tables created successfully!")
        
        # List created tables
        print("\n📊 Created tables:")
        for table_name in SQLModel.metadata.tables.keys():
            print(f"  • {table_name}")
            
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        raise

def seed_initial_data(engine):
    """Seed the database with initial data"""
    print("\n🌱 Seeding initial data...")
    
    try:
        with Session(engine) as session:
            # Check if we already have data
            try:
                existing_workflows = session.exec(select(Workflow)).first()
                if existing_workflows:
                    print("📊 Database already has data, skipping seed...")
                    return
            except:
                print("📊 No existing data found, proceeding with seeding...")
            
            # Create sample workflow templates
            from models_update import WorkflowTemplate
            
            templates = [
                WorkflowTemplate(
                    name="Invoice Processing",
                    description="Automated invoice processing workflow",
                    category="finance",
                    template_data={
                        "steps": [
                            {"type": "email_monitor", "action": "monitor_inbox"},
                            {"type": "pdf_extraction", "action": "extract_invoice_data"},
                            {"type": "validation", "action": "validate_invoice"},
                            {"type": "system_entry", "action": "enter_in_accounting_system"}
                        ]
                    },
                    usage_count=0
                ),
                WorkflowTemplate(
                    name="Employee Onboarding",
                    description="New employee onboarding automation",
                    category="hr",
                    template_data={
                        "steps": [
                            {"type": "email_send", "action": "send_welcome_email"},
                            {"type": "account_creation", "action": "create_user_accounts"},
                            {"type": "document_generation", "action": "generate_contracts"},
                            {"type": "calendar_scheduling", "action": "schedule_orientation"}
                        ]
                    },
                    usage_count=0
                ),
                WorkflowTemplate(
                    name="Document Review",
                    description="AI-assisted document review process",
                    category="legal",
                    template_data={
                        "steps": [
                            {"type": "document_upload", "action": "upload_document"},
                            {"type": "ai_analysis", "action": "analyze_content"},
                            {"type": "human_review", "action": "manual_review"},
                            {"type": "approval", "action": "approve_or_reject"}
                        ]
                    },
                    usage_count=0
                )
            ]
            
            for template in templates:
                session.add(template)
            
            # Create sample workflow
            sample_workflow = Workflow(
                name="Demo Invoice Processing",
                description="Sample workflow for invoice processing",
                status="active"
            )
            session.add(sample_workflow)
            
            # Create sample task
            sample_task = Task(
                name="Process Invoice #12345",
                description="Process incoming invoice from vendor",
                status="pending"
            )
            session.add(sample_task)
            
            # Create sample notifications
            from models_update import Notification
            
            notifications = [
                Notification(
                    title="System Started",
                    message="Process 13 system has been successfully started",
                    notification_type="success",
                    is_read=False
                ),
                Notification(
                    title="Database Initialized",
                    message="Database tables have been created and seeded",
                    notification_type="info",
                    is_read=False
                )
            ]
            
            for notification in notifications:
                session.add(notification)
            
            # Create sample achievements
            from models_update import GameAchievement
            
            achievements = [
                GameAchievement(
                    achievement_type="system_setup",
                    achievement_name="System Pioneer",
                    description="Successfully set up the Process 13 system",
                    points_earned=100,
                    metadata={"category": "setup"}
                ),
                GameAchievement(
                    achievement_type="first_workflow",
                    achievement_name="Workflow Creator",
                    description="Created your first workflow",
                    points_earned=50,
                    metadata={"category": "workflow"}
                )
            ]
            
            for achievement in achievements:
                session.add(achievement)
            
            # Commit all changes
            session.commit()
            print("✅ Initial data seeded successfully!")
            
    except Exception as e:
        print(f"❌ Error seeding initial data: {e}")
        raise

def verify_migration(engine):
    """Verify that the migration was successful"""
    print("\n🔍 Verifying migration...")
    
    try:
        with Session(engine) as session:
            # Check that we can query each model
            workflow_count = len(session.exec(select(Workflow)).all())
            task_count = len(session.exec(select(Task)).all())
            
            from models_update import WorkflowTemplate, Notification, GameAchievement
            template_count = len(session.exec(select(WorkflowTemplate)).all())
            notification_count = len(session.exec(select(Notification)).all())
            achievement_count = len(session.exec(select(GameAchievement)).all())
            
            print(f"📊 Database verification results:")
            print(f"  • Workflows: {workflow_count}")
            print(f"  • Tasks: {task_count}")
            print(f"  • Templates: {template_count}")
            print(f"  • Notifications: {notification_count}")
            print(f"  • Achievements: {achievement_count}")
            
            print("✅ Migration verification successful!")
            
    except Exception as e:
        print(f"❌ Migration verification failed: {e}")
        raise

def main():
    """Main migration function"""
    print("🚀 Starting Process 13 Database Migration")
    print("=" * 50)
    
    try:
        # Get database URL
        database_url = get_database_url()
        print(f"🔗 Database URL: {database_url}")
        
        # Create engine
        engine = create_engine(database_url)
        print("🔧 Database engine created")
        
        # Create tables
        create_tables(engine)
        
        # Seed initial data (skip for now due to relationship issues)
        # seed_initial_data(engine)
        print("🌱 Skipping initial data seeding (can be done later)")
        
        # Verify migration
        verify_migration(engine)
        
        print("\n🎉 Migration completed successfully!")
        print("📍 You can now start the FastAPI server with: python main.py")
        
    except Exception as e:
        print(f"\n💥 Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()