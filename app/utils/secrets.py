"""
Secret Management for AccessAI

Provides secure secret loading from environment variables and GCP Secret Manager.
In production on Cloud Run, secrets are injected as environment variables automatically.
"""

import os
from typing import Optional, Dict, Any

# Load .env file automatically for local development
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # If python-dotenv not installed, skip automatic loading
    pass

# Try to import GCP Secret Manager client for local development
# In production, secrets are already injected as env vars
try:
    from google.cloud import secretmanager
    _SECRET_MANAGER_AVAILABLE = True
except ImportError:
    _SECRET_MANAGER_AVAILABLE = False


class SecretManager:
    """
    Manage secrets from environment variables or GCP Secret Manager.

    Priority:
    1. Environment variable (for Cloud Run - secrets are injected)
    2. GCP Secret Manager (for local development with application-default login)
    3. Fallback to None (raise error if required)
    """

    def __init__(self, project_id: Optional[str] = None):
        """
        Initialize secret manager.

        Args:
            project_id: GCP project ID. Auto-detected if not provided.
        """
        self.project_id = project_id or os.getenv('GOOGLE_CLOUD_PROJECT')
        self._client = None

    def _get_client(self):
        """Lazy initialization of Secret Manager client."""
        if self._client is None and _SECRET_MANAGER_AVAILABLE and self.project_id:
            try:
                self._client = secretmanager.SecretManagerServiceClient()
            except Exception:
                self._client = None
        return self._client

    def get_secret(
        self,
        secret_name: str,
        fallback: Optional[str] = None,
        required: bool = False
    ) -> Optional[str]:
        """
        Get a secret value.

        Args:
            secret_name: Name of the secret (matches GCP Secret Manager secret ID)
            fallback: Fallback value if secret not found
            required: If True, raise error when secret not found

        Returns:
            Secret value or fallback/None

        Raises:
            ValueError: If required secret not found
        """
        # Priority 1: Environment variable (Cloud Run injects secrets here)
        env_value = os.getenv(secret_name)
        if env_value is not None:
            return env_value

        # Priority 2: GCP Secret Manager (for local development)
        client = self._get_client()
        if client and self.project_id:
            try:
                name = f"projects/{self.project_id}/secrets/{secret_name}/versions/latest"
                response = client.access_secret_version(request={"name": name})
                return response.payload.data.decode("UTF-8")
            except Exception:
                pass  # Fall through to fallback

        # Priority 3: Fallback or error
        if required:
            raise ValueError(f"Required secret '{secret_name}' not found")

        return fallback

    def get_all_secrets(self, secret_names: list) -> Dict[str, str]:
        """
        Get multiple secrets at once.

        Args:
            secret_names: List of secret names

        Returns:
            Dictionary of secret_name: value
        """
        return {name: self.get_secret(name) for name in secret_names}


# Global secret manager instance
_secret_manager = None


def get_secret_manager() -> SecretManager:
    """Get or create global secret manager instance."""
    global _secret_manager
    if _secret_manager is None:
        _secret_manager = SecretManager()
    return _secret_manager


def get_secret(secret_name: str, fallback: Optional[str] = None, required: bool = False) -> Optional[str]:
    """
    Convenience function to get a secret.

    Args:
        secret_name: Name of the secret
        fallback: Fallback value
        required: If True, raise error when not found

    Returns:
        Secret value
    """
    return get_secret_manager().get_secret(secret_name, fallback, required)


# =============================================================================
# AccessAI Specific Secrets
# =============================================================================

def get_google_cloud_project() -> Optional[str]:
    """Get Google Cloud Project ID."""
    return get_secret('GOOGLE_CLOUD_PROJECT')


def get_google_cloud_location() -> str:
    """Get Google Cloud Location/Region."""
    return get_secret('GOOGLE_CLOUD_LOCATION', fallback='asia-south1')


def get_google_maps_api_key() -> Optional[str]:
    """Get Google Maps API Key."""
    return get_secret('GOOGLE_MAPS_API_KEY')


def get_encryption_key() -> Optional[str]:
    """Get encryption key for health data."""
    return get_secret('ENCRYPTION_KEY')


def get_emergency_contact_email() -> Optional[str]:
    """Get emergency contact email."""
    return get_secret('EMERGENCY_CONTACT_EMAIL')


def get_emergency_contact_phone() -> Optional[str]:
    """Get emergency contact phone."""
    return get_secret('EMERGENCY_CONTACT_PHONE')


def get_tts_voice() -> str:
    """Get TTS voice configuration."""
    return get_secret('TTS_VOICE', fallback='en-US-Neural2-F')


def get_tts_speed() -> float:
    """Get TTS speed configuration."""
    try:
        return float(get_secret('TTS_SPEED', fallback='1.0'))
    except ValueError:
        return 1.0


# =============================================================================
# Helper: Check all required secrets are available
# =============================================================================

def check_secrets_health() -> Dict[str, Any]:
    """
    Check which secrets are available.

    Returns:
        Dictionary with secret availability status
    """
    secrets_to_check = {
        'GOOGLE_CLOUD_PROJECT': ('Google Cloud Project', False),
        'GOOGLE_CLOUD_LOCATION': ('Google Cloud Location', False),
        'GOOGLE_MAPS_API_KEY': ('Google Maps API', True),
        'ENCRYPTION_KEY': ('Encryption Key', False),
        'EMERGENCY_CONTACT_EMAIL': ('Emergency Email', True),
        'EMERGENCY_CONTACT_PHONE': ('Emergency Phone', True),
    }

    status = {}
    missing = []

    for secret_name, (description, is_optional) in secrets_to_check.items():
        value = get_secret(secret_name)
        available = value is not None
        status[secret_name] = {
            'available': available,
            'description': description
        }
        if not available and not is_optional:
            missing.append(description)

    return {
        'all_ready': len(missing) == 0,
        'missing_secrets': missing,
        'secret_status': status
    }


if __name__ == '__main__':
    # Test secret loading
    print("\n=== AccessAI Secret Manager Health Check ===\n")
    health = check_secrets_health()

    for secret_name, info in health['secret_status'].items():
        status = '✓' if info['available'] else '✗'
        print(f"  {status} {info['description']} ({secret_name})")

    if health['missing_secrets']:
        print(f"\n⚠️  Missing required secrets: {', '.join(health['missing_secrets'])}")
    else:
        print("\n✅ All secrets configured!")