import base64
from datetime import datetime
import re


def generate_password(business_short_code: str, passkey: str, timestamp: str) -> str:
    """
    Generate the password for M-Pesa API authentication.
    Password is a base64 encoded string of: BusinessShortCode + Passkey + Timestamp

    Args:
        business_short_code: The organization's shortcode (5-6 digits)
        passkey: The Lipa na M-Pesa Online Passkey
        timestamp: Current timestamp in YYYYMMDDHHmmss format

    Returns:
        Base64 encoded password string
    """
    data_to_encode = f"{business_short_code}{passkey}{timestamp}"
    encoded_bytes = base64.b64encode(data_to_encode.encode())
    return encoded_bytes.decode('utf-8')


def get_timestamp() -> str:
    """
    Generate timestamp in the format required by M-Pesa API.
    Format: YYYYMMDDHHmmss

    Returns:
        Current timestamp as string in YYYYMMDDHHmmss format
    """
    return datetime.now().strftime('%Y%m%d%H%M%S')


def format_phone_number(phone_number: str) -> str:
    """
    Format phone number to M-Pesa required format (254XXXXXXXXX).
    Handles various input formats:
    - 0712345678 -> 254712345678
    - 712345678 -> 254712345678
    - +254712345678 -> 254712345678
    - 254712345678 -> 254712345678

    Args:
        phone_number: Phone number in various formats

    Returns:
        Formatted phone number starting with 254

    Raises:
        ValueError: If phone number format is invalid
    """
    # Remove any spaces, dashes, or other non-digit characters except '+'
    cleaned = re.sub(r'[^\d+]', '', phone_number)

    # Remove leading '+' if present
    if cleaned.startswith('+'):
        cleaned = cleaned[1:]

    # Remove leading '0' if present and add country code
    if cleaned.startswith('0'):
        cleaned = '254' + cleaned[1:]

    # Add country code if not present
    elif not cleaned.startswith('254'):
        cleaned = '254' + cleaned

    # Validate the final format (should be 254 followed by 9 digits)
    if not re.match(r'^254\d{9}$', cleaned):
        raise ValueError(
            f"Invalid phone number format: {phone_number}. "
            "Expected format: 254XXXXXXXXX (12 digits total)"
        )

    return cleaned
