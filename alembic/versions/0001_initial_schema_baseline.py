"""Initial schema baseline

Revision ID: 0001
Revises: 
Create Date: 2024-07-10 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    """Create all tables for the AI Engine platform."""
    
    # Users table
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('full_name', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_admin', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.Column('preferences', sa.JSON(), nullable=True),
        sa.Column('api_key', sa.String(), nullable=True),
        sa.Column('rate_limit_count', sa.Integer(), nullable=False, default=0),
        sa.Column('rate_limit_window', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('api_key')
    )
    
    # Workflows table
    op.create_table('workflows',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, default=1),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('steps', sa.JSON(), nullable=True),
        sa.Column('nodes', sa.JSON(), nullable=True),
        sa.Column('edges', sa.JSON(), nullable=True),
        sa.Column('config', sa.JSON(), nullable=True),
        sa.Column('schedule', sa.String(), nullable=True),
        sa.Column('timeout_seconds', sa.Integer(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, default=0),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Workflow Versions table
    op.create_table('workflow_versions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('workflow_id', sa.Integer(), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('changes_summary', sa.String(), nullable=True),
        sa.Column('workflow_data', sa.JSON(), nullable=False),
        sa.Column('is_published', sa.Boolean(), nullable=False, default=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflows.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('workflow_id', 'version_number')
    )
    
    # Tasks table
    op.create_table('tasks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('workflow_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('task_type', sa.String(), nullable=False),
        sa.Column('config', sa.JSON(), nullable=True),
        sa.Column('order', sa.Integer(), nullable=False),
        sa.Column('dependencies', sa.JSON(), nullable=True),
        sa.Column('conditions', sa.JSON(), nullable=True),
        sa.Column('retry_policy', sa.JSON(), nullable=True),
        sa.Column('timeout_seconds', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflows.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Executions table
    op.create_table('executions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('workflow_id', sa.Integer(), nullable=False),
        sa.Column('triggered_by', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('result', sa.JSON(), nullable=True),
        sa.Column('error', sa.String(), nullable=True),
        sa.Column('execution_context', sa.JSON(), nullable=True),
        sa.Column('metrics', sa.JSON(), nullable=True),
        sa.Column('logs', sa.JSON(), nullable=True),
        sa.Column('trigger_type', sa.String(), nullable=True),
        sa.Column('trigger_data', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['triggered_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflows.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for better performance
    op.create_index('idx_workflows_created_by', 'workflows', ['created_by'])
    op.create_index('idx_workflows_is_active', 'workflows', ['is_active'])
    op.create_index('idx_workflows_category', 'workflows', ['category'])
    op.create_index('idx_executions_workflow_id', 'executions', ['workflow_id'])
    op.create_index('idx_executions_status', 'executions', ['status'])
    op.create_index('idx_executions_started_at', 'executions', ['started_at'])
    op.create_index('idx_tasks_workflow_id', 'tasks', ['workflow_id'])
    op.create_index('idx_tasks_order', 'tasks', ['order'])
    op.create_index('idx_users_email', 'users', ['email'])
    op.create_index('idx_users_is_active', 'users', ['is_active'])


def downgrade():
    """Drop all tables."""
    op.drop_index('idx_users_is_active', table_name='users')
    op.drop_index('idx_users_email', table_name='users')
    op.drop_index('idx_tasks_order', table_name='tasks')
    op.drop_index('idx_tasks_workflow_id', table_name='tasks')
    op.drop_index('idx_executions_started_at', table_name='executions')
    op.drop_index('idx_executions_status', table_name='executions')
    op.drop_index('idx_executions_workflow_id', table_name='executions')
    op.drop_index('idx_workflows_category', table_name='workflows')
    op.drop_index('idx_workflows_is_active', table_name='workflows')
    op.drop_index('idx_workflows_created_by', table_name='workflows')
    
    op.drop_table('executions')
    op.drop_table('tasks')
    op.drop_table('workflow_versions')
    op.drop_table('workflows')
    op.drop_table('users')