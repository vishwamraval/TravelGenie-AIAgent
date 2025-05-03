import requests
from langchain.tools import tool


@tool
def get_weather_by_date(city, date_str):
    """
    Fetches the weather forecast for a given city and date.

    Parameters:
    - city (str): Name of the city
    - date_str (str): Date in 'YYYY-MM-DD' format

    Returns:
    - dict: Weather data for the specified date in JSON format, or an error message.

    Example: get_weather_by_date("College Station", "2025-05-03")
    """

    url = f"https://wttr.in/{city}?format=j1"
    response = requests.get(url)

    if response.status_code != 200:
        return {"error": "Error fetching weather data."}

    data = response.json()
    forecast_days = data["weather"]

    for day in forecast_days:
        if day["date"] == date_str:
            avgtemp = day["avgtempC"]
            condition = day["hourly"][4]["weatherDesc"][0]["value"]
            return {
                "date": date_str,
                "city": city,
                "avgtempC": avgtemp,
                "condition": condition,
            }

    return {
        "error": f"No forecast available for {date_str}. TravelGenie provides ~3-day forecasts only."
    }


# Example usage
# get_weather_by_date("College Station", "2025-05-03")
