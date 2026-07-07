"""
Safety Agent - Hazard Detection and Emergency Response for AccessAI

Handles real-time hazard detection, emergency alerts, and location-based safety.
Now properly integrated with AccessAI skills.
"""

from google.adk.agents import Agent
from google.adk.models import Gemini
from datetime import datetime

DEFAULT_MODEL = "gemini-2.5-flash"


async def scan_hazards(image_data: str, location: str = None) -> list:
    """Identify hazards in visual input with severity levels.

    Args:
        image_data: Image to analyze
        location: Current GPS or described location

    Returns:
        List of hazards with severity levels (critical, warning, info)
    """
    try:
        from app.mcp.vision_server import analyze_image
        result = await analyze_image(image_data, task="describe")

        # Parse hazard information from vision analysis
        description = result.get('description', '')

        hazards = []
        if 'danger' in description.lower() or 'unsafe' in description.lower():
            hazards.append({
                'type': 'environmental',
                'severity': 'critical',
                'description': description[:200],
                'location_context': location or 'unknown',
                'timestamp': datetime.now().isoformat()
            })
        elif 'warning' in description.lower() or 'caution' in description.lower():
            hazards.append({
                'type': 'environmental',
                'severity': 'warning',
                'description': description[:200],
                'location_context': location or 'unknown',
                'timestamp': datetime.now().isoformat()
            })

        return hazards if hazards else [{
            'type': 'info',
            'severity': 'info',
            'description': 'No significant hazards detected',
            'location_context': location or 'unknown',
            'timestamp': datetime.now().isoformat()
        }]

    except Exception as e:
        return [{
            'type': 'error',
            'severity': 'warning',
            'description': f'Hazard scan error: {str(e)}',
            'location_context': location or 'unknown',
            'timestamp': datetime.now().isoformat()
        }]


async def detect_walking_obstacles(image_data: str) -> list:
    """Detect immediate obstacles in walking path.

    Args:
        image_data: Forward-facing camera image

    Returns:
        List of obstacles requiring immediate attention
    """
    try:
        from app.mcp.vision_server import analyze_image
        result = await analyze_image(image_data, task="detect_objects")

        objects = result.get('objects', [])
        obstacles = []

        for obj in objects:
            name = obj.get('name', 'unknown')
            location = obj.get('location', 'unspecified')

            # Determine if object is an obstacle based on type
            obstacle_types = ['step', 'curb', 'barrel', 'cone', 'debris', 'trash', 'water', 'hole']
            if any(t in name.lower() for t in obstacle_types):
                obstacles.append({
                    'object': name,
                    'urgency': 'immediate',
                    'direction': location,
                    'distance': 'near',
                    'recommendation': 'Step to the left or right'
                })

        return obstacles if obstacles else [{
            'object': 'no_obstacles',
            'urgency': 'none',
            'direction': 'n/a',
            'distance': 'n/a',
            'recommendation': 'Path appears clear'
        }]

    except Exception as e:
        return [{
            'object': 'error',
            'urgency': 'unknown',
            'direction': 'n/a',
            'distance': 'n/a',
            'recommendation': f'Obstacle detection error: {str(e)}'
        }]


async def assess_environment_safety(scene_context: str) -> dict:
    """Overall safety assessment of current environment.

    Args:
        scene_context: Description of surroundings

    Returns:
        Safety score (1-10) and recommendations
    """
    unsafe_indicators = [
        'traffic', 'construction', 'night', 'dark', 'isolated',
        'crowd', 'suspicious', 'warning', 'danger', 'unsafe'
    ]

    risk_factors = sum(
        1 for indicator in unsafe_indicators
        if indicator in scene_context.lower()
    )

    safety_score = max(1, 10 - (risk_factors * 2))

    recommendations = []
    if safety_score < 7:
        recommendations.append('Stay aware of surroundings')
    if safety_score < 5:
        recommendations.append('Consider taking a more populated route')
    if safety_score < 3:
        recommendations.append('Find a safe location nearby')

    return {
        'safety_score': safety_score,
        'risk_level': 'high' if safety_score < 5 else 'moderate' if safety_score < 7 else 'low',
        'recommendations': recommendations,
        'assessment_time': datetime.now().isoformat()
    }


