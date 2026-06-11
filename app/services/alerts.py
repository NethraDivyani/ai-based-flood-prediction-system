def build_alert_message(predicted_class: str) -> str:
    messages = {
        "Normal": "No major flood signal detected for tomorrow.",
        "Alert": "Alert-level flood risk is expected tomorrow. Monitoring is recommended.",
        "Minor Flood": "Minor flood conditions may occur tomorrow. Prepare low-lying areas.",
        "Major Flood": "Major flood conditions are forecast tomorrow. Immediate preparedness is required."
    }
    return messages.get(predicted_class, "Flood forecast generated.")