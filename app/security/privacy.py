"""
Privacy controls for AccessAI.

Implements data minimization, consent management, and privacy policies.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from enum import Enum


class DataCategory(Enum):
    """Categories of user data for privacy classification."""
    HEALTH = "health"
    LOCATION = "location"
    COMMUNICATION = "communication"
    DIAGNOSTIC = "diagnostic"
    PREFERENCE = "preference"


class ConsentLevel(Enum):
    """User consent levels for data processing."""
    REQUIRED = "required"  # Essential for service
    OPTIONAL = "optional"  # User can opt out
    ANALYTICS = "analytics"  # Only with explicit consent


# Privacy policy configuration
PRIVACY_SETTINGS = {
    DataCategory.HEALTH: {
        'consent_level': ConsentLevel.REQUIRED,
        'retention_days': 365,
        'encryption_required': True,
        'shares_with_third_parties': False
    },
    DataCategory.LOCATION: {
        'consent_level': ConsentLevel.OPTIONAL,
        'retention_days': 30,
        'encryption_required': True,
        'shares_with_third_parties': False
    },
    DataCategory.DIAGNOSTIC: {
        'consent_level': ConsentLevel.ANALYTICS,
        'retention_days': 90,
        'encryption_required': False,
        'shares_with_third_parties': False
    }
}


class PrivacyManager:
    """Manages user privacy settings and data consent."""

    def __init__(self, user_id: str):
        """Initialize privacy manager for user.

        Args:
            user_id: Unique user identifier
        """
        self.user_id = user_id
        self.consent_records: Dict[str, bool] = {}
        self.data_access_log: List[Dict] = []

    def get_consent(self, category: DataCategory) -> bool:
        """Get user consent status for data category.

        Args:
            category: Data category to check

        Returns:
            True if consent granted, False otherwise
        """
        consent_key = f"{self.user_id}_{category.value}"
        return self.consent_records.get(consent_key, False)

    def request_consent(
        self,
        category: DataCategory,
        purpose: str,
        optional: bool = True
    ) -> Dict[str, any]:
        """Request user consent for data processing.

        Args:
            category: Data category
            purpose: Purpose of data collection
            optional: Whether consent is optional

        Returns:
            Consent request details
        """
        return {
            'category': category.value,
            'purpose': purpose,
            'required': not optional,
            'retention_days': PRIVACY_SETTINGS[category]['retention_days'],
            'timestamp': datetime.now().isoformat()
        }

    def grant_consent(self, category: DataCategory) -> bool:
        """Record user consent for data category.

        Args:
            category: Data category

        Returns:
            Confirmation of consent
        """
        consent_key = f"{self.user_id}_{category.value}"
        self.consent_records[consent_key] = True

        # Log consent
        self.data_access_log.append({
            'action': 'consent_granted',
            'category': category.value,
            'timestamp': datetime.now().isoformat()
        })

        return True

    def revoke_consent(self, category: DataCategory) -> bool:
        """Revoke user consent for data category.

        Args:
            category: Data category

        Returns:
            Confirmation of revocation
        """
        consent_key = f"{self.user_id}_{category.value}"
        self.consent_records[consent_key] = False

        self.data_access_log.append({
            'action': 'consent_revoked',
            'category': category.value,
            'timestamp': datetime.now().isoformat()
        })

        return True

    def get_data_retention_deadline(self, category: DataCategory) -> datetime:
        """Get when data of a category should be deleted.

        Args:
            category: Data category

        Returns:
            Retention deadline
        """
        retention_days = PRIVACY_SETTINGS[category]['retention_days']
        return datetime.now() + timedelta(days=retention_days)

    def logs_access_history(self, limit: int = 100) -> List[Dict]:
        """Get user's data access history.

        Args:
            limit: Maximum entries to return

        Returns:
            List of access log entries
        """
        return self.data_access_log[-limit:]

    def export_user_data(self) -> Dict[str, any]:
        """Export all user data in portable format.

        Returns:
            User data export
        """
        return {
            'user_id': self.user_id,
            'consent_status': self.consent_records,
            'access_history': self.logs_access_history(),
            'exported_at': datetime.now().isoformat(),
            'format_version': '1.0'
        }

    def delete_all_data(self) -> Dict[str, any]:
        """Delete all user data (right to be forgotten).

        Returns:
            Deletion confirmation
        """
        self.consent_records.clear()
        self.data_access_log.clear()

        return {
            'status': 'deleted',
            'user_id': self.user_id,
            'deleted_at': datetime.now().isoformat()
        }


def anonymize_data(data: Dict, fields_to_anonymize: List[str]) -> Dict:
    """Anonymize specific fields in user data.

    Args:
        data: Data dictionary
        fields_to_anonymize: List of field names to anonymize

    Returns:
        Anonymized data
    """
    anonymized = data.copy()

    for field in fields_to_anonymize:
        if field in anonymized:
            anonymized[field] = f"[REDACTED: {field}]"

    return anonymized


def get_privacy_compliance_report(user_id: str) -> Dict[str, any]:
    """Generate GDPR/privacy compliance report.

    Args:
        user_id: User identifier

    Returns:
        Compliance report
    """
    manager = PrivacyManager(user_id)

    return {
        'user_id': user_id,
        'report_generated': datetime.now().isoformat(),
        'consent_status': {
            category.value: manager.get_consent(category)
            for category in DataCategory
        },
        'data_categories_stored': [
            category.value
            for category in DataCategory
            if manager.get_consent(category)
        ],
        'retention_policies': {
            category.value: settings['retention_days']
            for category, settings in PRIVACY_SETTINGS.items()
        },
        'third_party_sharing': False
    }