"""
Timezone utilities for TraitorTrack application.
Provides Indian Standard Time (IST) formatting and conversion functions.
"""

from datetime import datetime
import pytz

IST = pytz.timezone('Asia/Kolkata')


def format_datetime_ist(dt, format_type='full'):
    """
    Format datetime to Indian Standard Time.
    
    Args:
        dt: datetime object to format (can be naive UTC or timezone-aware)
        format_type: 'full' (DD/MM/YY HH:MM), 'date' (DD/MM/YY), 'time' (HH:MM)
    
    Returns:
        Formatted string in IST timezone, or 'N/A' if dt is None
    """
    if dt is None:
        return 'N/A'
    
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)
    
    ist_dt = dt.astimezone(IST)
    
    if format_type == 'date':
        return ist_dt.strftime('%d/%m/%y')
    elif format_type == 'time':
        return ist_dt.strftime('%H:%M')
    else:
        return ist_dt.strftime('%d/%m/%y %H:%M')


def get_ist_now():
    """Get current time in IST."""
    return datetime.now(IST)


def convert_to_ist(dt):
    """
    Convert a datetime to IST timezone.
    
    Args:
        dt: datetime object (naive assumed UTC, or timezone-aware)
    
    Returns:
        datetime object in IST timezone, or None if input is None
    """
    if dt is None:
        return None
    
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)
    
    return dt.astimezone(IST)


def get_utc_now():
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(pytz.utc)
