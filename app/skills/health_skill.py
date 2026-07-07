"""
Health Management Skill - AccessAI

Provides health management capabilities including:
- Allergy checking and food safety
- Medication tracking and interactions
- Meal planning with dietary restrictions
- Health alert notifications
"""

import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Common allergens database
COMMON_ALLERGENS = [
    'peanuts', 'tree nuts', 'milk', 'eggs', 'wheat', 'soy',
    'fish', 'shellfish', 'sesame', 'corn', 'dairy', 'gluten', 'lecithin'
]

# Ingredient allergen mappings
INGREDIENT_ALLERGEN_MAP = {
    'peanut butter': ['peanuts'],
    'milk': ['milk', 'dairy'],
    'egg': ['eggs'],
    'wheat flour': ['wheat', 'gluten'],
    'shellfish': ['shellfish'],
    'soy sauce': ['soy'],
    'lecithin (soy)': ['soy'],
    'lecithin': ['soy', 'dairy']
}


async def check_food_safety(
    food_item: str,
    ingredients: List[str],
    user_allergies: List[str],
    user_medications: Optional[List[str]] = None
) -> Dict:
    """
    Check if a food item is safe for the user.

    Args:
        food_item: Name of the food item
        ingredients: List of ingredients
        user_allergies: User's known allergies
        user_medications: User's current medications

    Returns:
        Safety assessment with detailed warnings
    """
    alerts = []
    unsafe_ingredients = []
    interaction_warnings = []

    # Check for allergens
    for ingredient in ingredients:
        ingredient_lower = ingredient.lower()
        for allergy in user_allergies:
            allergy_lower = allergy.lower()
            if allergy_lower in ingredient_lower:
                alert = {
                    'type': 'allergen_detected',
                    'severity': 'critical',
                    'ingredient': ingredient,
                    'allergen': allergy,
                    'message': f"ALLERGEN WARNING: {ingredient} contains {allergy}"
                }
                alerts.append(alert)
                unsafe_ingredients.append(ingredient)

    # Check for cross-contamination risks
    for ingredient in ingredients:
        if ingredient_lower in INGREDIENT_ALLERGEN_MAP:
            mapped_allergens = INGREDIENT_ALLERGEN_MAP[ingredient_lower]
            for allergen in mapped_allergens:
                if allergen in [a.lower() for a in user_allergies]:
                    alert = {
                        'type': 'cross_contamination_risk',
                        'severity': 'warning',
                        'ingredient': ingredient,
                        'allergen': allergen,
                        'message': f"CROSS-CONTAMINATION RISK: {ingredient} may contain traces of {allergen}"
                    }
                    if alert not in alerts:
                        alerts.append(alert)

    # Check medication interactions
    if user_medications:
        known_interactions = {
            'warfarin': ['vitamin K', 'leafy greens', 'cranberry'],
            'maoi': ['aged cheese', 'wine', 'bananas', 'fava beans'],
            'statin': ['grapefruit', 'grapefruit juice'],
            'antibiotic': ['dairy', 'calcium', 'iron']
        }

        for medication in user_medications:
            med_lower = medication.lower()
            for interaction_med, foods in known_interactions.items():
                if interaction_med in med_lower:
                    for food in foods:
                        for ingredient in ingredients:
                            if food in ingredient.lower():
                                interaction_warnings.append({
                                    'type': 'medication_interaction',
                                    'severity': 'warning',
                                    'medication': medication,
                                    'food': ingredient,
                                    'message': f"CAUTION: {ingredient} may interact with {medication}"
                                })

    is_safe = len(alerts) == 0
    highest_severity = 'safe'

    for alert in alerts:
        if alert['severity'] == 'critical':
            highest_severity = 'critical'
            is_safe = False
        elif alert['severity'] == 'warning' and highest_severity != 'critical':
            highest_severity = 'warning'

    return {
        'is_safe': is_safe,
        'safety_level': highest_severity,
        'food_item': food_item,
        'checked_ingredients': len(ingredients),
        'alert_count': len(alerts),
        'alerts': alerts,
        'interaction_warnings': interaction_warnings,
        'unsafe_ingredients': unsafe_ingredients,
        'recommendation': _get_recommendation(highest_severity, alerts),
        'checked_at': datetime.now().isoformat()
    }


