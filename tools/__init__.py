from .flights import get_flights
from .hotels import get_hotels
from .attractions import get_attractions
from .date_time import get_todays_date
from .rag_tool import local_rag_tool
from .weather import get_weather_by_date

# This is a registry of all the tools available for the TravelGenie agent.
tool_registry = {
    "get_flights": get_flights,
    "get_hotels": get_hotels,
    "get_attractions": get_attractions,
    "get_todays_date": get_todays_date,
    "local_rag_tool": local_rag_tool,
    "get_weather_by_date": get_weather_by_date,
}
