from langchain.tools import tool
import requests


@tool
def get_attractions(query: str, languagecode: str = "en-us") -> str:
    """
    Fetches location coordinates and region info from a city or place name using the Booking.com API.

    Args:
        query: City or destination name (e.g., "Houston").
        languagecode: Language for the results (default is "en-us").

    Returns:
        A List of attractions in the specified city.
    """
    url = "https://booking-com15.p.rapidapi.com/api/v1/attraction/searchLocation"

    querystring = {"query": query, "languagecode": languagecode}

    headers = {
        "x-rapidapi-key": "b948bbfd4cmsh14ab1def603a52ap1724e7jsn2350fde52ee3",
        "x-rapidapi-host": "booking-com15.p.rapidapi.com",
    }

    response = requests.get(url, headers=headers, params=querystring)

    atx = []
    if response.status_code == 200:
        data = response.json()
        for product in data["data"]["products"]:
            atx.append(product["title"])
        return atx
    else:
        return f"Error: {response.status_code} - {response.text} "
