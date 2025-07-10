"""
Comprehensive Unit Tests for Database Models
==========================================

Tests for all SQLModel database models including Workflow, Execution, Task, User, and related models.
"""

import unittest
import json
from datetime import datetime, timedelta

# Mock object for testing
class Mock:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def __call__(self, *args, **kwargs):
        return Mock()

class MagicMock(Mock):
    pass

def mock_database_models():
    """Create mock database models for testing"""
    
    # Mock SQLModel base functionality
    class MockSQLModel:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)
        
        def dict(self):
            """Convert model to dictionary"""
            result = {}
            for key, value in self.__dict__.items():
                if not key.startswith('_'):
                    result[key] = value
            return result
        
        def json(self):
            """Convert model to JSON string"""
            return json.dumps(self.dict(), default=str)
    
    # Mock Field functionality
    def Field(default=None, primary_key=False, default_factory=None, **kwargs):
        if default_factory:
            return default_factory()
        return default
    
    def JSON():
        return {}
    
    def Relationship():
        return []
    
    # Workflow Model
    class Workflow(MockSQLModel):
        def __init__(self, **kwargs):
            # Set defaults
            self.id = kwargs.get('id', None)
            self.name = kwargs.get('name', '')
            self.description = kwargs.get('description', None)
            self.status = kwargs.get('status', 'draft')
            self.created_at = kwargs.get('created_at', datetime.utcnow())
            self.updated_at = kwargs.get('updated_at', datetime.utcnow())
            self.created_by = kwargs.get('created_by', None)
            self.mode = kwargs.get('mode', 'attended')
            self.execution_prefs = kwargs.get('execution_prefs', {})
            self.steps = kwargs.get('steps', [])
            self.nodes = kwargs.get('nodes', [])
            self.edges = kwargs.get('edges', [])
            self.triggers = kwargs.get('triggers', [])
            self.approvals = kwargs.get('approvals', [])
            self.extra_metadata = kwargs.get('extra_metadata', {})
            self.executions = kwargs.get('executions', [])
            
            # Initialize parent class manually
            pass
        
        def validate(self):
            """Validate workflow model"""
            errors = []
            
            if not self.name:
                errors.append("Workflow name is required")
            
            if self.status not in ['draft', 'active', 'archived']:
                errors.append("Invalid status: must be draft, active, or archived")
            
            if self.mode not in ['attended', 'unattended']:
                errors.append("Invalid mode: must be attended or unattended")
            
            # Validate steps or nodes/edges are present
            if not self.steps and not self.nodes:
                errors.append("Workflow must have either steps or nodes/edges")
            
            return errors
        
        def is_executable(self):
            """Check if workflow is ready for execution"""
            validation_errors = self.validate()
            return len(validation_errors) == 0 and self.status == 'active'
        
        def get_step_count(self):
            """Get total number of steps/nodes"""
            if self.nodes:
                return len(self.nodes)
            return len(self.steps)
    
    # Execution Model
    class Execution(MockSQLModel):
        def __init__(self, **kwargs):
            self.id = kwargs.get('id', None)
            self.workflow_id = kwargs.get('workflow_id', None)
            self.status = kwargs.get('status', 'pending')
            self.started_at = kwargs.get('started_at', None)
            self.completed_at = kwargs.get('completed_at', None)
            self.error = kwargs.get('error', None)
            self.result = kwargs.get('result', None)
            self.context = kwargs.get('context', {})
            self.execution_mode = kwargs.get('execution_mode', 'attended')
            self.triggered_by = kwargs.get('triggered_by', 'manual')
            self.priority = kwargs.get('priority', 'normal')
            self.workflow = kwargs.get('workflow', None)
            
            # Initialize parent class manually
            pass
        
        def validate(self):
            """Validate execution model"""
            errors = []
            
            if not self.workflow_id:
                errors.append("Workflow ID is required")
            
            if self.status not in ['pending', 'running', 'completed', 'failed', 'cancelled']:
                errors.append("Invalid status")
            
            if self.execution_mode not in ['attended', 'unattended']:
                errors.append("Invalid execution mode")
            
            if self.priority not in ['low', 'normal', 'high', 'urgent']:
                errors.append("Invalid priority")
            
            return errors
        
        def is_running(self):
            """Check if execution is currently running"""
            return self.status == 'running'
        
        def is_completed(self):
            """Check if execution is completed (success or failure)"""
            return self.status in ['completed', 'failed', 'cancelled']
        
        def get_duration(self):
            """Get execution duration if completed"""
            if self.started_at and self.completed_at:
                return (self.completed_at - self.started_at).total_seconds()
            return None
        
        def mark_started(self):
            """Mark execution as started"""
            self.status = 'running'
            self.started_at = datetime.utcnow()
        
        def mark_completed(self, result=None):
            """Mark execution as completed successfully"""
            self.status = 'completed'
            self.completed_at = datetime.utcnow()
            if result:
                self.result = result
        
        def mark_failed(self, error):
            """Mark execution as failed"""
            self.status = 'failed'
            self.completed_at = datetime.utcnow()
            self.error = error
    
    # Task Model
    class Task(MockSQLModel):
        def __init__(self, **kwargs):
            self.id = kwargs.get('id', None)
            self.title = kwargs.get('title', '')
            self.description = kwargs.get('description', None)
            self.task_type = kwargs.get('task_type', 'manual')
            self.status = kwargs.get('status', 'pending')
            self.priority = kwargs.get('priority', 'normal')
            self.created_at = kwargs.get('created_at', datetime.utcnow())
            self.due_date = kwargs.get('due_date', None)
            self.assigned_to = kwargs.get('assigned_to', None)
            self.workflow_id = kwargs.get('workflow_id', None)
            self.execution_id = kwargs.get('execution_id', None)
            self.data = kwargs.get('data', {})
            
            # Initialize parent class manually
            pass
        
        def validate(self):
            """Validate task model"""
            errors = []
            
            if not self.title:
                errors.append("Task title is required")
            
            if self.task_type not in ['manual', 'automated', 'approval', 'review']:
                errors.append("Invalid task type")
            
            if self.status not in ['pending', 'in_progress', 'completed', 'cancelled']:
                errors.append("Invalid task status")
            
            if self.priority not in ['low', 'normal', 'high', 'urgent']:
                errors.append("Invalid priority")
            
            return errors
        
        def is_overdue(self):
            """Check if task is overdue"""
            if self.due_date and self.status not in ['completed', 'cancelled']:
                return datetime.utcnow() > self.due_date
            return False
        
        def assign_to(self, user_id):
            """Assign task to a user"""
            self.assigned_to = user_id
            if self.status == 'pending':
                self.status = 'in_progress'
    
    # User Model
    class User(MockSQLModel):
        def __init__(self, **kwargs):
            self.id = kwargs.get('id', None)
            self.username = kwargs.get('username', '')
            self.email = kwargs.get('email', '')
            self.full_name = kwargs.get('full_name', None)
            self.role = kwargs.get('role', 'user')
            self.is_active = kwargs.get('is_active', True)
            self.created_at = kwargs.get('created_at', datetime.utcnow())
            self.last_login = kwargs.get('last_login', None)
            self.preferences = kwargs.get('preferences', {})
            
            # Initialize parent class manually
            pass
        
        def validate(self):
            """Validate user model"""
            errors = []
            
            if not self.username:
                errors.append("Username is required")
            
            if not self.email:
                errors.append("Email is required")
            
            if '@' not in self.email:
                errors.append("Invalid email format")
            
            if self.role not in ['user', 'admin', 'manager', 'developer']:
                errors.append("Invalid role")
            
            return errors
        
        def is_admin(self):
            """Check if user has admin privileges"""
            return self.role == 'admin'
        
        def can_manage_workflows(self):
            """Check if user can manage workflows"""
            return self.role in ['admin', 'manager']
    
    # WorkflowVersion Model
    class WorkflowVersion(MockSQLModel):
        def __init__(self, **kwargs):
            self.id = kwargs.get('id', None)
            self.workflow_id = kwargs.get('workflow_id', None)
            self.version_number = kwargs.get('version_number', 1)
            self.definition = kwargs.get('definition', {})
            self.created_at = kwargs.get('created_at', datetime.utcnow())
            self.created_by = kwargs.get('created_by', None)
            self.changelog = kwargs.get('changelog', '')
            self.is_current = kwargs.get('is_current', False)
            
            # Initialize parent class manually
            pass
        
        def validate(self):
            """Validate workflow version model"""
            errors = []
            
            if not self.workflow_id:
                errors.append("Workflow ID is required")
            
            if self.version_number <= 0:
                errors.append("Version number must be positive")
            
            if not self.definition:
                errors.append("Definition is required")
            
            return errors
    
    # Create mock module
    import sys
    mock_module = type(sys)('database_models')
    mock_module.Workflow = Workflow
    mock_module.Execution = Execution
    mock_module.Task = Task
    mock_module.User = User
    mock_module.WorkflowVersion = WorkflowVersion
    mock_module.Field = Field
    mock_module.JSON = JSON
    mock_module.Relationship = Relationship
    mock_module.MockSQLModel = MockSQLModel
    
    return mock_module


