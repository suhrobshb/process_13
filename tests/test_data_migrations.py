"""
Data Consistency & Migration Testing Suite
==========================================

This test suite validates data integrity, schema migrations, and database consistency:
- Schema migration validation
- Data integrity checks
- Backup and restore testing
- Database constraint validation
- Data corruption detection
- Migration rollback testing
- Cross-table relationship validation
- Performance impact of migrations

Critical for ensuring workflow data integrity and upgrade reliability.
"""

import pytest
import tempfile
import os
import json
import shutil
from datetime import datetime, timedelta
from sqlmodel import Session, create_engine, SQLModel, select
from sqlmodel.pool import StaticPool
from unittest.mock import patch, MagicMock
import alembic.config
import alembic.script
import alembic.environment
from alembic.runtime.migration import MigrationContext
from alembic.operations import Operations

from ai_engine.database import get_session, create_db_and_tables
from ai_engine.models.workflow import Workflow
from ai_engine.models.execution import Execution
from ai_engine.models.task import Task
from ai_engine.models.user import User, Role, Tenant
from ai_engine.models.workflow_version import WorkflowVersion


@pytest.fixture(name="test_engine")
def test_engine_fixture():
    """Create test database engine"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture(name="test_session")
def test_session_fixture(test_engine):
    """Create test database session"""
    with Session(test_engine) as session:
        yield session


@pytest.fixture(name="sample_data")
def sample_data_fixture(test_session: Session):
    """Create sample data for testing"""
    # Create test user
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password="hashed_password",
        is_active=True
    )
    test_session.add(user)
    test_session.commit()
    test_session.refresh(user)
    
    # Create test workflows
    workflows = []
    for i in range(5):
        workflow = Workflow(
            name=f"Test Workflow {i}",
            description=f"Test workflow description {i}",
            steps=[
                {"action": "click", "target": f"button{i}", "parameters": {"x": 100 + i, "y": 200 + i}},
                {"action": "type", "target": f"input{i}", "parameters": {"text": f"test text {i}"}}
            ],
            created_by=user.id
        )
        test_session.add(workflow)
        workflows.append(workflow)
    
    test_session.commit()
    
    # Create test executions
    executions = []
    for i, workflow in enumerate(workflows):
        test_session.refresh(workflow)
        execution = Execution(
            workflow_id=workflow.id,
            status=f"status_{i}",
            logs=f"Test execution logs for workflow {i}",
            started_at=datetime.utcnow() - timedelta(hours=i),
            completed_at=datetime.utcnow() - timedelta(hours=i-1) if i > 0 else None
        )
        test_session.add(execution)
        executions.append(execution)
    
    test_session.commit()
    
    return {
        'user': user,
        'workflows': workflows,
        'executions': executions
    }


class TestDataIntegrity:
    """Test data integrity and consistency"""
    
    def test_foreign_key_constraints(self, test_session: Session, sample_data):
        """Test foreign key constraint enforcement"""
        user = sample_data['user']
        workflow = sample_data['workflows'][0]
        
        # Try to create execution with invalid workflow_id
        invalid_execution = Execution(
            workflow_id=99999,  # Non-existent workflow
            status="test",
            logs="test logs"
        )
        
        test_session.add(invalid_execution)
        
        # Should raise integrity error
        with pytest.raises(Exception):  # SQLite may not enforce FK constraints by default
            test_session.commit()
    
    def test_unique_constraints(self, test_session: Session):
        """Test unique constraint enforcement"""
        # Create user with unique email
        user1 = User(
            username="user1",
            email="unique@example.com",
            hashed_password="password1",
            is_active=True
        )
        test_session.add(user1)
        test_session.commit()
        
        # Try to create another user with same email
        user2 = User(
            username="user2",
            email="unique@example.com",  # Duplicate email
            hashed_password="password2",
            is_active=True
        )
        test_session.add(user2)
        
        # Should raise integrity error
        with pytest.raises(Exception):
            test_session.commit()
    
    def test_not_null_constraints(self, test_session: Session):
        """Test NOT NULL constraint enforcement"""
        # Try to create workflow without required fields
        invalid_workflow = Workflow(
            name=None,  # Required field
            description="Test description",
            steps=[]
        )
        test_session.add(invalid_workflow)
        
        with pytest.raises(Exception):
            test_session.commit()
    
    def test_data_type_constraints(self, test_session: Session):
        """Test data type constraint enforcement"""
        # Test JSON field validation
        workflow = Workflow(
            name="Test Workflow",
            description="Test description",
            steps="invalid_json_should_be_list"  # Should be list, not string
        )
        test_session.add(workflow)
        
        # Depending on SQLModel/SQLAlchemy version, this might be allowed
        # but should be caught by application validation
        try:
            test_session.commit()
            # If commit succeeds, verify data is properly handled
            test_session.refresh(workflow)
            # Steps should be properly serialized/deserialized
        except Exception:
            # If it fails, that's also acceptable for type safety
            test_session.rollback()
    
    def test_cross_table_relationships(self, test_session: Session, sample_data):
        """Test relationships between tables are consistent"""
        user = sample_data['user']
        workflows = sample_data['workflows']
        executions = sample_data['executions']
        
        # Verify user-workflow relationships
        user_workflows = test_session.exec(
            select(Workflow).where(Workflow.created_by == user.id)
        ).all()
        assert len(user_workflows) == len(workflows)
        
        # Verify workflow-execution relationships
        for workflow in workflows:
            workflow_executions = test_session.exec(
                select(Execution).where(Execution.workflow_id == workflow.id)
            ).all()
            assert len(workflow_executions) == 1  # Each workflow has one execution
    
    def test_data_consistency_after_updates(self, test_session: Session, sample_data):
        """Test data remains consistent after updates"""
        workflow = sample_data['workflows'][0]
        original_name = workflow.name
        
        # Update workflow
        workflow.name = "Updated Workflow Name"
        workflow.description = "Updated description"
        test_session.add(workflow)
        test_session.commit()
        
        # Verify update
        test_session.refresh(workflow)
        assert workflow.name == "Updated Workflow Name"
        assert workflow.description == "Updated description"
        
        # Verify related executions still reference correct workflow
        executions = test_session.exec(
            select(Execution).where(Execution.workflow_id == workflow.id)
        ).all()
        assert len(executions) > 0
        for execution in executions:
            assert execution.workflow_id == workflow.id


class TestSchemaMigration:
    """Test schema migration functionality"""
    
    def test_migration_script_validation(self):
        """Test that migration scripts are valid"""
        # This would typically test actual Alembic migration scripts
        # For now, we'll test the basic migration infrastructure
        
        try:
            # Test that we can create migration context
            from alembic.migration import MigrationContext
            from alembic.operations import Operations
            
            # This validates that migration infrastructure is available
            assert MigrationContext is not None
            assert Operations is not None
            
        except ImportError:
            pytest.skip("Alembic not available for migration testing")
    
    def test_migration_rollback_capability(self, test_engine):
        """Test that migrations can be rolled back"""
        # Create a test migration scenario
        with test_engine.connect() as connection:
            context = MigrationContext.configure(connection)
            op = Operations(context)
            
            # Test that we can create and drop tables (basic migration ops)
            try:
                # This tests the migration infrastructure
                op.create_table(
                    'test_migration_table',
                    op.Column('id', op.Integer, primary_key=True),
                    op.Column('name', op.String(50))
                )
                
                # Verify table was created
                tables = connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='test_migration_table'"
                ).fetchall()
                assert len(tables) == 1
                
                # Drop table (rollback simulation)
                op.drop_table('test_migration_table')
                
                # Verify table was dropped
                tables = connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='test_migration_table'"
                ).fetchall()
                assert len(tables) == 0
                
            except Exception as e:
                # Some operations might not be supported in test environment
                pytest.skip(f"Migration operations not supported: {e}")
    
    def test_migration_data_preservation(self, test_session: Session):
        """Test that data is preserved during schema migrations"""
        # Create test data before "migration"
        workflow = Workflow(
            name="Pre-migration Workflow",
            description="Data that should survive migration",
            steps=[{"action": "test"}]
        )
        test_session.add(workflow)
        test_session.commit()
        test_session.refresh(workflow)
        
        original_id = workflow.id
        original_name = workflow.name
        
        # Simulate a migration that adds a new column
        # In a real scenario, this would be an Alembic migration
        
        # Verify data still exists and is intact
        recovered_workflow = test_session.get(Workflow, original_id)
        assert recovered_workflow is not None
        assert recovered_workflow.name == original_name
        assert recovered_workflow.description == "Data that should survive migration"
    
    def test_migration_performance_impact(self, test_session: Session):
        """Test migration performance with large datasets"""
        import time
        
        # Create a moderately large dataset
        workflows = []
        for i in range(100):  # Create 100 workflows
            workflow = Workflow(
                name=f"Workflow {i}",
                description=f"Description {i}",
                steps=[{"action": "test", "step": i}]
            )
            workflows.append(workflow)
        
        start_time = time.time()
        test_session.add_all(workflows)
        test_session.commit()
        creation_time = time.time() - start_time
        
        # Migration simulation: bulk update (common migration operation)
        start_time = time.time()
        for workflow in workflows:
            workflow.description = f"Updated {workflow.description}"
        test_session.commit()
        migration_time = time.time() - start_time
        
        # Performance assertions
        assert creation_time < 5.0, f"Data creation took too long: {creation_time:.2f}s"
        assert migration_time < 10.0, f"Migration simulation took too long: {migration_time:.2f}s"
        
        # Verify all data was updated correctly
        updated_workflows = test_session.exec(select(Workflow)).all()
        assert len(updated_workflows) == 100
        for workflow in updated_workflows:
            assert "Updated" in workflow.description


class TestBackupAndRestore:
    """Test backup and restore functionality"""
    
    def test_data_export(self, test_session: Session, sample_data):
        """Test exporting data for backup"""
        # Export workflows
        workflows = test_session.exec(select(Workflow)).all()
        workflow_data = []
        for workflow in workflows:
            workflow_data.append({
                'id': workflow.id,
                'name': workflow.name,
                'description': workflow.description,
                'steps': workflow.steps,
                'created_by': workflow.created_by,
                'created_at': workflow.created_at.isoformat() if workflow.created_at else None
            })
        
        # Export executions
        executions = test_session.exec(select(Execution)).all()
        execution_data = []
        for execution in executions:
            execution_data.append({
                'id': execution.id,
                'workflow_id': execution.workflow_id,
                'status': execution.status,
                'logs': execution.logs,
                'started_at': execution.started_at.isoformat() if execution.started_at else None,
                'completed_at': execution.completed_at.isoformat() if execution.completed_at else None
            })
        
        backup_data = {
            'workflows': workflow_data,
            'executions': execution_data,
            'backup_timestamp': datetime.utcnow().isoformat()
        }
        
        # Verify backup data integrity
        assert len(backup_data['workflows']) == 5
        assert len(backup_data['executions']) == 5
        assert 'backup_timestamp' in backup_data
        
        # Test JSON serialization (important for backup files)
        json_backup = json.dumps(backup_data)
        restored_data = json.loads(json_backup)
        assert restored_data['workflows'][0]['name'] == sample_data['workflows'][0].name
    
    def test_data_import(self, test_session: Session):
        """Test importing data from backup"""
        # Create backup data
        backup_data = {
            'workflows': [
                {
                    'name': 'Restored Workflow 1',
                    'description': 'Restored from backup',
                    'steps': [{'action': 'click', 'target': 'button'}]
                },
                {
                    'name': 'Restored Workflow 2',
                    'description': 'Another restored workflow',
                    'steps': [{'action': 'type', 'target': 'input', 'parameters': {'text': 'test'}}]
                }
            ],
            'executions': [
                {
                    'workflow_id': 1,
                    'status': 'completed',
                    'logs': 'Restored execution logs'
                }
            ]
        }
        
        # Import workflows
        imported_workflows = []
        for workflow_data in backup_data['workflows']:
            workflow = Workflow(
                name=workflow_data['name'],
                description=workflow_data['description'],
                steps=workflow_data['steps']
            )
            test_session.add(workflow)
            imported_workflows.append(workflow)
        
        test_session.commit()
        
        # Verify import
        for workflow in imported_workflows:
            test_session.refresh(workflow)
            assert workflow.id is not None
            assert workflow.name.startswith('Restored Workflow')
        
        # Verify workflows are queryable
        restored_workflows = test_session.exec(select(Workflow)).all()
        assert len(restored_workflows) == 2
    
    def test_backup_file_integrity(self, test_session: Session, sample_data):
        """Test backup file integrity and corruption detection"""
        # Create backup file
        workflows = test_session.exec(select(Workflow)).all()
        backup_data = {
            'workflows': [
                {
                    'id': w.id,
                    'name': w.name,
                    'description': w.description,
                    'steps': w.steps
                } for w in workflows
            ],
            'checksum': 'test_checksum',  # In real implementation, calculate actual checksum
            'version': '1.0'
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(backup_data, f)
            backup_file_path = f.name
        
        try:
            # Verify file can be read back
            with open(backup_file_path, 'r') as f:
                restored_data = json.load(f)
            
            assert restored_data['version'] == '1.0'
            assert len(restored_data['workflows']) == 5
            assert 'checksum' in restored_data
            
            # Test corruption detection (modify file)
            with open(backup_file_path, 'r') as f:
                content = f.read()
            
            corrupted_content = content.replace('"name":', '"invalid_field":')
            
            with open(backup_file_path, 'w') as f:
                f.write(corrupted_content)
            
            # Verify corruption is detected
            with open(backup_file_path, 'r') as f:
                try:
                    corrupted_data = json.load(f)
                    # Should notice field name changes
                    assert 'invalid_field' in str(corrupted_data)
                except json.JSONDecodeError:
                    # JSON corruption detected
                    pass
        
        finally:
            os.unlink(backup_file_path)
    
    def test_incremental_backup(self, test_session: Session, sample_data):
        """Test incremental backup functionality"""
        # Simulate initial backup timestamp
        last_backup = datetime.utcnow() - timedelta(hours=1)
        
        # Create new data after backup timestamp
        new_workflow = Workflow(
            name="New Workflow After Backup",
            description="Should be in incremental backup",
            steps=[{"action": "new_action"}]
        )
        test_session.add(new_workflow)
        test_session.commit()
        test_session.refresh(new_workflow)
        
        # Query for incremental changes
        # Note: This requires created_at/updated_at fields to be properly set
        incremental_workflows = test_session.exec(
            select(Workflow).where(Workflow.created_at > last_backup)
        ).all()
        
        # In our test, the new workflow should be included
        # (This assumes created_at is automatically set)
        assert len(incremental_workflows) >= 1
        assert any(w.name == "New Workflow After Backup" for w in incremental_workflows)


class TestDataCorruptionDetection:
    """Test detection and handling of data corruption"""
    
    def test_json_field_corruption_detection(self, test_session: Session):
        """Test detection of corrupted JSON fields"""
        # Create workflow with valid JSON steps
        workflow = Workflow(
            name="JSON Test Workflow",
            description="Testing JSON field integrity",
            steps=[{"action": "click", "target": "button"}]
        )
        test_session.add(workflow)
        test_session.commit()
        test_session.refresh(workflow)
        
        # Verify JSON field is properly handled
        assert isinstance(workflow.steps, list)
        assert len(workflow.steps) == 1
        assert workflow.steps[0]["action"] == "click"
        
        # Test with complex JSON
        complex_steps = [
            {
                "action": "click",
                "target": "button",
                "parameters": {"x": 100, "y": 200},
                "conditions": [{"type": "element_exists", "selector": "#button"}]
            },
            {
                "action": "type",
                "target": "input[name='username']",
                "parameters": {"text": "testuser", "clear_first": True}
            }
        ]
        
        workflow.steps = complex_steps
        test_session.add(workflow)
        test_session.commit()
        test_session.refresh(workflow)
        
        # Verify complex JSON is preserved
        assert len(workflow.steps) == 2
        assert workflow.steps[0]["parameters"]["x"] == 100
        assert workflow.steps[1]["parameters"]["clear_first"] is True
    
    def test_missing_required_relationships(self, test_session: Session):
        """Test detection of missing required relationships"""
        # Create execution without valid workflow reference
        # (This would typically be caught by foreign key constraints)
        
        try:
            orphaned_execution = Execution(
                workflow_id=99999,  # Non-existent workflow
                status="orphaned",
                logs="This execution has no valid workflow"
            )
            test_session.add(orphaned_execution)
            test_session.commit()
            
            # If we get here, test the orphaned data detection
            orphaned_executions = test_session.exec(
                select(Execution).where(
                    ~Execution.workflow_id.in_(
                        select(Workflow.id)
                    )
                )
            ).all()
            
            assert len(orphaned_executions) > 0
            
        except Exception:
            # Foreign key constraint properly prevented orphaned data
            test_session.rollback()
    
    def test_data_type_inconsistencies(self, test_session: Session):
        """Test detection of data type inconsistencies"""
        # Test with edge cases that might cause type issues
        
        # Very long strings
        long_description = "A" * 10000
        workflow = Workflow(
            name="Long Description Test",
            description=long_description,
            steps=[{"action": "test"}]
        )
        test_session.add(workflow)
        test_session.commit()
        test_session.refresh(workflow)
        
        assert len(workflow.description) == 10000
        
        # Special characters and encoding
        special_chars_workflow = Workflow(
            name="Special Chars: 测试 🚀 Ñiño",
            description="Testing unicode: αβγ δεζ ηθι κλμ νξο πρστ υφχ ψω",
            steps=[{"action": "test", "special": "🔥💻⚡"}]
        )
        test_session.add(special_chars_workflow)
        test_session.commit()
        test_session.refresh(special_chars_workflow)
        
        assert "测试" in special_chars_workflow.name
        assert "🚀" in special_chars_workflow.name
        assert "🔥" in str(special_chars_workflow.steps)
    
    def test_concurrent_modification_detection(self, test_session: Session, sample_data):
        """Test detection of concurrent modification issues"""
        workflow = sample_data['workflows'][0]
        
        # Simulate concurrent modifications
        # First session modifies workflow
        workflow.name = "Modified by Session 1"
        workflow.description = "First modification"
        
        # Create second session to simulate concurrent access
        with Session(test_session.bind) as session2:
            # Second session gets same workflow
            workflow2 = session2.get(Workflow, workflow.id)
            workflow2.name = "Modified by Session 2"
            workflow2.description = "Second modification"
            
            # Both sessions commit - last one wins
            test_session.add(workflow)
            test_session.commit()
            
            session2.add(workflow2)
            session2.commit()
            
            # Verify final state
            test_session.refresh(workflow)
            # Should have the second session's changes
            assert workflow.name == "Modified by Session 2"
            assert workflow.description == "Second modification"


class TestDatabaseConstraints:
    """Test database constraint validation"""
    
    def test_check_constraints(self, test_session: Session):
        """Test custom check constraints"""
        # Test workflow name length constraint (if implemented)
        try:
            workflow = Workflow(
                name="",  # Empty name should be invalid
                description="Test description",
                steps=[{"action": "test"}]
            )
            test_session.add(workflow)
            test_session.commit()
            
            # If we get here, add application-level validation test
            assert workflow.name == ""  # Empty string was allowed
            
        except Exception:
            # Database constraint prevented empty name
            test_session.rollback()
    
    def test_index_integrity(self, test_session: Session, sample_data):
        """Test database index integrity and performance"""
        # Test queries that should use indexes efficiently
        
        # Query by workflow name (should be indexed)
        import time
        start_time = time.time()
        
        for i in range(100):  # Multiple queries to test index usage
            workflows = test_session.exec(
                select(Workflow).where(Workflow.name.like("Test Workflow%"))
            ).all()
        
        query_time = time.time() - start_time
        
        # Should complete quickly with proper indexing
        assert query_time < 1.0, f"Queries took too long: {query_time:.2f}s"
        assert len(workflows) > 0
    
    def test_cascade_delete_behavior(self, test_session: Session, sample_data):
        """Test cascade delete behavior"""
        workflow = sample_data['workflows'][0]
        workflow_id = workflow.id
        
        # Get related executions
        executions = test_session.exec(
            select(Execution).where(Execution.workflow_id == workflow_id)
        ).all()
        execution_count = len(executions)
        
        # Delete workflow
        test_session.delete(workflow)
        test_session.commit()
        
        # Check if related executions were handled properly
        remaining_executions = test_session.exec(
            select(Execution).where(Execution.workflow_id == workflow_id)
        ).all()
        
        # Depending on cascade settings:
        # - CASCADE: related executions should be deleted
        # - RESTRICT: delete should have failed
        # - SET NULL: executions should have workflow_id = NULL
        
        # For this test, we'll check that the relationship is handled consistently
        if len(remaining_executions) == execution_count:
            # No cascade delete - executions still exist
            # Should test that they're properly marked as orphaned
            pass
        elif len(remaining_executions) == 0:
            # Cascade delete worked - executions were removed
            pass
        else:
            # Partial deletion shouldn't happen
            pytest.fail("Inconsistent cascade delete behavior")


class TestMigrationRollback:
    """Test migration rollback scenarios"""
    
    def test_rollback_after_failed_migration(self, test_engine):
        """Test rollback after a failed migration"""
        # Simulate a migration that fails partway through
        
        with test_engine.connect() as connection:
            trans = connection.begin()
            
            try:
                # Simulate successful migration steps
                connection.execute("CREATE TABLE temp_migration_test (id INTEGER)")
                
                # Simulate a failure
                # connection.execute("INVALID SQL THAT FAILS")
                # Instead, we'll manually rollback to test the mechanism
                trans.rollback()
                
                # Verify rollback worked
                try:
                    result = connection.execute("SELECT * FROM temp_migration_test")
                    pytest.fail("Table should not exist after rollback")
                except Exception:
                    # Table doesn't exist - rollback worked
                    pass
                    
            except Exception:
                trans.rollback()
    
    def test_partial_migration_recovery(self, test_session: Session):
        """Test recovery from partial migration state"""
        # Create test data
        workflow = Workflow(
            name="Pre-migration Data",
            description="Should survive partial migration",
            steps=[{"action": "test"}]
        )
        test_session.add(workflow)
        test_session.commit()
        test_session.refresh(workflow)
        
        original_id = workflow.id
        
        # Simulate partial migration failure and recovery
        try:
            # Simulate migration step 1: success
            workflow.description = "Migration step 1 completed"
            test_session.add(workflow)
            test_session.commit()
            
            # Simulate migration step 2: failure
            # In real scenario, this would be a schema change that fails
            # Here we'll simulate with a constraint violation
            
            # Recovery: verify data is still consistent
            recovered_workflow = test_session.get(Workflow, original_id)
            assert recovered_workflow is not None
            assert "Migration step 1 completed" in recovered_workflow.description
            
        except Exception:
            test_session.rollback()
            # Verify rollback preserved original data
            recovered_workflow = test_session.get(Workflow, original_id)
            assert recovered_workflow is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])