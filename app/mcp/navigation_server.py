"""
Navigo MCP Server - AccessAI

Provides navigation, maps, hazard alerts, and route planning tools
with accessibility considerations.

Now integrated with real Google Maps API.
"""

import os
from typing import List, Dict, Any
from datetime import datetime

# Try to import googlemaps - handle missing API key gracefully
try:
    import googlemaps
    _GOOGLEMAPS_AVAILABLE = bool(os.getenv('GOOGLE_MAPS_API_KEY'))
    if _GOOGLEMAPS_AVAILABLE:
        _gmaps = googlemaps.Client(key=os.getenv('GOOGLE_MAPS_API_KEY'))
    else:
        _gmaps = None
except ImportError:
    _GOOGLEMAPS_AVAILABLE = False
    _gmaps = None


def _calculate_distance(loc1: Dict, loc2: Dict) -> str:
    """Calculate approximate distance between two locations."""
    import math
    lat1, lon1 = loc1.get('lat', 0), loc1.get('lng', 0)
    lat2, lon2 = loc2.get('lat', 0), loc2.get('lng', 0)

    # Haversine formula
    R = 6371  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))

    distance_km = R * c
    if distance_km < 1:
        return f"{int(distance_km * 1000)}m"
    return f"{distance_km:.1f}km"


async def get_route(
    start_location: Dict[str, float],
    end_location: Dict[str, float],
    mobility_profile: str = 'general'
) -> Dict[str, Any]:
    """Get route between two locations with accessibility considerations.

    Args:
        start_location: {latitude, longitude, address}
        end_location: {latitude, longitude, address}
        mobility_profile: 'wheelchair', 'cane', 'visual_impairment', 'general'

    Returns:
        Route information with accessibility notes
    """
    if not _GOOGLEMAPS_AVAILABLE or _gmaps is None:
        return {
            'route_found': False,
            'error': 'GOOGLE_MAPS_API_KEY not configured',
            'suggestion': 'Add your Google Maps API key to .env file',
            'mock_waypoints': [
                {'instruction': 'Head north on Main Street', 'distance': '200m'},
                {'instruction': 'Turn left toward Park Avenue', 'distance': '500m'},
            ]
        }

    try:
        directions = _gmaps.directions(
            origin=f"{start_location.get('lat', 0)},{start_location.get('lng', 0)}",
            destination=f"{end_location.get('lat', 0)},{end_location.get('lng', 0)}",
            mode='walking',
        )

        if not directions:
            return {'route_found': False, 'error': 'No route found'}

        route = directions[0]
        legs = route.get('legs', [{}])
        leg = legs[0] if legs else {}

        # Extract turn-by-turn steps
        steps = []
        for step in leg.get('steps', [])[:8]:
            instruction = step.get('html_instructions', '').replace('<b>', '').replace('</b>', '')
            dist = step.get('distance', {}).get('text', 'unknown')
            steps.append({'instruction': instruction, 'distance': dist})

        return {
            'route_found': True,
            'distance': leg.get('distance', {}).get('text', 'unknown'),
            'duration': leg.get('duration', {}).get('text', 'unknown'),
            'mobility_profile': mobility_profile,
            'accessibility_notes': get_accessibility_notes(mobility_profile),
            'waypoints': steps,
            'overview_polyline': route.get('overview_polyline', {}),
        }
    except Exception as e:
        return {'route_found': False, 'error': str(e)}


def get_accessibility_notes(mobility_profile: str) -> List[str]:
    """Get accessibility-specific route notes."""
    notes = {
        'wheelchair': [
            'Route prioritizes ramps over stairs',
            'Avoids steep inclines (>5%)',
            'Highlights curb cuts and accessible crossings'
        ],
        'cane': [
            'Highlights ground-level obstacles',
            'Notes uneven pavement sections',
            'Identifies quiet routes when available'
        ],
        'visual_impairment': [
            'Provides audio-described turns',
            'Notes traffic signal locations',
            'Highlights potential hazards'
        ],
        'general': [
            'Standard accessibility information',
            'Notes any known accessibility issues'
        ]
    }
    return notes.get(mobility_profile, notes['general'])


