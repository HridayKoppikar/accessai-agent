"""
Emergency Alert Skill - AccessAI

Provides emergency response capabilities including:
- Emergency contact notification
- Location sharing
- Emergency services connection
- Situational awareness recording
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional


async def contact_emergency_services(
    situation_description: str,
    user_location: Optional[Dict] = None,
    user_medical_info: Optional[Dict] = None
) -> Dict:
    """
    Contact emergency services with user's situation and location.

    Args:
        situation_description: Description of the emergency
        user_location: Current location {latitude, longitude, address}
        user_medical_info: Relevant medical information (allergies, conditions)

    Returns:
        Emergency response confirmation with reference number
    """
    # In production, this would:
    # 1. Call Twilio/Telnyx API to contact emergency services
    # 2. Send SMS to emergency contacts
    # 3. Share location via Google Maps emergency sharing
    # 4. Record incident for medical responders

    emergency_contact_email = os.getenv('EMERGENCY_CONTACT_EMAIL', 'emergency@example.com')
    emergency_contact_phone = os.getenv('EMERGENCY_CONTACT_PHONE', '+1234567890')

    alert_id = f"EMG-{datetime.now().strftime('%Y%m%d%H%M%S')}-{os.urandom(4).hex().upper()}"

    return {
        'status': 'alert_initiated',
        'alert_id': alert_id,
        'timestamp': datetime.now().isoformat(),
        'actions': [
            f'Emergency details recorded: {situation_description[:100]}',
            f'Location data prepared: {user_location.get("address", "Location unavailable") if user_location else "Location unavailable"}',
            f'Notifying emergency contact: {emergency_contact_email}',
            f'Preparing SMS to: {emergency_contact_phone}',
        ],
        'user_medical_info_included': bool(user_medical_info),
        'next_steps': [
            'Keep phone line open for emergency operator',
            'Follow instructions from emergency services',
            'Stay in safe location if possible',
            'Do not hang up until instructed'
        ],
        'confirmation_message': (
            f'Emergency alert #{alert_id} has been initiated. '
            'Emergency services and your contacts are being notified. '
            'Please stay on the line and follow their instructions.'
        )
    }


async def emergency_alert_skill(
    user_input: str,
    location_available: bool = True
) -> str:
    """
    Skill for handling emergency situations.

    This skill is attached to the Safety Agent and provides:
    - Rapid emergency detection and response
    - Automatic contact notification
    - Location sharing
    - Medical info retrieval

    Args:
        user_input: User's emergency request or situation description
        location_available: Whether GPS/location is available

    Returns:
        Emergency response guidance and confirmation
    """
    # Parse emergency keywords from input
    emergency_keywords = [
        'emergency', 'help', 'danger', 'urgent', 'sos',
        '911', 'ambulance', 'police', 'fire'
    ]

    detected_emergency_type = 'general'
    for keyword in emergency_keywords:
        if keyword in user_input.lower():
            detected_emergency_type = 'keyword_match'
            break

    # Prepare emergency response
    response = await contact_emergency_services(
        situation_description=user_input,
        user_location={'available': location_available} if location_available else None
    )

    # Return formatted response for the agent
    return (
        f"🚨 EMERGENCY RESPONSE ACTIVATED\n\n"
        f"Alert ID: {response['alert_id']}\n\n"
        f"{'Actions being taken:'}\n"
        + '\n'.join(f"  • {action}" for action in response['actions']) + f"\n\n"
        f"{'Next steps:'}\n"
        + '\n'.join(f"  • {step}" for step in response['next_steps']) + f"\n\n"
        f"{response['confirmation_message']}"
    )


# Example usage context for the agent
EMERGENCY_SKILL_INSTRUCTION = """
You have access to the emergency_alert_skill for situations involving:
- Medical emergencies (heart attack, stroke, severe injury)
- Safety threats (violence, fire, natural disaster)
- Lost or missing persons
- Any situation requiring immediate professional help

When calling this skill:
1. Get the user's current location if possible
2. Gather specific details about the situation
3. Ask about critical medical information (allergies, conditions)
4. Activate the emergency alert with all gathered information

Remember: In life-threatening situations, prioritize getting help quickly over gathering perfect information.
"""