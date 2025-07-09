"""
Secure Secrets Management System
=================================

This module provides a secure way to handle sensitive configuration data
including API keys, database passwords, and other secrets. It supports
multiple backends for secret storage and retrieval.
"""

import os
import json
import base64
import logging
from typing import Dict, Any, Optional, Union
from pathlib import Path
from cryptography.fernet import Fernet
import hashlib

logger = logging.getLogger(__name__)


class SecretNotFoundError(Exception):
    """Raised when a requested secret is not found"""
    pass


class SecretEncryptionError(Exception):
    """Raised when secret encryption/decryption fails"""
    pass


class SecretsManager:
    """
    Secure secrets management with multiple backend support
    """
    
    def __init__(self, backend: str = "env", **kwargs):
        """
        Initialize the secrets manager with specified backend
        
        Args:
            backend: Backend type ('env', 'file', 'vault', 'aws', 'gcp')
            **kwargs: Backend-specific configuration
        """
        self.backend = backend
        self.config = kwargs
        self._cache: Dict[str, str] = {}
        self._encryption_key: Optional[bytes] = None
        
        # Initialize encryption if enabled
        if self.config.get('encrypt', False):
            self._init_encryption()
    
    def _init_encryption(self):
        """Initialize encryption key for secret storage"""
        key_source = self.config.get('encryption_key_source', 'generate')
        
        if key_source == 'generate':
            # Generate a new key (store this securely!)
            self._encryption_key = Fernet.generate_key()
            logger.warning("Generated new encryption key. Store this securely!")
        elif key_source == 'env':
            # Get key from environment variable
            key_data = os.getenv('SECRETS_ENCRYPTION_KEY')
            if not key_data:
                raise SecretEncryptionError("SECRETS_ENCRYPTION_KEY not found in environment")
            self._encryption_key = key_data.encode()
        elif key_source == 'file':
            # Read key from file
            key_file = self.config.get('encryption_key_file', '.secrets_key')
            if not os.path.exists(key_file):
                raise SecretEncryptionError(f"Encryption key file not found: {key_file}")
            with open(key_file, 'rb') as f:
                self._encryption_key = f.read()
        else:
            raise SecretEncryptionError(f"Unknown encryption key source: {key_source}")
    
    def _encrypt_value(self, value: str) -> str:
        """Encrypt a secret value"""
        if not self._encryption_key:
            return value
        
        try:
            cipher = Fernet(self._encryption_key)
            encrypted = cipher.encrypt(value.encode())
            return base64.b64encode(encrypted).decode()
        except Exception as e:
            raise SecretEncryptionError(f"Failed to encrypt value: {e}")
    
    def _decrypt_value(self, encrypted_value: str) -> str:
        """Decrypt a secret value"""
        if not self._encryption_key:
            return encrypted_value
        
        try:
            cipher = Fernet(self._encryption_key)
            encrypted_bytes = base64.b64decode(encrypted_value.encode())
            decrypted = cipher.decrypt(encrypted_bytes)
            return decrypted.decode()
        except Exception as e:
            raise SecretEncryptionError(f"Failed to decrypt value: {e}")
    
    def get_secret(self, key: str, default: Optional[str] = None) -> str:
        """
        Retrieve a secret value
        
        Args:
            key: Secret identifier
            default: Default value if secret not found
            
        Returns:
            Secret value
            
        Raises:
            SecretNotFoundError: If secret not found and no default provided
        """
        # Check cache first
        if key in self._cache:
            return self._cache[key]
        
        # Retrieve from backend
        value = None
        
        if self.backend == "env":
            value = self._get_from_env(key)
        elif self.backend == "file":
            value = self._get_from_file(key)
        elif self.backend == "vault":
            value = self._get_from_vault(key)
        elif self.backend == "aws":
            value = self._get_from_aws(key)
        elif self.backend == "gcp":
            value = self._get_from_gcp(key)
        else:
            raise ValueError(f"Unknown backend: {self.backend}")
        
        if value is None:
            if default is not None:
                return default
            raise SecretNotFoundError(f"Secret '{key}' not found")
        
        # Decrypt if needed
        if self.config.get('encrypt', False):
            value = self._decrypt_value(value)
        
        # Cache the result
        self._cache[key] = value
        return value
    
    def set_secret(self, key: str, value: str):
        """
        Store a secret value
        
        Args:
            key: Secret identifier
            value: Secret value
        """
        # Encrypt if needed
        if self.config.get('encrypt', False):
            value = self._encrypt_value(value)
        
        # Store in backend
        if self.backend == "env":
            self._set_in_env(key, value)
        elif self.backend == "file":
            self._set_in_file(key, value)
        elif self.backend == "vault":
            self._set_in_vault(key, value)
        elif self.backend == "aws":
            self._set_in_aws(key, value)
        elif self.backend == "gcp":
            self._set_in_gcp(key, value)
        else:
            raise ValueError(f"Unknown backend: {self.backend}")
        
        # Update cache
        self._cache[key] = self._decrypt_value(value) if self.config.get('encrypt', False) else value
    
    def _get_from_env(self, key: str) -> Optional[str]:
        """Get secret from environment variables"""
        return os.getenv(key)
    
    def _set_in_env(self, key: str, value: str):
        """Set secret in environment variables"""
        os.environ[key] = value
    
    def _get_from_file(self, key: str) -> Optional[str]:
        """Get secret from file storage"""
        secrets_file = self.config.get('secrets_file', '.secrets.json')
        
        if not os.path.exists(secrets_file):
            return None
        
        try:
            with open(secrets_file, 'r') as f:
                secrets = json.load(f)
            return secrets.get(key)
        except Exception as e:
            logger.error(f"Failed to read secrets file: {e}")
            return None
    
    def _set_in_file(self, key: str, value: str):
        """Set secret in file storage"""
        secrets_file = self.config.get('secrets_file', '.secrets.json')
        
        # Load existing secrets
        secrets = {}
        if os.path.exists(secrets_file):
            try:
                with open(secrets_file, 'r') as f:
                    secrets = json.load(f)
            except Exception as e:
                logger.error(f"Failed to read existing secrets file: {e}")
        
        # Update secret
        secrets[key] = value
        
        # Save back to file
        try:
            with open(secrets_file, 'w') as f:
                json.dump(secrets, f, indent=2)
            
            # Set restrictive permissions
            os.chmod(secrets_file, 0o600)
        except Exception as e:
            logger.error(f"Failed to write secrets file: {e}")
            raise
    
    def _get_from_vault(self, key: str) -> Optional[str]:
        """Get secret from HashiCorp Vault"""
        try:
            import hvac
            
            vault_url = self.config.get('vault_url', 'http://localhost:8200')
            vault_token = self.config.get('vault_token', os.getenv('VAULT_TOKEN'))
            vault_path = self.config.get('vault_path', 'secret/autoops')
            
            client = hvac.Client(url=vault_url, token=vault_token)
            
            if not client.is_authenticated():
                raise Exception("Vault authentication failed")
            
            response = client.secrets.kv.v2.read_secret_version(
                path=vault_path,
                mount_point='secret'
            )
            
            return response['data']['data'].get(key)
        except ImportError:
            logger.error("hvac library not installed. Install with: pip install hvac")
            return None
        except Exception as e:
            logger.error(f"Failed to get secret from Vault: {e}")
            return None
    
    def _set_in_vault(self, key: str, value: str):
        """Set secret in HashiCorp Vault"""
        try:
            import hvac
            
            vault_url = self.config.get('vault_url', 'http://localhost:8200')
            vault_token = self.config.get('vault_token', os.getenv('VAULT_TOKEN'))
            vault_path = self.config.get('vault_path', 'secret/autoops')
            
            client = hvac.Client(url=vault_url, token=vault_token)
            
            if not client.is_authenticated():
                raise Exception("Vault authentication failed")
            
            # Get existing secrets
            try:
                response = client.secrets.kv.v2.read_secret_version(
                    path=vault_path,
                    mount_point='secret'
                )
                existing_secrets = response['data']['data']
            except:
                existing_secrets = {}
            
            # Update with new secret
            existing_secrets[key] = value
            
            # Write back to Vault
            client.secrets.kv.v2.create_or_update_secret(
                path=vault_path,
                secret=existing_secrets,
                mount_point='secret'
            )
        except ImportError:
            logger.error("hvac library not installed. Install with: pip install hvac")
            raise
        except Exception as e:
            logger.error(f"Failed to set secret in Vault: {e}")
            raise
    
    def _get_from_aws(self, key: str) -> Optional[str]:
        """Get secret from AWS Secrets Manager"""
        try:
            import boto3
            
            region = self.config.get('aws_region', 'us-east-1')
            client = boto3.client('secretsmanager', region_name=region)
            
            secret_name = self.config.get('secret_name', 'autoops-secrets')
            
            response = client.get_secret_value(SecretId=secret_name)
            secrets = json.loads(response['SecretString'])
            
            return secrets.get(key)
        except ImportError:
            logger.error("boto3 library not installed. Install with: pip install boto3")
            return None
        except Exception as e:
            logger.error(f"Failed to get secret from AWS: {e}")
            return None
    
    def _set_in_aws(self, key: str, value: str):
        """Set secret in AWS Secrets Manager"""
        try:
            import boto3
            
            region = self.config.get('aws_region', 'us-east-1')
            client = boto3.client('secretsmanager', region_name=region)
            
            secret_name = self.config.get('secret_name', 'autoops-secrets')
            
            # Get existing secrets
            try:
                response = client.get_secret_value(SecretId=secret_name)
                secrets = json.loads(response['SecretString'])
            except:
                secrets = {}
            
            # Update with new secret
            secrets[key] = value
            
            # Write back to AWS
            client.update_secret(
                SecretId=secret_name,
                SecretString=json.dumps(secrets)
            )
        except ImportError:
            logger.error("boto3 library not installed. Install with: pip install boto3")
            raise
        except Exception as e:
            logger.error(f"Failed to set secret in AWS: {e}")
            raise
    
    def _get_from_gcp(self, key: str) -> Optional[str]:
        """Get secret from Google Cloud Secret Manager"""
        try:
            from google.cloud import secretmanager
            
            project_id = self.config.get('gcp_project_id', os.getenv('GCP_PROJECT_ID'))
            if not project_id:
                raise Exception("GCP project ID not configured")
            
            client = secretmanager.SecretManagerServiceClient()
            
            secret_name = f"projects/{project_id}/secrets/{key}/versions/latest"
            
            response = client.access_secret_version(request={"name": secret_name})
            return response.payload.data.decode("UTF-8")
        except ImportError:
            logger.error("google-cloud-secret-manager library not installed. Install with: pip install google-cloud-secret-manager")
            return None
        except Exception as e:
            logger.error(f"Failed to get secret from GCP: {e}")
            return None
    
    def _set_in_gcp(self, key: str, value: str):
        """Set secret in Google Cloud Secret Manager"""
        try:
            from google.cloud import secretmanager
            
            project_id = self.config.get('gcp_project_id', os.getenv('GCP_PROJECT_ID'))
            if not project_id:
                raise Exception("GCP project ID not configured")
            
            client = secretmanager.SecretManagerServiceClient()
            
            parent = f"projects/{project_id}"
            
            # Create secret if it doesn't exist
            try:
                client.create_secret(
                    request={
                        "parent": parent,
                        "secret_id": key,
                        "secret": {"replication": {"automatic": {}}}
                    }
                )
            except Exception:
                # Secret already exists, which is fine
                pass
            
            # Add secret version
            secret_name = f"projects/{project_id}/secrets/{key}"
            client.add_secret_version(
                request={
                    "parent": secret_name,
                    "payload": {"data": value.encode("UTF-8")}
                }
            )
        except ImportError:
            logger.error("google-cloud-secret-manager library not installed. Install with: pip install google-cloud-secret-manager")
            raise
        except Exception as e:
            logger.error(f"Failed to set secret in GCP: {e}")
            raise
    
    def list_secrets(self) -> list:
        """List all available secret keys"""
        if self.backend == "env":
            return [key for key in os.environ.keys() if key.startswith(self.config.get('prefix', ''))]
        elif self.backend == "file":
            secrets_file = self.config.get('secrets_file', '.secrets.json')
            if not os.path.exists(secrets_file):
                return []
            try:
                with open(secrets_file, 'r') as f:
                    secrets = json.load(f)
                return list(secrets.keys())
            except Exception:
                return []
        else:
            # For cloud providers, implement specific listing logic
            return []
    
    def delete_secret(self, key: str):
        """Delete a secret"""
        if self.backend == "env":
            os.environ.pop(key, None)
        elif self.backend == "file":
            secrets_file = self.config.get('secrets_file', '.secrets.json')
            if os.path.exists(secrets_file):
                try:
                    with open(secrets_file, 'r') as f:
                        secrets = json.load(f)
                    secrets.pop(key, None)
                    with open(secrets_file, 'w') as f:
                        json.dump(secrets, f, indent=2)
                except Exception as e:
                    logger.error(f"Failed to delete secret from file: {e}")
        
        # Remove from cache
        self._cache.pop(key, None)
    
    def rotate_secret(self, key: str, new_value: str):
        """Rotate a secret value"""
        old_value = self.get_secret(key)
        self.set_secret(key, new_value)
        logger.info(f"Rotated secret '{key}'")
        return old_value
    
    def health_check(self) -> Dict[str, Any]:
        """Check the health of the secrets backend"""
        try:
            # Try to get a test secret
            test_key = "health_check_test"
            test_value = "test_value"
            
            self.set_secret(test_key, test_value)
            retrieved_value = self.get_secret(test_key)
            self.delete_secret(test_key)
            
            return {
                "status": "healthy",
                "backend": self.backend,
                "test_successful": retrieved_value == test_value,
                "cache_size": len(self._cache)
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "backend": self.backend,
                "error": str(e),
                "cache_size": len(self._cache)
            }