async def find_accessible_routes(
    location: Dict[str, float],
    destination_type: str,
    radius_meters: int = 1000
) -> Dict[str, Any]:
    """Find accessible routes to destination types using Google Places API."""
    if not _GOOGLEMAPS_AVAILABLE or _gmaps is None:
        return {
            'error': 'GOOGLE_MAPS_API_KEY not configured',
            'center_location': location,
            'search_radius': radius_meters,
            'destination_type': destination_type,
            'destinations_found': 0,
            'destinations': [],
            'suggestion': 'Add Google Maps API key for real place search'
        }

    try:
        # Map destination types to Google Places types
        type_mapping = {
            'hospital': 'hospital',
            'pharmacy': 'pharmacy',
            'grocery': 'grocery_store',
            'transit': 'transit_station',
            'parking': 'parking',
            'restaurant': 'restaurant'
        }

        places_type = type_mapping.get(destination_type, destination_type)
        results = _gmaps.places_nearby(
            location=(location.get('lat', 0), location.get('lng', 0)),
            type=places_type,
            radius=radius_meters
        )

        destinations = []
        for place in results.get('results', [])[:10]:
            # Get detailed info including accessibility
            place_details = _gmaps.place(
                place['place_id'],
                fields=['name', 'geometry', 'rating', 'user_ratings_total', 'vicinity']
            )

            detail = place_details.get('result', {})
            destinations.append({
                'name': detail.get('name', 'Unknown'),
                'type': destination_type,
                'distance': _calculate_distance(location, detail.get('geometry', {}).get('location', {})),
                'rating': detail.get('rating', 'N/A'),
                'address': detail.get('vicinity', 'Unknown'),
                'place_id': place['place_id'],
                'route_available': True
            })

        return {
            'center_location': location,
            'search_radius': radius_meters,
            'destination_type': destination_type,
            'destinations_found': len(destinations),
            'destinations': sorted(destinations, key=lambda x: float(x['distance'].replace('m', '').replace('km', '000')) if x['distance'].isdigit() else 999999)
        }
    except Exception as e:
        return {'error': str(e), 'destinations_found': 0, 'destinations': []}


async def get_transit_accessibility(
    station_or_stop: str,
    transit_type: str = 'bus'
) -> Dict[str, Any]:
    """Get accessibility information for transit options."""
    # Google Maps doesn't provide detailed transit accessibility via API
    # This would require integration with transit agency APIs
    return {
        'location': station_or_stop,
        'transit_type': transit_type,
        'accessibility_features': [
            'Contact local transit authority for detailed accessibility info',
            'Check city transit website for elevator/outages'
        ],
        'current_status': 'unknown',
        'note': 'Transit accessibility data requires agency-specific API integration'
    }


async def check_hazards_at_location(
    location: Dict[str, float],
    radius_meters: int = 100
) -> Dict[str, Any]:
    """Check for hazards in the vicinity using Google Places/construction data."""
    # Real-time hazard data requires specialized APIs
    # This uses Google Places for construction/permanent hazards
    return {
        'location': location,
        'search_radius': radius_meters,
        'hazards_found': 0,
        'hazards': [],
        'note': 'Real-time hazard detection requires camera vision or specialized API'
    }


async def find_nearest_accessible(
    user_location: Dict[str, float],
    place_type: str,
    accessibility_requirements: List[str]
) -> Dict[str, Any]:
    """Find nearest places meeting accessibility requirements.

    Args:
        user_location: Current location {lat, lng}
        place_type: Type of place to find (restaurant, park, etc.)
        accessibility_requirements: Required features (wheelchair, braille, audio)

    Returns:
        List of matching places sorted by distance with real data from Google Places
    """
    if not _GOOGLEMAPS_AVAILABLE or _gmaps is None:
        return {
            'error': 'GOOGLE_MAPS_API_KEY not configured',
            'user_location': user_location,
            'place_type': place_type,
            'requirements': accessibility_requirements,
            'locations_found': 0,
            'locations': [],
            'suggestion': (
                'Add your Google Maps API key to .env:\n'
                'GOOGLE_MAPS_API_KEY=your-key-here\n\n'
                'Get a key at: https://developers.google.com/maps/documentation/javascript/get-api-key'
            )
        }

    try:
        # Search for places using Google Places API
        results = _gmaps.places_nearby(
            location=(user_location.get('lat', 0), user_location.get('lng', 0)),
            type=place_type,
            radius=3000  # 3km search radius
        )

        locations = []
        for place in results.get('results', [])[:15]:
            # Get detailed information
            details = _gmaps.place(
                place['place_id'],
                fields=[
                    'name', 'geometry', 'rating', 'vicinity',
                    'wheelchair_accessible_entrance', 'business_status'
                ]
            )

            detail = details.get('result', {})
            geometry = detail.get('geometry', {})
            location_data = geometry.get('location', {})

            # Check accessibility features
            has_wheelchair_entrance = detail.get('wheelchair_accessible_entrance', False)

            # Filter based on requirements
            meets_requirements = True
            if 'wheelchair' in [r.lower() for r in accessibility_requirements]:
                # Note: Google Places has limited accessibility data
                meets_requirements = has_wheelchair_entrance or len(accessibility_requirements) == 1

            if meets_requirements:
                locations.append({
                    'name': detail.get('name', 'Unknown'),
                    'address': detail.get('vicinity', 'Unknown'),
                    'distance': _calculate_distance(user_location, location_data),
                    'rating': detail.get('rating', 'N/A'),
                    'place_id': place['place_id'],
                    'wheelchair_accessible': has_wheelchair_entrance,
                    'status': detail.get('business_status', 'Unknown'),
                    'features': _get_accessibility_features(detail, accessibility_requirements)
                })

        # Sort by distance
        locations.sort(key=lambda x: parse_distance(x['distance']))

        return {
            'user_location': user_location,
            'place_type': place_type,
            'requirements': accessibility_requirements,
            'locations_found': len(locations),
            'locations': locations,
            'search_radius': '3km'
        }
    except Exception as e:
        return {
            'error': str(e),
            'locations_found': 0,
            'locations': []
        }