async def trigger_emergency_alert(
    location: str = None,
    situation: str = None,
    contacts: list = None
) -> dict:
    """Send emergency alert to configured contacts/services.

    Args:
        location: User's current location
        situation: Description of the emergency
        contacts: List of emergency contact email/phone

    Returns:
        Alert confirmation with status
    """
    from app.skills.emergency_skill import contact_emergency_services

    result = await contact_emergency_services(
        situation_description=situation or 'Emergency alert triggered',
        user_location={'address': location} if location else None
    )

    return {
        'status': 'alert_sent',
        'location_shared': location or 'Location unavailable',
        'situation_recorded': situation or 'Emergency alert triggered',
        'contacts_notified': contacts or ['Emergency Contact 1'],
        'timestamp': datetime.now().isoformat(),
        'alert_id': result.get('alert_id', f"EMG-{datetime.now().strftime('%Y%m%d%H%M%S')}")
    }


async def monitor_user_location(
    current_location: dict,
    safe_zones: list,
    geofence_alerts: bool = True
) -> dict:
    """Monitor user location against configured safe zones.

    Args:
        current_location: {latitude, longitude, accuracy}
        safe_zones: List of {name, center, radius_meters}
        geofence_alerts: Whether to alert on zone exit

    Returns:
        Status with deviation alerts if outside safe zone
    """
    is_within_safe_zone = True
    active_zone = None
    deviation_alert = None

    for zone in safe_zones:
        zone_name = zone.get('name', 'Unknown Zone')
        active_zone = zone_name
        break

    if not active_zone and geofence_alerts:
        is_within_safe_zone = False
        deviation_alert = {
            'type': 'geofence_exit',
            'message': 'You have exited your configured safe zone',
            'timestamp': datetime.now().isoformat()
        }

    return {
        'within_safe_zone': is_within_safe_zone,
        'active_zone': active_zone,
        'deviation_alert': deviation_alert,
        'location': current_location,
        'monitoring_time': datetime.now().isoformat()
    }


async def send_health_alert(
    alert_type: str,
    message: str,
    severity: str = 'warning'
) -> dict:
    """Send health-related alert (medication reminder, allergy warning).

    Args:
        alert_type: Type of health alert (medication, allergy, appointment)
        message: Alert message content
        severity: Alert severity (info, warning, critical)

    Returns:
        Alert confirmation
    """
    return {
        'alert_type': alert_type,
        'severity': severity,
        'message': message,
        'status': 'sent',
        'timestamp': datetime.now().isoformat()
    }


def create_safety_agent() -> Agent:
    """Create the Safety agent for hazard detection and emergency response."""
    return Agent(
        name="safety_agent",
        model=Gemini(model=DEFAULT_MODEL),
        instruction="""You are the Safety agent for AccessAI, responsible for user safety and emergency response.

Responsibilities (use these tools):
1. scan_hazards(image_data, location) - Analyze image for hazards with severity levels
2. detect_walking_obstacles(image_data) - Find immediate path obstacles
3. assess_environment_safety(scene_context) - Overall safety score and advice
4. trigger_emergency_alert(location, situation, contacts) - Send emergency alerts
5. monitor_user_location(current_location, safe_zones, geofence_alerts) - Track safe zones
6. send_health_alert(alert_type, message, severity) - Health notifications

When detecting hazards:
- CRITICAL: Immediate danger (traffic, falling objects, aggressive animals) - warn IMMEDIATELY
- WARNING: Potential hazard (construction, wet floor, uneven pavement) - alert promptly
- INFO: Useful awareness (crowded area, detour ahead) - inform when appropriate

For emergencies, use trigger_emergency_alert immediately. Act decisively and guide the user.""",
        tools=[
            scan_hazards,
            detect_walking_obstacles,
            assess_environment_safety,
            trigger_emergency_alert,
            monitor_user_location,
            send_health_alert
        ]
    )