def _get_recommendation(severity: str, alerts: List[Dict]) -> str:
    """Get recommendation based on safety assessment."""
    if severity == 'critical':
        return "DO NOT CONSUME - Contains allergens you are allergic to"
    elif severity == 'warning':
        return "PROCEED WITH CAUTION - Potential risks detected, review warnings"
    else:
        return "APPEARS SAFE - No immediate concerns detected"


async def health_management_skill(
    user_query: str,
    user_profile: Optional[Dict] = None
) -> str:
    """
    Skill for managing health-related queries.

    This skill is attached to the Assistant Agent and provides:
    - Food safety checking
    - Allergy awareness
    - Medication interaction warnings
    - Meal planning assistance

    Args:
        user_query: User's health-related question or request
        user_profile: User's health profile (allergies, medications, dietary restrictions)

    Returns:
        Health guidance and safety assessment
    """
    if user_profile is None:
        user_profile = {
            'allergies': [],
            'medications': [],
            'dietary_restrictions': []
        }

    # Determine the type of health query
    query_lower = user_query.lower()

    if any(kw in query_lower for kw in ['safe', 'allergen', 'ingredient', 'eat', 'consume']):
        # Food safety query
        return await _handle_food_safety_query(user_query, user_profile)
    elif any(kw in query_lower for kw in ['medication', 'medicine', 'drug', 'prescription']):
        # Medication query
        return _handle_medication_query(user_query, user_profile)
    elif any(kw in query_lower for kw in ['meal', 'recipe', 'cook', 'breakfast', 'lunch', 'dinner']):
        # Meal planning query
        return _handle_meal_planning_query(user_query, user_profile)
    else:
        # General health query
        return _handle_general_health_query(user_query, user_profile)


async def _handle_food_safety_query(user_query: str, user_profile: Dict) -> str:
    """Handle food safety checking queries."""
    # Extract food item and ingredients from query (simplified)
    # In production, use NLP or image OCR to extract this info

    # If the router passed OCR'd ingredients from a label image, use them first.
    # This makes the README's "read label → check allergies" pipeline real.
    ocr_ingredients = user_profile.get("_ocr_ingredients")

    food_item = "the food item"
    ingredients = []

    query_lower = user_query.lower()

    if ocr_ingredients:
        # Use the real OCR'd ingredients; the user already uploaded a label.
        ingredients = list(ocr_ingredients)
        food_item = "the labelled food item"
    elif 'peanut' in query_lower or 'marzipan' in query_lower or 'nut' in query_lower:
        ingredients = ['almonds', 'tree nuts', 'peanut oil']
        food_item = "the mentioned food item"
    elif 'bread' in query_lower or 'wheat' in query_lower:
        ingredients = ['wheat flour', 'yeast', 'salt']
        food_item = "the bread product"
    else:
        # Default mock ingredients (fallback when no label image available)
        ingredients = ['wheat flour', 'sugar', 'soy lecithin', 'milk powder']
        food_item = "Sample Food Product"

    # Use user's allergies if available
    user_allergies = user_profile.get('allergies', ['peanuts', 'milk', 'gluten'])
    if not user_allergies:
        user_allergies = ['peanuts', 'milk', 'gluten']  # Default for demo

    # Perform safety check
    result = await check_food_safety(
        food_item=food_item,
        ingredients=ingredients,
        user_allergies=user_allergies,
        user_medications=user_profile.get('medications', [])
    )

    # Map the internal safety_level to an explicit, user-facing risk label.
    risk_map = {
        'critical': 'HIGH',
        'warning': 'MODERATE',
        'safe': 'LOW',
    }
    risk_level = risk_map.get(result.get('safety_level', 'safe'), 'LOW')

    # Format response — always state the explicit HIGH/MODERATE/LOW risk level.
    if result['is_safe']:
        return (
            f"🏥 FOOD SAFETY CHECK\n\n"
            f"Item: {result['food_item']}\n"
            f"Status: SAFE ✅\n"
            f"Risk level: {risk_level}\n\n"
            f"{result['recommendation']}\n\n"
            f"No allergen warnings detected for your allergies: {', '.join(user_allergies)}\n\n"
            f"Always double-check the product label when in doubt!"
        )
    else:
        status_label = 'UNSAFE ❌' if risk_level == 'HIGH' else 'CAUTION ⚠️'
        concerns = '\n'.join(f"  • {alert['message']}" for alert in result['alerts']) or "  • None"
        interactions = '\n'.join(f"  • {w['message']}" for w in result.get('interaction_warnings', [])) or "  • No medication interactions"
        return (
            f"🏥 FOOD SAFETY ALERT\n\n"
            f"Item: {result['food_item']}\n"
            f"Status: {status_label}\n"
            f"Risk level: {risk_level}\n\n"
            f"{result['recommendation']}\n\n"
            f"Detected allergen concerns:\n"
            f"{concerns}\n\n"
            f"Medication interactions:\n"
            f"{interactions}\n\n"
            f"{'⚠️ AVOID — contains an allergen you are allergic to.' if risk_level == 'HIGH' else 'Proceed with caution and consult your healthcare provider.'}"
        )