# Global secrets manager instance
_secrets_manager: Optional[SecretsManager] = None


def get_secrets_manager() -> SecretsManager:
    """Get the global secrets manager instance"""
    global _secrets_manager
    
    if _secrets_manager is None:
        # Initialize based on environment
        backend = os.getenv('SECRETS_BACKEND', 'env')
        
        config = {}
        if backend == 'file':
            config['secrets_file'] = os.getenv('SECRETS_FILE', '.secrets.json')
            config['encrypt'] = os.getenv('SECRETS_ENCRYPT', 'false').lower() == 'true'
        elif backend == 'vault':
            config['vault_url'] = os.getenv('VAULT_URL', 'http://localhost:8200')
            config['vault_token'] = os.getenv('VAULT_TOKEN')
            config['vault_path'] = os.getenv('VAULT_PATH', 'secret/autoops')
        elif backend == 'aws':
            config['aws_region'] = os.getenv('AWS_REGION', 'us-east-1')
            config['secret_name'] = os.getenv('AWS_SECRET_NAME', 'autoops-secrets')
        elif backend == 'gcp':
            config['gcp_project_id'] = os.getenv('GCP_PROJECT_ID')
        
        _secrets_manager = SecretsManager(backend=backend, **config)
    
    return _secrets_manager


def get_secret(key: str, default: Optional[str] = None) -> str:
    """Convenience function to get a secret"""
    return get_secrets_manager().get_secret(key, default)


