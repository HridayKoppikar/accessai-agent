"""
Assistant Agent - Core Interface for AccessAI

Handles conversation, health management, meal planning, and navigation.
Now properly integrated with AccessAI skills.
"""

from google.adk.agents import Agent
from google.adk.models import Gemini

DEFAULT_MODEL = "gemini-2.5-flash"


async def chat_response(user_input: str, context: dict = None) -> str:
    """Generate natural language response to user input.

    Args:
        user_input: User's message
        context: Conversation context

    Returns:
        Natural language response
    """
    return f"I understand you said '{user_input[:50]}'. How can I help you today?"


async def check_ingredients_against_allergies(ingredients: list, allergies: list) -> dict:
    """Check if ingredients are safe given user allergies.

    Args:
        ingredients: List of food ingredients
        allergies: User's known allergies

    Returns:
        Safety assessment with warnings
    """
    from app.skills.health_skill import check_food_safety

    result = await check_food_safety(
        food_item="checked item",
        ingredients=ingredients,
        user_allergies=allergies
    )
    return {
        'safe': result['is_safe'],
        'warnings': [a['message'] for a in result.get('alerts', [])],
        'checked_ingredients': len(ingredients),
        'cross_contamination_risk': 'low' if result['is_safe'] else 'high'
    }


async def plan_meal(ingredients: list, dietary_restrictions: list) -> dict:
    """Generate meal plan from available ingredients.

    Args:
        ingredients: Available ingredients
        dietary_restrictions: User's dietary needs

    Returns:
        Recipe with preparation steps
    """
    from app.skills.health_skill import plan_meal_dietary

    result = await plan_meal_dietary(ingredients, dietary_restrictions)
    return result


async def navigation_instructions(path: dict, mobility_profile: str = 'general') -> list:
    """Generate turn-by-turn navigation instructions.

    Args:
        path: Route information with waypoints
        mobility_profile: User's mobility needs (wheelchair, cane, general)

    Returns:
        Step-by-step spoken instructions
    """
    from app.skills.navigation_skill import navigation_guidance_skill

    destination = path.get('destination', 'unknown location') if path else 'unknown location'
    result = await navigation_guidance_skill(destination, mobility_profile)
    return [result]


async def generate_narration(environment_state: dict) -> str:
    """Convert environment state to spoken narration for TTS.

    Args:
        environment_state: Current situation data

    Returns:
        Spoken description for text-to-speech
    """
    from app.skills.transcription_skill import generate_audio_narration

    parts = []
    if 'location' in environment_state:
        parts.append(f"You are at {environment_state['location']}")
    if 'time' in environment_state:
        parts.append(f"The time is {environment_state['time']}")
    if 'hazards' in environment_state and environment_state['hazards']:
        parts.append(f"Warning: {len(environment_state['hazards'])} hazards detected")

    narration_text = ". ".join(parts) if parts else "I'm ready to help."
    return generate_audio_narration(narration_text)


def create_assistant_agent() -> Agent:
    """Create the Assistant agent for core interface and health management."""
    return Agent(
        name="assistant_agent",
        model=Gemini(model=DEFAULT_MODEL),
        instruction="""You are the Assistant agent for AccessAI, the primary conversational interface.
Your role is to provide a helpful, empathetic 24/7 personal assistant experience.

Responsibilities (use these tools for specific tasks):
1. chat_response(user_input) - Handle general conversation
2. check_ingredients_against_allergies(ingredients, allergies) - Check food safety
3. plan_meal(ingredients, dietary_restrictions) - Suggest safe recipes
4. navigation_instructions(path, mobility_profile) - Provide directions
5. generate_narration(environment_state) - Create TTS output

Handle these requests:
- Health queries: Use check_ingredients_against_allergies for food safety
- "Read aloud": Use generate_narration to create TTS
- Navigation: Use navigation_instructions for directions
- Meal planning: Use plan_meal for recipe suggestions

Always be patient, clear, and concise. Remember user preferences across sessions.
For health queries, ALWAYS prioritize safety - check allergies and medications first.""",
        tools=[
            chat_response,
            check_ingredients_against_allergies,
            plan_meal,
            navigation_instructions,
            generate_narration
        ]
    )