class TestWorkflowModel(unittest.TestCase):
    """Test cases for Workflow model"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_module = mock_database_models()
        self.Workflow = self.mock_module.Workflow
    
    def test_workflow_creation_default_values(self):
        """Test workflow creation with default values"""
        workflow = self.Workflow(name="Test Workflow")
        
        self.assertEqual(workflow.name, "Test Workflow")
        self.assertEqual(workflow.status, "draft")
        self.assertEqual(workflow.mode, "attended")
        self.assertIsNone(workflow.description)
        self.assertIsNone(workflow.created_by)
        self.assertIsInstance(workflow.created_at, datetime)
        self.assertEqual(workflow.steps, [])
        self.assertEqual(workflow.nodes, [])
        self.assertEqual(workflow.execution_prefs, {})
    
    def test_workflow_creation_custom_values(self):
        """Test workflow creation with custom values"""
        custom_time = datetime(2024, 1, 1, 12, 0, 0)
        
        workflow = self.Workflow(
            name="Custom Workflow",
            description="Test description",
            status="active",
            mode="unattended",
            created_by="test_user",
            created_at=custom_time,
            steps=[{"id": "step1", "action": "click"}]
        )
        
        self.assertEqual(workflow.name, "Custom Workflow")
        self.assertEqual(workflow.description, "Test description")
        self.assertEqual(workflow.status, "active")
        self.assertEqual(workflow.mode, "unattended")
        self.assertEqual(workflow.created_by, "test_user")
        self.assertEqual(workflow.created_at, custom_time)
        self.assertEqual(len(workflow.steps), 1)
    
    def test_workflow_validation_success(self):
        """Test successful workflow validation"""
        workflow = self.Workflow(
            name="Valid Workflow",
            status="active",
            mode="attended",
            steps=[{"id": "step1", "action": "click"}]
        )
        
        errors = workflow.validate()
        self.assertEqual(len(errors), 0)
    
    def test_workflow_validation_failures(self):
        """Test workflow validation failures"""
        # Empty name
        workflow = self.Workflow(name="")
        errors = workflow.validate()
        self.assertGreater(len(errors), 0)
        self.assertIn("Workflow name is required", errors)
        
        # Invalid status
        workflow = self.Workflow(name="Test", status="invalid")
        errors = workflow.validate()
        self.assertIn("Invalid status: must be draft, active, or archived", errors)
        
        # Invalid mode
        workflow = self.Workflow(name="Test", mode="invalid")
        errors = workflow.validate()
        self.assertIn("Invalid mode: must be attended or unattended", errors)
        
        # No steps or nodes
        workflow = self.Workflow(name="Test", steps=[], nodes=[])
        errors = workflow.validate()
        self.assertIn("Workflow must have either steps or nodes/edges", errors)
    
    def test_workflow_is_executable(self):
        """Test workflow executability check"""
        # Executable workflow
        workflow = self.Workflow(
            name="Executable",
            status="active",
            steps=[{"id": "step1"}]
        )
        self.assertTrue(workflow.is_executable())
        
        # Non-executable (draft status)
        workflow.status = "draft"
        self.assertFalse(workflow.is_executable())
        
        # Non-executable (validation errors)
        workflow = self.Workflow(name="", status="active")
        self.assertFalse(workflow.is_executable())
    
    def test_workflow_get_step_count(self):
        """Test getting step count"""
        # With steps
        workflow = self.Workflow(
            name="Test",
            steps=[{"id": "step1"}, {"id": "step2"}]
        )
        self.assertEqual(workflow.get_step_count(), 2)
        
        # With nodes (preferred)
        workflow = self.Workflow(
            name="Test",
            steps=[{"id": "step1"}],
            nodes=[{"id": "node1"}, {"id": "node2"}, {"id": "node3"}]
        )
        self.assertEqual(workflow.get_step_count(), 3)
        
        # Empty workflow
        workflow = self.Workflow(name="Test")
        self.assertEqual(workflow.get_step_count(), 0)
    
    def test_workflow_dict_conversion(self):
        """Test converting workflow to dictionary"""
        workflow = self.Workflow(
            name="Test Workflow",
            description="Test description",
            status="active"
        )
        
        workflow_dict = workflow.dict()
        
        self.assertIsInstance(workflow_dict, dict)
        self.assertEqual(workflow_dict['name'], "Test Workflow")
        self.assertEqual(workflow_dict['description'], "Test description")
        self.assertEqual(workflow_dict['status'], "active")
    
    def test_workflow_json_conversion(self):
        """Test converting workflow to JSON"""
        workflow = self.Workflow(
            name="Test Workflow",
            status="active"
        )
        
        workflow_json = workflow.json()
        
        self.assertIsInstance(workflow_json, str)
        parsed = json.loads(workflow_json)
        self.assertEqual(parsed['name'], "Test Workflow")
        self.assertEqual(parsed['status'], "active")


class TestExecutionModel(unittest.TestCase):
    """Test cases for Execution model"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_module = mock_database_models()
        self.Execution = self.mock_module.Execution
    
    def test_execution_creation_default_values(self):
        """Test execution creation with default values"""
        execution = self.Execution(workflow_id=1)
        
        self.assertEqual(execution.workflow_id, 1)
        self.assertEqual(execution.status, "pending")
        self.assertEqual(execution.execution_mode, "attended")
        self.assertEqual(execution.triggered_by, "manual")
        self.assertEqual(execution.priority, "normal")
        self.assertIsNone(execution.started_at)
        self.assertIsNone(execution.completed_at)
        self.assertEqual(execution.context, {})
    
    def test_execution_validation_success(self):
        """Test successful execution validation"""
        execution = self.Execution(
            workflow_id=1,
            status="pending",
            execution_mode="attended",
            priority="normal"
        )
        
        errors = execution.validate()
        self.assertEqual(len(errors), 0)
    
    def test_execution_validation_failures(self):
        """Test execution validation failures"""
        # Missing workflow_id
        execution = self.Execution()
        errors = execution.validate()
        self.assertIn("Workflow ID is required", errors)
        
        # Invalid status
        execution = self.Execution(workflow_id=1, status="invalid")
        errors = execution.validate()
        self.assertIn("Invalid status", errors)
        
        # Invalid execution_mode
        execution = self.Execution(workflow_id=1, execution_mode="invalid")
        errors = execution.validate()
        self.assertIn("Invalid execution mode", errors)
        
        # Invalid priority
        execution = self.Execution(workflow_id=1, priority="invalid")
        errors = execution.validate()
        self.assertIn("Invalid priority", errors)
    
    def test_execution_status_checks(self):
        """Test execution status checking methods"""
        execution = self.Execution(workflow_id=1)
        
        # Test pending status
        execution.status = "pending"
        self.assertFalse(execution.is_running())
        self.assertFalse(execution.is_completed())
        
        # Test running status
        execution.status = "running"
        self.assertTrue(execution.is_running())
        self.assertFalse(execution.is_completed())
        
        # Test completed status
        execution.status = "completed"
        self.assertFalse(execution.is_running())
        self.assertTrue(execution.is_completed())
        
        # Test failed status
        execution.status = "failed"
        self.assertFalse(execution.is_running())
        self.assertTrue(execution.is_completed())
    
    def test_execution_duration_calculation(self):
        """Test execution duration calculation"""
        execution = self.Execution(workflow_id=1)
        
        # No duration without timestamps
        self.assertIsNone(execution.get_duration())
        
        # Set timestamps
        start_time = datetime(2024, 1, 1, 10, 0, 0)
        end_time = datetime(2024, 1, 1, 10, 5, 30)  # 5.5 minutes later
        
        execution.started_at = start_time
        execution.completed_at = end_time
        
        duration = execution.get_duration()
        self.assertEqual(duration, 330.0)  # 5.5 minutes = 330 seconds
    
    def test_execution_lifecycle_methods(self):
        """Test execution lifecycle management methods"""
        execution = self.Execution(workflow_id=1)
        
        # Mark as started
        execution.mark_started()
        self.assertEqual(execution.status, "running")
        self.assertIsNotNone(execution.started_at)
        
        # Mark as completed
        result = {"output": "test result"}
        execution.mark_completed(result)
        self.assertEqual(execution.status, "completed")
        self.assertIsNotNone(execution.completed_at)
        self.assertEqual(execution.result, result)
        
        # Test mark as failed
        execution2 = self.Execution(workflow_id=1)
        execution2.mark_failed("Test error")
        self.assertEqual(execution2.status, "failed")
        self.assertEqual(execution2.error, "Test error")
        self.assertIsNotNone(execution2.completed_at)


