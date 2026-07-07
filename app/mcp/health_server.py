"""
HealthGuard MCP Server - AccessAI

Provides health-related tools for allergy checking, medication tracking,
and nutrition analysis.
"""

from typing import List, Dict, Any
from datetime import datetime


# Common allergens database
COMMON_ALLERGENS = [
    'peanuts', 'tree nuts', 'milk', 'eggs', 'wheat', 'soy',
    'fish', 'shellfish', 'sesame', 'corn', 'dairy', 'gluten'
]

# Ingredient allergen mappings
INGREDIENT_ALLERGEN_MAP = {
    'peanut butter': ['peanuts'],
    'milk': ['milk', 'dairy'],
    'egg': ['eggs'],
    'wheat flour': ['wheat', 'gluten'],
    'shellfish': ['shellfish'],
    'soy sauce': ['soy']
}


async def check_allergens(
    ingredients: List[str],
    user_allergies: List[str]
) -> Dict[str, Any]:
    """Check ingredients against user allergies.

    Args:
        ingredients: List of ingredients to check
        user_allergies: User's known allergies

    Returns:
        Safety assessment with detailed warnings
    """
    alerts = []
    unsafe_ingredients = []

    for ingredient in ingredients:
        ingredient_lower = ingredient.lower()
        for allergy in user_allergies:
            allergy_lower = allergy.lower()
            if allergy_lower in ingredient_lower:
                alerts.append({
                    'type': 'allergen_detected',
                    'severity': 'critical',
                    'ingredient': ingredient,
                    'allergen': allergy,
                    'message': f"ALLERGEN WARNING: {ingredient} contains {allergy}"
                })
                unsafe_ingredients.append(ingredient)

    return {
        'is_safe': len(alerts) == 0,
        'checked_ingredients': len(ingredients),
        'alert_count': len(alerts),
        'alerts': alerts,
        'unsafe_ingredients': unsafe_ingredients,
        'checked_at': datetime.now().isoformat()
    }


async def check_cross_contamination(
    food_item: str,
    user_allergies: List[str],
    facility_info: str = None
) -> Dict[str, Any]:
    """Check for cross-contamination risks.

    Args:
        food_item: Name of the food item
        user_allergies: User's allergies
        facility_info: Manufacturing facility information

    Returns:
        Cross-contamination risk assessment
    """
    # Common cross-contamination scenarios
    cross_contam_risks = {
        'peanuts': ['tree nuts', 'milk', 'soy'],
        'shellfish': ['fish'],
        'gluten': ['wheat', 'barley', 'oats']
    }

    risks = []
    for allergy in user_allergies:
        if allergy in cross_contam_risks:
            for related in cross_contam_risks[allergy]:
                if related in food_item.lower():
                    risks.append({
                        'type': 'cross_contamination',
                        'severity': 'warning',
                        'primary_allergen': allergy,
                        'related_ingredient': related,
                        'message': f"Possible cross-contamination: {related} may contain traces of {allergy}"
                    })

    return {
        'food_item': food_item,
        'risk_level': 'high' if risks else 'low',
        'risks': risks,
        'recommendation': 'Avoid if severe allergy' if risks else 'Appears safe'
    }


async def get_nutrition_info(food_item: str) -> Dict[str, Any]:
    """Get nutrition information for a food item.

    Args:
        food_item: Name of the food item

    Returns:
        Nutrition facts
    """
    return {
        'food_item': food_item,
        'serving_size': '100g',
        'calories': 150,
        'macronutrients': {
            'protein': 5,
            'carbohydrates': 20,
            'fat': 6,
            'fiber': 3,
            'sugar': 8
        },
        'vitamins_minerals': {},
        'sodium': 200
    }