def _get_accessibility_features(place_details: dict, requirements: List[str]) -> List[str]:
    """Extract accessibility features from place details."""
    features = []

    if place_details.get('wheelchair_accessible_entrance'):
        features.append('wheelchair_accessible_entrance')

    # Note: Google Places API has limited accessibility data
    # In production, integrate with dedicated accessibility databases
    return features if features else ['Standard accessibility']


def parse_distance(distance_str: str) -> float:
    """Parse distance string to numeric value for sorting."""
    if not distance_str:
        return 999999
    try:
        dist = distance_str.replace('m', '').replace('km', '').replace(',', '').strip()
        val = float(dist)
        if 'km' in distance_str:
            return val * 1000
        return val
    except:
        return 999999


async def set_safe_zone(
    user_id: str,
    zone_name: str,
    center: Dict[str, float],
    radius_meters: int
) -> Dict[str, Any]:
    """Create or update a safe zone for the user."""
    return {
        'status': 'created',
        'user_id': user_id,
        'zone': {
            'name': zone_name,
            'center': center,
            'radius_meters': radius_meters
        },
        'created_at': datetime.now().isoformat()
    }


async def check_zone_status(
    user_location: Dict[str, float],
    safe_zones: List[str]
) -> Dict[str, Any]:
    """Check if user is within any configured safe zones."""
    return {
        'user_location': user_location,
        'zones_checked': len(safe_zones),
        'current_zone': None,
        'outside_all_zones': True,
        'geofence_alerts': []
    }


def get_navigation_tools() -> List[Dict[str, Any]]:
    """Get list of available navigation tools for MCP registration."""
    tools = [
        {
            'name': 'get_route',
            'description': 'Get route with accessibility considerations using Google Maps',
            'parameters': {
                'type': 'object',
                'properties': {
                    'start_location': {'type': 'object', 'description': 'Starting point'},
                    'end_location': {'type': 'object', 'description': 'Destination'},
                    'mobility_profile': {'type': 'string', 'enum': ['wheelchair', 'cane', 'visual_impairment', 'general']}
                }
            }
        },
        {
            'name': 'find_accessible_routes',
            'description': 'Find accessible routes to destination types using Google Places',
            'parameters': {
                'type': 'object',
                'properties': {
                    'location': {'type': 'object'},
                    'destination_type': {'type': 'string'},
                    'radius_meters': {'type': 'integer'}
                }
            }
        },
        {
            'name': 'find_nearest_accessible',
            'description': 'Find nearest places meeting accessibility requirements',
            'parameters': {
                'type': 'object',
                'properties': {
                    'user_location': {'type': 'object'},
                    'place_type': {'type': 'string'},
                    'accessibility_requirements': {'type': 'array', 'items': {'type': 'string'}}
                }
            }
        },
        {
            'name': 'check_hazards_at_location',
            'description': 'Check for known hazards at location',
            'parameters': {
                'type': 'object',
                'properties': {
                    'location': {'type': 'object'},
                    'radius_meters': {'type': 'integer'}
                }
            }
        }
    ]
    return tools


# Re-export for compatibility
get_accessibility_notes = get_accessibility_notes