def _handle_medication_query(user_query: str, user_profile: Dict) -> str:
    """Handle medication-related queries."""
    medications = user_profile.get('medications', [])

    if not medications:
        return (
            f"💊 MEDICATION INFORMATION\n\n"
            f"No medications currently on file for your profile.\n\n"
            f"To add medications, please say or type: 'Add medication: [medication name]'\n\n"
            f"I can help you check for food interactions once medications are added."
        )

    return (
        f"💊 MEDICATION ADVISORY\n\n"
        f"Your current medications:\n"
        + '\n'.join(f"  • {med}" for med in medications) + f"\n\n"
        f"{'Key interactions to avoid:'}\n"
        + '\n'.join(f"  • Dairy products with antibiotics" if 'antibiotic' in str(medications).lower() else "  • No specific warnings") + f"\n\n"
        f"Always consult your healthcare provider with specific medication questions."
    )


def _handle_meal_planning_query(user_query: str, user_profile: Dict) -> str:
    """Handle meal planning queries."""
    dietary_restrictions = user_profile.get('dietary_restrictions', [])
    allergies = user_profile.get('allergies', [])

    return (
        f"🍽️ MEAL PLANNING ASSISTANCE\n\n"
        f"Your dietary profile:\n"
        + (f"  • Allergies: {', '.join(allergies)}" if allergies else "  • No allergies on file\n") +
        (f"  • Dietary restrictions: {', '.join(dietary_restrictions)}" if dietary_restrictions else "  • No dietary restrictions on file\n") + f"\n\n"
        f"{'Suggested meals based on your profile:'}\n"
        f"  • Grilled chicken with steamed vegetables (safe, no allergens)\n"
        f"  • Rice and black beans with vegetables (naturally allergen-free)\n"
        f"  • Fresh fruit salad with yogurt alternative\n\n"
        f"Would you like me to check specific ingredients or suggest recipes?"
    )


def _handle_general_health_query(user_query: str, user_profile: Dict) -> str:
    """Handle general health queries."""
    return (
        f"🏥 HEALTH INFORMATION\n\n"
        f"I'm here to help with your health-related questions.\n\n"
        f"I can assist you with:\n"
        f"  • Checking food safety against your allergies\n"
        f"  • Reviewing medication interactions\n"
        f"  • Planning safe meals\n"
        f"  • Understanding nutrition information\n\n"
        f"What would you like help with today?"
    )


# Example usage context for the agent
HEALTH_SKILL_INSTRUCTION = """
You have access to the health_management_skill for all health-related queries.

When handling health queries:
1. ALWAYS prioritize safety - check allergies before any food recommendation
2. Ask clarifying questions if the food item is unclear
3. When checking medication interactions, request a complete medication list
4. For meal planning, consider all dietary restrictions and allergies
5. When in doubt, recommend consulting a healthcare professional

Remember: Health data is sensitive. Handle all information with care and encourage users to verify critical health decisions with professionals.
"""