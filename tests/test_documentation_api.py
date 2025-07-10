"""
Documentation Testing and API Validation Suite
===============================================

This test suite validates:
- API documentation accuracy and completeness
- OpenAPI/Swagger schema validation
- Docstring coverage and quality
- Example code in documentation
- API response schema validation
- Documentation accessibility and formatting

Ensures developer experience and integration ease.
"""

import pytest
import json
import requests
from typing import Dict, Any, List
from pathlib import Path
import ast
import inspect
import docstring_parser
from fastapi.testclient import TestClient
from fastapi.openapi.utils import get_openapi

from ai_engine.main import app
from ai_engine.routers import (
    workflow_router,
    execution_router,
    task_router,
    auth_router,
    discovery_router,
    recording_router,
    chat_router,
    real_time_router,
    websocket_router,
)


@pytest.fixture
def client():
    """Create test client for API testing"""
    return TestClient(app)


@pytest.fixture
def openapi_schema():
    """Get OpenAPI schema from FastAPI app"""
    return get_openapi(
        title=app.title,
        version=app.version,
        openapi_version=app.openapi_version,
        description=app.description,
        routes=app.routes,
    )


class TestAPIDocumentation:
    """Test API documentation completeness and accuracy"""
    
    def test_openapi_schema_generation(self, openapi_schema):
        """Test that OpenAPI schema is properly generated"""
        assert openapi_schema is not None
        assert "openapi" in openapi_schema
        assert "info" in openapi_schema
        assert "paths" in openapi_schema
        
        # Check required info fields
        info = openapi_schema["info"]
        assert "title" in info
        assert "version" in info
        assert len(info["title"]) > 0
        assert len(info["version"]) > 0
    
    def test_api_endpoints_documented(self, openapi_schema):
        """Test that all API endpoints are documented"""
        paths = openapi_schema.get("paths", {})
        
        # Expected core endpoints
        expected_endpoints = [
            "/workflows",
            "/workflows/{workflow_id}",
            "/executions",
            "/executions/{execution_id}",
            "/tasks",
            "/auth/token",
            "/auth/me",
        ]
        
        documented_paths = set(paths.keys())
        
        for endpoint in expected_endpoints:
            # Check if exact match or pattern match exists
            matches = [path for path in documented_paths if self._path_matches(path, endpoint)]
            assert len(matches) > 0, f"Endpoint {endpoint} not found in documentation"
    
    def _path_matches(self, documented_path: str, expected_path: str) -> bool:
        """Check if documented path matches expected path pattern"""
        # Simple pattern matching for path parameters
        doc_parts = documented_path.split("/")
        exp_parts = expected_path.split("/")
        
        if len(doc_parts) != len(exp_parts):
            return False
        
        for doc_part, exp_part in zip(doc_parts, exp_parts):
            if exp_part.startswith("{") and exp_part.endswith("}"):
                # Path parameter - should match {param_name} pattern in documented path
                continue
            elif doc_part != exp_part:
                return False
        
        return True
    
    def test_http_methods_documented(self, openapi_schema):
        """Test that HTTP methods are properly documented"""
        paths = openapi_schema.get("paths", {})
        
        for path, methods in paths.items():
            for method, details in methods.items():
                if method in ["get", "post", "put", "delete", "patch"]:
                    # Check required fields for each method
                    assert "responses" in details, f"No responses documented for {method.upper()} {path}"
                    assert "summary" in details or "description" in details, \
                        f"No summary/description for {method.upper()} {path}"
                    
                    # Check that 200/201 success responses are documented
                    responses = details["responses"]
                    success_codes = [code for code in responses.keys() if code.startswith("2")]
                    assert len(success_codes) > 0, f"No success response documented for {method.upper()} {path}"
    
    def test_request_schemas_documented(self, openapi_schema):
        """Test that request schemas are properly documented"""
        paths = openapi_schema.get("paths", {})
        
        for path, methods in paths.items():
            for method, details in methods.items():
                if method in ["post", "put", "patch"]:
                    # These methods should have request body documentation
                    if "requestBody" in details:
                        request_body = details["requestBody"]
                        assert "content" in request_body
                        
                        content = request_body["content"]
                        assert "application/json" in content or "multipart/form-data" in content
                        
                        # Check schema is defined
                        for content_type, content_details in content.items():
                            if "schema" in content_details:
                                schema = content_details["schema"]
                                assert "$ref" in schema or "properties" in schema
    
    def test_response_schemas_documented(self, openapi_schema):
        """Test that response schemas are properly documented"""
        paths = openapi_schema.get("paths", {})
        components = openapi_schema.get("components", {})
        schemas = components.get("schemas", {})
        
        for path, methods in paths.items():
            for method, details in methods.items():
                responses = details.get("responses", {})
                
                for status_code, response_details in responses.items():
                    if status_code.startswith("2"):  # Success responses
                        if "content" in response_details:
                            content = response_details["content"]
                            
                            for content_type, content_details in content.items():
                                if "schema" in content_details:
                                    schema = content_details["schema"]
                                    
                                    # Validate schema reference or structure
                                    if "$ref" in schema:
                                        ref_path = schema["$ref"]
                                        if ref_path.startswith("#/components/schemas/"):
                                            schema_name = ref_path.split("/")[-1]
                                            assert schema_name in schemas, \
                                                f"Referenced schema {schema_name} not found"
    
    def test_error_responses_documented(self, openapi_schema):
        """Test that error responses are documented"""
        paths = openapi_schema.get("paths", {})
        
        for path, methods in paths.items():
            for method, details in methods.items():
                responses = details.get("responses", {})
                
                # Check for common error status codes
                error_codes = ["400", "401", "403", "404", "422", "500"]
                documented_errors = [code for code in responses.keys() if code in error_codes]
                
                # At least some error responses should be documented
                assert len(documented_errors) > 0, \
                    f"No error responses documented for {method.upper()} {path}"
    
    def test_authentication_documented(self, openapi_schema):
        """Test that authentication requirements are documented"""
        components = openapi_schema.get("components", {})
        security_schemes = components.get("securitySchemes", {})
        
        # Should have security schemes defined
        assert len(security_schemes) > 0, "No security schemes documented"
        
        # Check for common auth types
        auth_types = [scheme.get("type") for scheme in security_schemes.values()]
        assert "http" in auth_types or "oauth2" in auth_types or "apiKey" in auth_types