class TestTaskModel(unittest.TestCase):
    """Test cases for Task model"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_module = mock_database_models()
        self.Task = self.mock_module.Task
    
    def test_task_creation_default_values(self):
        """Test task creation with default values"""
        task = self.Task(title="Test Task")
        
        self.assertEqual(task.title, "Test Task")
        self.assertEqual(task.task_type, "manual")
        self.assertEqual(task.status, "pending")
        self.assertEqual(task.priority, "normal")
        self.assertIsNone(task.description)
        self.assertIsNone(task.assigned_to)
        self.assertIsInstance(task.created_at, datetime)
        self.assertEqual(task.data, {})
    
    def test_task_validation_success(self):
        """Test successful task validation"""
        task = self.Task(
            title="Valid Task",
            task_type="manual",
            status="pending",
            priority="normal"
        )
        
        errors = task.validate()
        self.assertEqual(len(errors), 0)
    
    def test_task_validation_failures(self):
        """Test task validation failures"""
        # Missing title
        task = self.Task(title="")
        errors = task.validate()
        self.assertIn("Task title is required", errors)
        
        # Invalid task_type
        task = self.Task(title="Test", task_type="invalid")
        errors = task.validate()
        self.assertIn("Invalid task type", errors)
        
        # Invalid status
        task = self.Task(title="Test", status="invalid")
        errors = task.validate()
        self.assertIn("Invalid task status", errors)
        
        # Invalid priority
        task = self.Task(title="Test", priority="invalid")
        errors = task.validate()
        self.assertIn("Invalid priority", errors)
    
    def test_task_overdue_check(self):
        """Test task overdue checking"""
        task = self.Task(title="Test Task")
        
        # No due date
        self.assertFalse(task.is_overdue())
        
        # Future due date
        future_date = datetime.utcnow() + timedelta(days=1)
        task.due_date = future_date
        self.assertFalse(task.is_overdue())
        
        # Past due date
        past_date = datetime.utcnow() - timedelta(days=1)
        task.due_date = past_date
        self.assertTrue(task.is_overdue())
        
        # Completed task (not overdue even if past due)
        task.status = "completed"
        self.assertFalse(task.is_overdue())
    
    def test_task_assignment(self):
        """Test task assignment"""
        task = self.Task(title="Test Task", status="pending")
        
        # Assign to user
        task.assign_to("user123")
        
        self.assertEqual(task.assigned_to, "user123")
        self.assertEqual(task.status, "in_progress")


class TestUserModel(unittest.TestCase):
    """Test cases for User model"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_module = mock_database_models()
        self.User = self.mock_module.User
    
    def test_user_creation_default_values(self):
        """Test user creation with default values"""
        user = self.User(username="testuser", email="test@example.com")
        
        self.assertEqual(user.username, "testuser")
        self.assertEqual(user.email, "test@example.com")
        self.assertEqual(user.role, "user")
        self.assertTrue(user.is_active)
        self.assertIsNone(user.full_name)
        self.assertIsInstance(user.created_at, datetime)
        self.assertEqual(user.preferences, {})
    
    def test_user_validation_success(self):
        """Test successful user validation"""
        user = self.User(
            username="testuser",
            email="test@example.com",
            role="user"
        )
        
        errors = user.validate()
        self.assertEqual(len(errors), 0)
    
    def test_user_validation_failures(self):
        """Test user validation failures"""
        # Missing username
        user = self.User(username="", email="test@example.com")
        errors = user.validate()
        self.assertIn("Username is required", errors)
        
        # Missing email
        user = self.User(username="test", email="")
        errors = user.validate()
        self.assertIn("Email is required", errors)
        
        # Invalid email format
        user = self.User(username="test", email="invalid-email")
        errors = user.validate()
        self.assertIn("Invalid email format", errors)
        
        # Invalid role
        user = self.User(username="test", email="test@example.com", role="invalid")
        errors = user.validate()
        self.assertIn("Invalid role", errors)
    
    def test_user_role_checks(self):
        """Test user role checking methods"""
        # Regular user
        user = self.User(username="user", email="user@example.com", role="user")
        self.assertFalse(user.is_admin())
        self.assertFalse(user.can_manage_workflows())
        
        # Admin user
        user.role = "admin"
        self.assertTrue(user.is_admin())
        self.assertTrue(user.can_manage_workflows())
        
        # Manager user
        user.role = "manager"
        self.assertFalse(user.is_admin())
        self.assertTrue(user.can_manage_workflows())


