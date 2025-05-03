import json
import http.client
import urllib.parse
import csv
from langchain.tools import tool
from concurrent.futures import ThreadPoolExecutor, as_completed


def load_city_to_iata(csv_file_path):
    city_to_iata = {}
    try:
        with open(csv_file_path, newline="", encoding="utf-8-sig") as csvfile:
            reader = csv.DictReader(csvfile, delimiter=";")
            for row in reader:
                try:
                    city = row["City Name"].strip()
                    iata = row["Airport Code"].strip()
                    if city and iata:
                        if city not in city_to_iata:
                            city_to_iata[city] = []
                        if iata not in city_to_iata[city]:
                            city_to_iata[city].append(iata)
                except KeyError:
                    continue
                except Exception:
                    continue
    except FileNotFoundError:
        print(f"Error: The file {csv_file_path} was not found.")
        pass
    except Exception:
        pass
    return city_to_iata


CSV_FILE_PATH = "./airport_codes.csv"
CITY_TO_IATA = load_city_to_iata(CSV_FILE_PATH)


@tool
def get_flights(from_city: str, to_city: str, date: str):
    """
    Find flights from one city to another on a specific date, handling multiple airports.
    Args:
        from_city (str): The city to fly from.
        to_city (str): The city to fly to.
        date (str): The date of the flight in MM/DD/YYYY format.
    Returns:
        str: A message indicating the flight search details.
    """
    date_parts = date.split("/")
    formatted_date = (
        f"{date_parts[2]}-{date_parts[0].zfill(2)}-{date_parts[1].zfill(2)}"
    )

    from_iatas = CITY_TO_IATA.get(from_city, [])
    to_iatas = CITY_TO_IATA.get(to_city, [])

    if not from_iatas or not to_iatas:
        return f"Error: No IATA code found for {from_city} or {to_city}"

    input_data_list = []
    for from_iata in from_iatas:
        for to_iata in to_iatas:
            input_data = {
                from_city: {
                    "Arrival Date": formatted_date,
                    "Departure Date": formatted_date,
                    "Airport": f"{from_iata}.AIRPORT",
                },
                to_city: {
                    "Arrival Date": formatted_date,
                    "Departure Date": formatted_date,
                    "Airport": f"{to_iata}.AIRPORT",
                },
            }
            input_data_list.append((from_iata, to_iata, input_data))

    all_flight_data = []
    num_adults = 1
    for from_iata, to_iata, input_data in input_data_list:
        flight_data = FlightRetriever(input_data, num_adults)
        for flight in flight_data:
            flight["from_airport"] = from_iata
            flight["to_airport"] = to_iata
        all_flight_data.extend(flight_data)

    if not all_flight_data:
        return f"No flights found from {from_city} to {to_city} on {date}."

    result = f"Flights from {from_city} to {to_city} on {date}:\n"

    for flight in all_flight_data:
        if flight["note"]:
            result += f"\n{flight['from_airport']} to {flight['to_airport']}: {flight['note']}\n"
        elif flight["flights"]:
            result += f"\nAvailable flights from {flight['from_airport']} to {flight['to_airport']}:\n"
            for option in flight["flights"]:
                result += (
                    f"- {option['type']} flight: ${option['price_usd']}, "
                    f"Departs {option['departure_time']}, "
                    f"Arrives {option['arrival_time']}, "
                    f"Airline: {option['airline']}\n"
                )

    return result.strip()


def JSONconverter(input):
    cities = list(input.keys())
    arrivals = []
    departures = []
    airports = []

    for keys, values in input.items():
        arrivals.append(values["Arrival Date"])
        departures.append(values["Departure Date"])
        airports.append(values["Airport"])

    return cities, arrivals, departures, airports


def structure_flight_data(flight_dict):
    structured_data = []

    for (from_city, to_city, date), details in flight_dict.items():
        if isinstance(details, str):
            structured_data.append(
                {
                    "from": from_city,
                    "to": to_city,
                    "date": date,
                    "flights": None,
                    "note": details,
                }
            )
        else:
            flight_options = []
            for category, (price, dep_time, arr_time, airline) in details.items():
                flight_options.append(
                    {
                        "type": category,
                        "price_usd": price,
                        "departure_time": dep_time,
                        "arrival_time": arr_time,
                        "airline": airline,
                    }
                )

            structured_data.append(
                {
                    "from": from_city,
                    "to": to_city,
                    "date": date,
                    "flights": flight_options,
                    "note": None,
                }
            )

    return structured_data


def fetch_flight_data(
    start,
    end,
    start_city,
    end_city,
    real_start_city,
    real_end_city,
    departuredate,
    numadults,
):
    TempFlightHash = {}
    FinalFlightHash = {}
    conn = http.client.HTTPSConnection("booking-com15.p.rapidapi.com")
    headers = {
        "x-rapidapi-key": "b948bbfd4cmsh14ab1def603a52ap1724e7jsn2350fde52ee3",
        "x-rapidapi-host": "booking-com15.p.rapidapi.com",
    }

    url = (
        f"/api/v1/flights/searchFlights?fromId={urllib.parse.quote(start)}&toId={urllib.parse.quote(end)}"
        f"&pageNo=1&adults={numadults}&children=0%2C17&sort=BEST"
        f"&cabinClass=ECONOMY&cy_code=USD&departDate={departuredate}"
    )

    try:
        conn.request("GET", url, headers=headers)
        res = conn.getresponse()
        data = res.read()
        data_json = json.loads(data.decode("utf-8"))
    except Exception as e:
        conn.close()
        return (
            real_start_city,
            real_end_city,
            departuredate,
        ), f"Error fetching data: {str(e)}"
    finally:
        conn.close()

    if "error" in data_json.get("data", {}):
        return (
            real_start_city,
            real_end_city,
            departuredate,
        ), "No flights for these locations. Check alternate way of travel!"

    for flights in data_json["data"].get("flightDeals", []):
        TempFlightHash[flights["key"]] = (
            flights["priceRounded"]["units"],
            flights["offerToken"],
        )

    for sorts, tokens in TempFlightHash.items():
        token = tokens[1]
        for flights in data_json["data"].get("flightOffers", []):
            if token == flights["token"]:
                airline = flights["segments"][0].get("airlineName", "Unknown Airline")
                FinalFlightHash[sorts] = (
                    tokens[0],
                    flights["segments"][0]["departureTime"],
                    flights["segments"][0]["arrivalTime"],
                    airline,
                )

    return (real_start_city, real_end_city, departuredate), FinalFlightHash


def FlightRetriever(input, numadults):
    FullyFinalFlightHash = {}
    real_cities, arrivals, departures, airports = JSONconverter(input)

    tasks = []
    for i in range(len(real_cities) - 1):
        tasks.append(
            (
                airports[i],
                airports[i + 1],
                real_cities[i],
                real_cities[i + 1],
                real_cities[i],
                real_cities[i + 1],
                departures[i],
                numadults,
            )
        )

    with ThreadPoolExecutor(max_workers=50) as executor:
        future_to_task = {
            executor.submit(fetch_flight_data, *task): task for task in tasks
        }
        for future in as_completed(future_to_task):
            key, result = future.result()
            FullyFinalFlightHash[key] = result

    return structure_flight_data(FullyFinalFlightHash)