def set_secret(key: str, value: str):
    """Convenience function to set a secret"""
    return get_secrets_manager().set_secret(key, value)


# Common secret keys
class SecretKeys:
    """Common secret key constants"""
    
    # Database
    DATABASE_URL = "DATABASE_URL"
    POSTGRES_PASSWORD = "POSTGRES_PASSWORD"
    
    # Redis
    REDIS_PASSWORD = "REDIS_PASSWORD"
    REDIS_URL = "REDIS_URL"
    
    # Authentication
    SECRET_KEY = "SECRET_KEY"
    JWT_SECRET = "JWT_SECRET"
    
    # External APIs
    OPENAI_API_KEY = "OPENAI_API_KEY"
    SLACK_WEBHOOK_URL = "SLACK_WEBHOOK_URL"
    TWILIO_AUTH_TOKEN = "TWILIO_AUTH_TOKEN"
    
    # Monitoring
    GRAFANA_ADMIN_PASSWORD = "GRAFANA_ADMIN_PASSWORD"
    
    # Cloud
    AWS_ACCESS_KEY_ID = "AWS_ACCESS_KEY_ID"
    AWS_SECRET_ACCESS_KEY = "AWS_SECRET_ACCESS_KEY"
    GCP_SERVICE_ACCOUNT_KEY = "GCP_SERVICE_ACCOUNT_KEY"