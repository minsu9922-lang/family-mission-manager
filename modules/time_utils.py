from datetime import datetime
import pytz

KST = pytz.timezone('Asia/Seoul')

def get_now():
    """Returns current time in KST."""
    return datetime.now(KST)

def get_today_str(fmt="%Y-%m-%d"):
    """Returns today's date string in KST."""
    return get_now().strftime(fmt)

def get_current_time_str(fmt="%Y-%m-%d %H:%M:%S"):
    """Returns current timestamp string in KST."""
    return get_now().strftime(fmt)
