# utils.py
from datetime import datetime, timedelta

def calculate_next_date(start_date, frequency):
    """Calculate the next date based on frequency and start date."""
    today = datetime.now()
    if today < start_date:
        return start_date

    next_date = start_date
    if frequency == 'daily':
        while next_date <= today:
            next_date += timedelta(days=1)
    elif frequency == 'weekly':
        while next_date <= today:
            next_date += timedelta(weeks=1)
    elif frequency == 'monthly':
        while next_date <= today:
            month = next_date.month % 12 + 1
            year = next_date.year + (next_date.month // 12)
            day = min(next_date.day,
                      [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31,
                       30, 31, 30, 31][month - 1])
            next_date = datetime(year, month, day)
    elif frequency == 'yearly':
        while next_date <= today:
            try:
                next_date = datetime(next_date.year + 1, next_date.month, next_date.day)
            except ValueError:  # Handle Feb 29 in leap years
                next_date = datetime(next_date.year + 1, next_date.month, 28)

    return next_date