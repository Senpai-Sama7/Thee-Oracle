def validate_input(data, required_fields, optional_fields=None):
    """Validate input data"""
    if not isinstance(data, dict):
        return False, "Invalid data format"

    # Check required fields
    for field in required_fields:
        if field not in data or not data[field]:
            return False, f"Missing required field: {field}"

    # Sanitize string inputs
    for key, value in data.items():
        if isinstance(value, str):
            # Basic XSS prevention
            data[key] = value.replace("<", "&lt;").replace(">", "&gt;")
            # SQL injection prevention
            data[key] = data[key].replace("'", "''").replace('"', '""')

    return True, "Valid"
