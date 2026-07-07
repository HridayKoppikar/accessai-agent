"""Test emergency classification logic."""

from app.agents.coordinator import classify_request_type

test_cases = [
    # (input, expected_result)
    ("Hello", "chat"),
    ("Help me find a restaurant", "navigation"),  # Should NOT be emergency
    ("Help me navigate to Phoenix Palladium", "navigation"),  # Should NOT be emergency
    ("Emergency! I need help now", "emergency"),
    ("Call 911, someone fell", "emergency"),
    ("Not an emergency, just help finding a place", "chat"),  # Negation
    ("No emergency, just lost", "chat"),  # Negation
    ("I'm in danger, urgent help", "emergency"),
    ("Where is the nearest pharmacy", "navigation"),
    ("Describe what you see", "perception"),
    ("Is this safe to eat", "health"),
    ("Help!", "chat"),  # Help alone should NOT be emergency
    ("Danger! Falling objects", "emergency"),
    ("SOS please help", "emergency"),
]

print("\nTesting Emergency Classification\n" + "="*50)

passed = 0
failed = 0

for input_text, expected in test_cases:
    result = classify_request_type(input_text)
    status = "PASS" if result == expected else "FAIL"

    if result == expected:
        passed += 1
    else:
        failed += 1

    print(f"\n{status}: '{input_text}'")
    print(f"  Expected: {expected}")
    print(f"  Got:      {result}")

print("\n" + "="*50)
print(f"Results: {passed} passed, {failed} failed")
print("="*50)