"""
Environment Variable Validator
=============================

Validates required environment variables at application startup.
"""

import os
import logging
from typing import Dict, List, Optional, Any
from enum import Enum

logger = logging.getLogger(__name__)


class RequirementLevel(Enum):
    """Requirement levels for environment variables"""
    REQUIRED = "required"
    RECOMMENDED = "recommended"
    OPTIONAL = "optional"


class EnvValidator:
    """Validates environment variables and provides configuration insights"""
    
    def __init__(self):
        self.variables = {}
        self.validation_results = {}
        
        # Define environment variable requirements
        self._define_requirements()
    
    def _define_requirements(self):
        """Define environment variable requirements"""
        
        # Database configuration
        self.variables.update({
            "DATABASE_URL": {
                "level": RequirementLevel.REQUIRED,
                "description": "Database connection string",
                "example": "postgresql://user:pass@host:5432/dbname",
                "validator": self._validate_database_url
            },
            "POSTGRES_DB": {
                "level": RequirementLevel.RECOMMENDED,
                "description": "PostgreSQL database name",
                "example": "autoops"
            },
            "POSTGRES_USER": {
                "level": RequirementLevel.RECOMMENDED,
                "description": "PostgreSQL username",
                "example": "postgres"
            },
            "POSTGRES_PASSWORD": {
                "level": RequirementLevel.RECOMMENDED,
                "description": "PostgreSQL password",
                "example": "secure_password",
                "sensitive": True
            }
        })
        
        # Redis configuration
        self.variables.update({
            "REDIS_URL": {
                "level": RequirementLevel.RECOMMENDED,
                "description": "Redis connection string",
                "example": "redis://localhost:6379/0",
                "validator": self._validate_redis_url
            }
        })
        
        # Security configuration
        self.variables.update({
            "SECRET_KEY": {
                "level": RequirementLevel.REQUIRED,
                "description": "Application secret key for JWT tokens",
                "example": "your-secret-key-here",
                "sensitive": True,
                "validator": self._validate_secret_key
            },
            "ACCESS_TOKEN_EXPIRE_MINUTES": {
                "level": RequirementLevel.OPTIONAL,
                "description": "JWT token expiration time in minutes",
                "example": "30",
                "validator": self._validate_positive_integer
            }
        })
        
        # External service API keys
        self.variables.update({
            "OPENAI_API_KEY": {
                "level": RequirementLevel.RECOMMENDED,
                "description": "OpenAI API key for LLM integration",
                "example": "sk-...",
                "sensitive": True,
                "validator": self._validate_openai_key
            },
            "ANTHROPIC_API_KEY": {
                "level": RequirementLevel.OPTIONAL,
                "description": "Anthropic API key for Claude integration",
                "example": "sk-ant-...",
                "sensitive": True
            }
        })
        
        # Email configuration
        self.variables.update({
            "SMTP_SERVER": {
                "level": RequirementLevel.OPTIONAL,
                "description": "SMTP server hostname",
                "example": "smtp.gmail.com"
            },
            "SMTP_PORT": {
                "level": RequirementLevel.OPTIONAL,
                "description": "SMTP server port",
                "example": "587",
                "validator": self._validate_port
            },
            "SMTP_USERNAME": {
                "level": RequirementLevel.OPTIONAL,
                "description": "SMTP username/email",
                "example": "your-email@gmail.com",
                "sensitive": True
            },
            "SMTP_PASSWORD": {
                "level": RequirementLevel.OPTIONAL,
                "description": "SMTP password or app password",
                "example": "your-app-password",
                "sensitive": True
            }
        })
        
        # Application configuration
        self.variables.update({
            "LOG_LEVEL": {
                "level": RequirementLevel.OPTIONAL,
                "description": "Logging level",
                "example": "INFO",
                "validator": self._validate_log_level
            },
            "ALLOWED_ORIGINS": {
                "level": RequirementLevel.OPTIONAL,
                "description": "CORS allowed origins",
                "example": "http://localhost:3000,https://yourdomain.com"
            },
            "ENABLE_METRICS": {
                "level": RequirementLevel.OPTIONAL,
                "description": "Enable metrics collection",
                "example": "true",
                "validator": self._validate_boolean
            }
        })
        
        # Feature flags
        self.variables.update({
            "ENABLE_DESKTOP_AUTOMATION": {
                "level": RequirementLevel.OPTIONAL,
                "description": "Enable desktop automation features",
                "example": "false",
                "validator": self._validate_boolean
            },
            "ENABLE_BROWSER_AUTOMATION": {
                "level": RequirementLevel.OPTIONAL,
                "description": "Enable browser automation features",
                "example": "false",
                "validator": self._validate_boolean
            }
        })
    
    def validate_all(self) -> Dict[str, Any]:
        """
        Validate all environment variables and return results
        
        Returns:
            Dict with validation results, warnings, and errors
        """
        results = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "missing_required": [],
            "missing_recommended": [],
            "configured_variables": [],
            "sensitive_in_logs": []
        }
        
        for var_name, config in self.variables.items():
            value = os.getenv(var_name)
            level = config["level"]
            
            # Check if variable is set
            if value is None:
                if level == RequirementLevel.REQUIRED:
                    results["errors"].append(f"Required environment variable '{var_name}' is not set")
                    results["missing_required"].append(var_name)
                    results["valid"] = False
                elif level == RequirementLevel.RECOMMENDED:
                    results["warnings"].append(f"Recommended environment variable '{var_name}' is not set")
                    results["missing_recommended"].append(var_name)
            else:
                # Variable is set
                results["configured_variables"].append(var_name)
                
                # Run custom validator if provided
                validator = config.get("validator")
                if validator:
                    validation_result = validator(value)
                    if not validation_result["valid"]:
                        results["errors"].append(f"Invalid value for '{var_name}': {validation_result['error']}")
                        results["valid"] = False
                
                # Check for sensitive variables in logs
                if config.get("sensitive", False) and not value.startswith("***"):
                    results["sensitive_in_logs"].append(var_name)
        
        self.validation_results = results
        return results
    
    def _validate_database_url(self, value: str) -> Dict[str, Any]:
        """Validate database URL format"""
        if not value:
            return {"valid": False, "error": "Database URL cannot be empty"}
        
        if not (value.startswith("postgresql://") or value.startswith("sqlite://")):
            return {"valid": False, "error": "Database URL must start with postgresql:// or sqlite://"}
        
        return {"valid": True}
    
    def _validate_redis_url(self, value: str) -> Dict[str, Any]:
        """Validate Redis URL format"""
        if not value.startswith("redis://"):
            return {"valid": False, "error": "Redis URL must start with redis://"}
        
        return {"valid": True}
    
    def _validate_secret_key(self, value: str) -> Dict[str, Any]:
        """Validate secret key strength"""
        if len(value) < 16:
            return {"valid": False, "error": "Secret key must be at least 16 characters long"}
        
        if value in ["test_secret_key_for_development", "your-secret-key-here"]:
            return {"valid": False, "error": "Secret key appears to be a placeholder - use a secure random key"}
        
        return {"valid": True}
    
    def _validate_openai_key(self, value: str) -> Dict[str, Any]:
        """Validate OpenAI API key format"""
        if not value.startswith("sk-"):
            return {"valid": False, "error": "OpenAI API key must start with 'sk-'"}
        
        if value == "test_key_placeholder":
            return {"valid": False, "error": "OpenAI API key appears to be a placeholder"}
        
        return {"valid": True}
    
    def _validate_positive_integer(self, value: str) -> Dict[str, Any]:
        """Validate positive integer"""
        try:
            int_value = int(value)
            if int_value <= 0:
                return {"valid": False, "error": "Value must be a positive integer"}
            return {"valid": True}
        except ValueError:
            return {"valid": False, "error": "Value must be an integer"}
    
    def _validate_port(self, value: str) -> Dict[str, Any]:
        """Validate port number"""
        try:
            port = int(value)
            if not (1 <= port <= 65535):
                return {"valid": False, "error": "Port must be between 1 and 65535"}
            return {"valid": True}
        except ValueError:
            return {"valid": False, "error": "Port must be an integer"}
    
    def _validate_log_level(self, value: str) -> Dict[str, Any]:
        """Validate log level"""
        valid_levels = ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"]
        if value.upper() not in valid_levels:
            return {"valid": False, "error": f"Log level must be one of: {', '.join(valid_levels)}"}
        
        return {"valid": True}
    
    def _validate_boolean(self, value: str) -> Dict[str, Any]:
        """Validate boolean value"""
        if value.lower() not in ["true", "false", "1", "0", "yes", "no"]:
            return {"valid": False, "error": "Boolean value must be true/false, 1/0, or yes/no"}
        
        return {"valid": True}
    
    def print_validation_report(self):
        """Print a formatted validation report"""
        if not self.validation_results:
            self.validate_all()
        
        results = self.validation_results
        
        print("\n" + "=" * 60)
        print("ENVIRONMENT VARIABLE VALIDATION REPORT")
        print("=" * 60)
        
        # Overall status
        status = "✅ VALID" if results["valid"] else "❌ INVALID"
        print(f"Overall Status: {status}")
        print()
        
        # Configured variables
        if results["configured_variables"]:
            print(f"✅ Configured Variables ({len(results['configured_variables'])}):")
            for var in sorted(results["configured_variables"]):
                sensitive = self.variables[var].get("sensitive", False)
                value = os.getenv(var)
                display_value = "***HIDDEN***" if sensitive else value
                print(f"   {var} = {display_value}")
            print()
        
        # Errors
        if results["errors"]:
            print(f"❌ Errors ({len(results['errors'])}):")
            for error in results["errors"]:
                print(f"   • {error}")
            print()
        
        # Warnings
        if results["warnings"]:
            print(f"⚠️  Warnings ({len(results['warnings'])}):")
            for warning in results["warnings"]:
                print(f"   • {warning}")
            print()
        
        # Missing required variables
        if results["missing_required"]:
            print("💡 Required Variables Setup Guide:")
            for var in results["missing_required"]:
                config = self.variables[var]
                print(f"   {var}:")
                print(f"     Description: {config['description']}")
                print(f"     Example: {config['example']}")
            print()
        
        # Missing recommended variables
        if results["missing_recommended"]:
            print("💡 Recommended Variables Setup Guide:")
            for var in results["missing_recommended"]:
                config = self.variables[var]
                print(f"   {var}:")
                print(f"     Description: {config['description']}")
                print(f"     Example: {config['example']}")
            print()
        
        # Security warnings
        if results["sensitive_in_logs"]:
            print("🔒 Security Warning:")
            print("   The following sensitive variables may be exposed in logs:")
            for var in results["sensitive_in_logs"]:
                print(f"   • {var}")
            print("   Consider using secrets management or masking values.")
            print()
        
        print("=" * 60)
    
    def get_missing_variables_guide(self) -> str:
        """Get a guide for setting up missing variables"""
        if not self.validation_results:
            self.validate_all()
        
        results = self.validation_results
        guide_lines = []
        
        if results["missing_required"] or results["missing_recommended"]:
            guide_lines.append("# Environment Variables Setup Guide")
            guide_lines.append("")
            guide_lines.append("# Copy this to your .env file and update with your values:")
            guide_lines.append("")
            
            for var_list, title in [(results["missing_required"], "# Required Variables"), 
                                   (results["missing_recommended"], "# Recommended Variables")]:
                if var_list:
                    guide_lines.append(title)
                    for var in var_list:
                        config = self.variables[var]
                        guide_lines.append(f"# {config['description']}")
                        guide_lines.append(f"{var}={config['example']}")
                        guide_lines.append("")
        
        return "\n".join(guide_lines)
    
    def is_production_ready(self) -> bool:
        """Check if configuration is production ready"""
        if not self.validation_results:
            self.validate_all()
        
        results = self.validation_results
        
        # Must have no errors
        if not results["valid"]:
            return False
        
        # Must have database configured
        if "DATABASE_URL" not in results["configured_variables"]:
            return False
        
        # Must have a secure secret key
        secret_key = os.getenv("SECRET_KEY", "")
        if secret_key in ["test_secret_key_for_development", "your-secret-key-here"]:
            return False
        
        return True


# Singleton instance
_env_validator = None


def get_env_validator() -> EnvValidator:
    """Get singleton environment validator instance"""
    global _env_validator
    if _env_validator is None:
        _env_validator = EnvValidator()
    return _env_validator


def validate_environment() -> Dict[str, Any]:
    """Validate environment and return results"""
    validator = get_env_validator()
    return validator.validate_all()


def print_env_report():
    """Print environment validation report"""
    validator = get_env_validator()
    validator.print_validation_report()


if __name__ == "__main__":
    # Run environment validation
    print_env_report()
    
    # Check if production ready
    validator = get_env_validator()
    if validator.is_production_ready():
        print("🚀 Configuration is production ready!")
    else:
        print("⚠️  Configuration needs updates for production deployment.")
    
    # Generate setup guide
    guide = validator.get_missing_variables_guide()
    if guide:
        print("\n" + guide)