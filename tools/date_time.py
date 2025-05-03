from langchain.tools import tool
from datetime import date


@tool
def get_todays_date() -> str:
    """Returns today's date in YYYY-MM-DD format.
    Args:
        None
    Returns:
        str: Today's date in YYYY-MM-DD format.
    """
    return f"{date.today()}"