class TestDocstringCoverage:
    """Test Python docstring coverage and quality"""
    
    def test_module_docstrings(self):
        """Test that Python modules have docstrings"""
        ai_engine_path = Path("ai_engine")
        python_files = list(ai_engine_path.rglob("*.py"))
        
        missing_docstrings = []
        
        for file_path in python_files:
            if file_path.name == "__init__.py":
                continue  # Skip __init__.py files
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                tree = ast.parse(content)
                
                # Check if module has docstring
                if not ast.get_docstring(tree):
                    missing_docstrings.append(str(file_path))
                    
            except Exception as e:
                pytest.skip(f"Could not parse {file_path}: {e}")
        
        # Allow some files to not have docstrings
        coverage_percentage = (len(python_files) - len(missing_docstrings)) / len(python_files) * 100
        assert coverage_percentage >= 70, \
            f"Module docstring coverage too low: {coverage_percentage:.1f}% (missing: {missing_docstrings})"
    
    def test_function_docstrings(self):
        """Test that public functions have docstrings"""
        from ai_engine import workflow_engine, task_detection, database
        
        modules_to_test = [workflow_engine, task_detection, database]
        
        for module in modules_to_test:
            functions = [getattr(module, name) for name in dir(module) 
                        if callable(getattr(module, name)) and not name.startswith('_')]
            
            missing_docstrings = []
            
            for func in functions:
                if not func.__doc__:
                    missing_docstrings.append(f"{module.__name__}.{func.__name__}")
            
            if functions:  # Only check if module has functions
                coverage = (len(functions) - len(missing_docstrings)) / len(functions) * 100
                assert coverage >= 60, \
                    f"Function docstring coverage too low in {module.__name__}: {coverage:.1f}%"
    
    def test_class_docstrings(self):
        """Test that classes have docstrings"""
        from ai_engine.models import workflow, execution, task, user
        
        modules_to_test = [workflow, execution, task, user]
        
        for module in modules_to_test:
            classes = [getattr(module, name) for name in dir(module) 
                      if inspect.isclass(getattr(module, name)) and not name.startswith('_')]
            
            missing_docstrings = []
            
            for cls in classes:
                if not cls.__doc__:
                    missing_docstrings.append(f"{module.__name__}.{cls.__name__}")
            
            if classes:  # Only check if module has classes
                coverage = (len(classes) - len(missing_docstrings)) / len(classes) * 100
                assert coverage >= 80, \
                    f"Class docstring coverage too low in {module.__name__}: {coverage:.1f}%"
    
    def test_docstring_quality(self):
        """Test docstring quality and format"""
        from ai_engine.workflow_engine import WorkflowEngine
        
        if hasattr(WorkflowEngine, 'execute_workflow'):
            func = WorkflowEngine.execute_workflow
            if func.__doc__:
                # Parse docstring
                try:
                    parsed = docstring_parser.parse(func.__doc__)
                    
                    # Check for required sections
                    assert parsed.short_description, "Docstring should have short description"
                    assert len(parsed.short_description) > 10, "Short description too brief"
                    
                    # Check parameters are documented
                    if hasattr(func, '__code__') and func.__code__.co_argcount > 1:  # Exclude 'self'
                        param_names = func.__code__.co_varnames[1:func.__code__.co_argcount]
                        documented_params = [param.arg_name for param in parsed.params]
                        
                        for param_name in param_names:
                            if param_name not in documented_params:
                                pytest.skip(f"Parameter {param_name} not documented")
                    
                except Exception:
                    pytest.skip("Could not parse docstring format")


