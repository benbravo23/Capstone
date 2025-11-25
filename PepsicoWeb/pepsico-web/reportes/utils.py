"""Utilidades para reportes."""

from datetime import datetime
import re


def parse_spanish_date(date_str):
    """
    Parse a Spanish formatted date string to a date object.
    Formats accepted: "20 de octubre de 2025", "20-10-2025", "2025-10-20"
    
    Args:
        date_str: String in Spanish format (e.g., "20 de octubre de 2025")
        
    Returns:
        datetime.date object or None if parsing fails
    """
    if not date_str or not isinstance(date_str, str):
        return None
    
    date_str = date_str.strip()
    
    # Spanish month names mapping
    spanish_months = {
        'enero': 1,
        'febrero': 2,
        'marzo': 3,
        'abril': 4,
        'mayo': 5,
        'junio': 6,
        'julio': 7,
        'agosto': 8,
        'septiembre': 9,
        'setiembre': 9,  # Alternative spelling
        'octubre': 10,
        'noviembre': 11,
        'diciembre': 12
    }
    
    # Try pattern: "DD de MESES YYYY"
    match = re.match(r'(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})', date_str, re.IGNORECASE)
    if match:
        day, month_name, year = match.groups()
        month_num = spanish_months.get(month_name.lower())
        if month_num:
            try:
                return datetime(int(year), month_num, int(day)).date()
            except ValueError:
                pass
    
    # Try pattern: "DD-MM-YYYY"
    match = re.match(r'(\d{1,2})-(\d{1,2})-(\d{4})', date_str)
    if match:
        day, month, year = match.groups()
        try:
            return datetime(int(year), int(month), int(day)).date()
        except ValueError:
            pass
    
    # Try pattern: "YYYY-MM-DD" (ISO format)
    match = re.match(r'(\d{4})-(\d{1,2})-(\d{1,2})', date_str)
    if match:
        year, month, day = match.groups()
        try:
            return datetime(int(year), int(month), int(day)).date()
        except ValueError:
            pass
    
    return None


def parse_spanish_datetime(datetime_str):
    """
    Parse a Spanish formatted datetime string.
    
    Args:
        datetime_str: String in format "DD de mes de YYYY HH:MM" or ISO format
        
    Returns:
        datetime.datetime object or None if parsing fails
    """
    if not datetime_str or not isinstance(datetime_str, str):
        return None
    
    datetime_str = datetime_str.strip()
    
    # Try to extract date and time parts
    # Pattern: "DD de MESES YYYY HH:MM"
    spanish_months = {
        'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
        'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
        'septiembre': 9, 'setiembre': 9, 'octubre': 10,
        'noviembre': 11, 'diciembre': 12
    }
    
    match = re.match(
        r'(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})\s+(\d{1,2}):(\d{2})(?::(\d{2}))?',
        datetime_str,
        re.IGNORECASE
    )
    if match:
        day, month_name, year, hour, minute, second = match.groups()
        month_num = spanish_months.get(month_name.lower())
        if month_num:
            try:
                return datetime(
                    int(year), month_num, int(day),
                    int(hour), int(minute), int(second or 0)
                )
            except ValueError:
                pass
    
    # Try ISO format: "YYYY-MM-DD HH:MM:SS"
    match = re.match(r'(\d{4})-(\d{1,2})-(\d{1,2})\s+(\d{1,2}):(\d{2})(?::(\d{2}))?', datetime_str)
    if match:
        year, month, day, hour, minute, second = match.groups()
        try:
            return datetime(
                int(year), int(month), int(day),
                int(hour), int(minute), int(second or 0)
            )
        except ValueError:
            pass
    
    return None