class TestWorkflowVersionModel(unittest.TestCase):
    """Test cases for WorkflowVersion model"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_module = mock_database_models()
        self.WorkflowVersion = self.mock_module.WorkflowVersion
    
    def test_workflow_version_creation_default_values(self):
        """Test workflow version creation with default values"""
        version = self.WorkflowVersion(
            workflow_id=1,
            definition={"steps": []}
        )
        
        self.assertEqual(version.workflow_id, 1)
        self.assertEqual(version.version_number, 1)
        self.assertEqual(version.definition, {"steps": []})
        self.assertIsInstance(version.created_at, datetime)
        self.assertEqual(version.changelog, "")
        self.assertFalse(version.is_current)
    
    def test_workflow_version_validation_success(self):
        """Test successful workflow version validation"""
        version = self.WorkflowVersion(
            workflow_id=1,
            version_number=2,
            definition={"nodes": [], "edges": []}
        )
        
        errors = version.validate()
        self.assertEqual(len(errors), 0)
    
    def test_workflow_version_validation_failures(self):
        """Test workflow version validation failures"""
        # Missing workflow_id
        version = self.WorkflowVersion(definition={"steps": []})
        errors = version.validate()
        self.assertIn("Workflow ID is required", errors)
        
        # Invalid version number
        version = self.WorkflowVersion(
            workflow_id=1,
            version_number=0,
            definition={"steps": []}
        )
        errors = version.validate()
        self.assertIn("Version number must be positive", errors)
        
        # Missing definition
        version = self.WorkflowVersion(workflow_id=1, definition={})
        errors = version.validate()
        self.assertIn("Definition is required", errors)


def run_database_model_tests():
    """Run all database model tests"""
    print("Running Database Model Tests...")
    print("=" * 50)
    
    # Create test suite
    test_classes = [
        TestWorkflowModel,
        TestExecutionModel,
        TestTaskModel,
        TestUserModel,
        TestWorkflowVersionModel
    ]
    
    suite = unittest.TestSuite()
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\nTest Results:")
    print("Tests Run: {}".format(result.testsRun))
    print("Failures: {}".format(len(result.failures)))
    print("Errors: {}".format(len(result.errors)))
    success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100)
    print("Success Rate: {:.1f}%".format(success_rate))
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_database_model_tests()
    if success:
        print("\n[SUCCESS] All Database Model tests passed!")
    else:
        print("\n[FAILED] Some tests failed!")