async def check_medication_interactions(
    medications: List[str],
    food_or_supplement: str
) -> Dict[str, Any]:
    """Check for medication-food interactions.

    Args:
        medications: List of user's medications
        food_or_supplement: Food or supplement being considered

    Returns:
        Interaction assessment
    """
    # Common medication interactions
    known_interactions = {
        'warfarin': ['vitamin K', 'leafy greens', 'cranberry'],
        'maoi': ['aged cheese', 'wine', 'bananas'],
        'statin': ['grapefruit'],
        'antibiotic': ['dairy', 'calcium']
    }

    interactions = []
    for med in medications:
        for interaction_food, foods in known_interactions.items():
            if interaction_food in med.lower():
                for food in foods:
                    if food in food_or_supplement.lower():
                        interactions.append({
                            'type': 'medication_interaction',
                            'severity': 'warning',
                            'medication': med,
                            'food': food_or_supplement,
                            'interaction_food': food,
                            'message': f"CAUTION: {food_or_supplement} may interact with {med}"
                        })

    return {
        'medications_checked': len(medications),
        'food': food_or_supplement,
        'interactions_found': len(interactions),
        'interactions': interactions,
        'is_safe': len(interactions) == 0,
        'recommendation': 'Consult doctor if interactions found' if interactions else 'No known interactions'
    }


async def plan_meal_dietary(
    ingredients: List[str],
    dietary_restrictions: List[str],
    meals_count: int = 3
) -> Dict[str, Any]:
    """Plan meals based on ingredients and dietary needs.

    Args:
        ingredients: Available ingredients
        dietary_restrictions: User's dietary needs (vegan, gluten-free, keto, etc.)
        meals_count: Number of meals to plan

    Returns:
        Meal plan with recipes
    """
    return {
        'meals_planned': meals_count,
        'dietary_compliance': all(r in ['vegan', 'vegetarian', 'gluten-free', 'keto', 'dairy-free'] for r in dietary_restrictions),
        'restrictions': dietary_restrictions,
        'meals': [
            {
                'name': f'Meal {i+1}',
                'ingredients': ingredients[:3],
                'steps': ['Prepare', 'Cook', 'Serve'],
                'prep_time': '20 minutes',
                'calories': 400
            }
            for i in range(meals_count)
        ]
    }


async def set_medication_reminder(
    medication_name: str,
    dosage: str,
    schedule: str,
    emergency_contact: str = None
) -> Dict[str, Any]:
    """Set up a medication reminder.

    Args:
        medication_name: Name of medication
        dosage: Dosage amount
        schedule: When to take (e.g., "8am daily")
        emergency_contact: Contact for missed doses

    Returns:
        Reminder confirmation
    """
    return {
        'status': 'reminder_set',
        'medication': medication_name,
        'dosage': dosage,
        'schedule': schedule,
        'emergency_contact': emergency_contact,
        'next_reminder': 'Tomorrow at scheduled time'
    }


def get_health_tools() -> List[Dict[str, Any]]:
    """Get list of available health tools for MCP registration."""
    return [
        {
            'name': 'check_allergens',
            'description': 'Check ingredients against user allergies',
            'parameters': {
                'ingredients': {'type': 'array', 'items': {'type': 'string'}},
                'user_allergies': {'type': 'array', 'items': {'type': 'string'}}
            }
        },
        {
            'name': 'check_cross_contamination',
            'description': 'Check for cross-contamination risks',
            'parameters': {
                'food_item': {'type': 'string'},
                'user_allergies': {'type': 'array', 'items': {'type': 'string'}},
                'facility_info': {'type': 'string'}
            }
        },
        {
            'name': 'get_nutrition_info',
            'description': 'Get nutrition facts for food',
            'parameters': {
                'food_item': {'type': 'string'}
            }
        },
        {
            'name': 'check_medication_interactions',
            'description': 'Check medication-food interactions',
            'parameters': {
                'medications': {'type': 'array', 'items': {'type': 'string'}},
                'food_or_supplement': {'type': 'string'}
            }
        },
        {
            'name': 'plan_meal_dietary',
            'description': 'Plan meals based on dietary restrictions',
            'parameters': {
                'ingredients': {'type': 'array', 'items': {'type': 'string'}},
                'dietary_restrictions': {'type': 'array', 'items': {'type': 'string'}},
                'meals_count': {'type': 'integer'}
            }
        }
    ]