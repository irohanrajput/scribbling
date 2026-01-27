def validate_tool(text: str) -> str:
    if "fake" in text.lower():
        return "INVALID"
    return "VALID"