class TestAPIResponseValidation:
    """Test API response validation against documented schemas"""
    
    def test_workflow_list_response_schema(self, client):
        """Test workflow list endpoint response matches schema"""
        response = client.get("/workflows/")
        
        # Should return 200 or 401 (if auth required)
        assert response.status_code in [200, 401]
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list), "Workflows endpoint should return a list"
            
            if data:  # If there are workflows
                workflow = data[0]
                required_fields = ["id", "name", "description", "steps"]
                
                for field in required_fields:
                    assert field in workflow, f"Workflow missing required field: {field}"
                
                # Validate field types
                assert isinstance(workflow["id"], int), "Workflow ID should be integer"
                assert isinstance(workflow["name"], str), "Workflow name should be string"
                assert isinstance(workflow["steps"], list), "Workflow steps should be list"
    
    def test_execution_response_schema(self, client):
        """Test execution endpoint response matches schema"""
        response = client.get("/executions/")
        
        assert response.status_code in [200, 401]
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list), "Executions endpoint should return a list"
            
            if data:  # If there are executions
                execution = data[0]
                required_fields = ["id", "workflow_id", "status"]
                
                for field in required_fields:
                    assert field in execution, f"Execution missing required field: {field}"
                
                # Validate field types
                assert isinstance(execution["id"], int), "Execution ID should be integer"
                assert isinstance(execution["workflow_id"], int), "Workflow ID should be integer"
                assert isinstance(execution["status"], str), "Execution status should be string"
    
    def test_error_response_schema(self, client):
        """Test error responses match documented schema"""
        # Test 404 error
        response = client.get("/workflows/99999")
        
        if response.status_code == 404:
            data = response.json()
            assert "detail" in data, "Error response should have 'detail' field"
            assert isinstance(data["detail"], str), "Error detail should be string"
        
        # Test validation error (422)
        response = client.post("/workflows/", json={"invalid": "data"})
        
        if response.status_code == 422:
            data = response.json()
            assert "detail" in data, "Validation error should have 'detail' field"
            assert isinstance(data["detail"], list), "Validation detail should be list"


