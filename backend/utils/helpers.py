"""Helper utility functions."""
import random
import string
from datetime import datetime


def generate_grievance_id() -> str:
    """Generate a unique grievance ID in format GRV0001234."""
    digits = ''.join(random.choices(string.digits, k=7))
    return f"GRV{digits}"


def format_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format datetime object to string."""
    if dt is None:
        return ""
    return dt.strftime(format_str)