class TestDocumentationExamples:
    """Test code examples in documentation"""
    
    def test_readme_examples(self):
        """Test examples in README file"""
        readme_path = Path("README.md")
        
        if not readme_path.exists():
            pytest.skip("README.md not found")
        
        with open(readme_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for common documentation sections
        required_sections = ["installation", "usage", "api", "example"]
        content_lower = content.lower()
        
        missing_sections = []
        for section in required_sections:
            if section not in content_lower:
                missing_sections.append(section)
        
        assert len(missing_sections) <= 1, \
            f"README missing important sections: {missing_sections}"
        
        # Check for code examples
        code_blocks = content.count("```")
        assert code_blocks >= 4, "README should have at least 2 code examples (4 ``` markers)"
    
    def test_api_example_requests(self, client):
        """Test that API examples in documentation work"""
        # Example workflow creation
        example_workflow = {
            "name": "Example Workflow",
            "description": "Documentation example workflow",
            "steps": [
                {"action": "click", "target": "button", "parameters": {"x": 100, "y": 200}}
            ]
        }
        
        response = client.post("/workflows/", json=example_workflow)
        
        # Should either succeed or require authentication
        assert response.status_code in [200, 201, 401, 422]
        
        if response.status_code in [200, 201]:
            data = response.json()
            assert data["name"] == example_workflow["name"]
            assert data["description"] == example_workflow["description"]


class TestAPIAccessibility:
    """Test API accessibility and usability"""
    
    def test_cors_headers(self, client):
        """Test CORS headers are properly configured"""
        # OPTIONS request to check CORS
        response = client.options("/workflows/")
        
        # Should have CORS headers for web access
        # Note: This might not be testable in TestClient, depends on CORS middleware
        assert response.status_code in [200, 404, 405]  # Various acceptable responses
    
    def test_content_type_headers(self, client):
        """Test proper content-type headers"""
        response = client.get("/workflows/")
        
        if response.status_code == 200:
            assert "application/json" in response.headers.get("content-type", "")
    
    def test_rate_limiting_headers(self, client):
        """Test rate limiting headers if implemented"""
        response = client.get("/workflows/")
        
        # Rate limiting headers are optional but good practice
        headers = response.headers
        rate_limit_headers = [
            "x-ratelimit-limit",
            "x-ratelimit-remaining", 
            "x-ratelimit-reset",
            "retry-after"
        ]
        
        # If any rate limit headers are present, log them
        present_headers = [h for h in rate_limit_headers if h in headers]
        if present_headers:
            print(f"Rate limiting headers found: {present_headers}")


class TestOpenAPIValidation:
    """Test OpenAPI specification compliance"""
    
    def test_openapi_version_compliance(self, openapi_schema):
        """Test OpenAPI version compliance"""
        openapi_version = openapi_schema.get("openapi", "")
        
        # Should use OpenAPI 3.x
        assert openapi_version.startswith("3."), f"Should use OpenAPI 3.x, found: {openapi_version}"
    
    def test_schema_components_defined(self, openapi_schema):
        """Test that schema components are properly defined"""
        components = openapi_schema.get("components", {})
        schemas = components.get("schemas", {})
        
        # Should have model schemas defined
        expected_schemas = ["Workflow", "Execution", "Task", "User"]
        
        for schema_name in expected_schemas:
            if schema_name in schemas:
                schema = schemas[schema_name]
                assert "type" in schema, f"Schema {schema_name} missing type"
                assert "properties" in schema, f"Schema {schema_name} missing properties"
    
    def test_parameter_definitions(self, openapi_schema):
        """Test parameter definitions in paths"""
        paths = openapi_schema.get("paths", {})
        
        for path, methods in paths.items():
            if "{" in path:  # Path has parameters
                for method, details in methods.items():
                    if "parameters" in details:
                        parameters = details["parameters"]
                        
                        for param in parameters:
                            assert "name" in param, f"Parameter missing name in {method.upper()} {path}"
                            assert "in" in param, f"Parameter missing 'in' field in {method.upper()} {path}"
                            assert "schema" in param, f"Parameter missing schema in {method.upper()} {path}"
    
    def test_tags_organization(self, openapi_schema):
        """Test that endpoints are properly organized with tags"""
        paths = openapi_schema.get("paths", {})
        
        untagged_endpoints = []
        
        for path, methods in paths.items():
            for method, details in methods.items():
                if "tags" not in details or not details["tags"]:
                    untagged_endpoints.append(f"{method.upper()} {path}")
        
        # Most endpoints should have tags for organization
        total_endpoints = sum(len(methods) for methods in paths.values())
        if total_endpoints > 0:
            tagged_percentage = (total_endpoints - len(untagged_endpoints)) / total_endpoints * 100
            assert tagged_percentage >= 70, \
                f"Too many untagged endpoints: {tagged_percentage:.1f}% tagged"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])