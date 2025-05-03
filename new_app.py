from flask import Flask, render_template, request, jsonify
from agent import run_agent  # Assumed to be the same as TravelGenie

app = Flask(__name__)

# Global chat history (simulating st.session_state)
chat_history = []


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate_itinerary():
    try:
        # Extract form data
        country = request.form.get("country", "").strip()
        start_city = request.form.get("start_city", "").strip()
        destinations = request.form.get("destinations", "").strip()
        budget_in_usd = request.form.get("budget_in_usd", "")
        from_date = request.form.get("from_date", "")
        to_date = request.form.get("to_date", "")
        interests = request.form.get("interests", "")  # Single interest
        num_cities = request.form.get("num_cities", "")
        adult_travelers = request.form.get("adult_travelers", "")
        child_travelers = request.form.get("child_travelers", "")
        user_pref = request.form.get("user_pref", "").strip()
        special_requests = request.form.get("special_requests", "").strip()

        # Construct prompt
        prompt = f"""Plan a trip with the following details:
        - Country: {country}
        - Starting from: {start_city}
        - Destinations: {destinations}
        - Budget: ${budget_in_usd}
        - Travel dates: {from_date} to {to_date}
        - Interest: {interests if interests else "None"}
        - Number of cities: {num_cities}
        - Number of travelers: {adult_travelers} Adults, {child_travelers} Kids
        - Preferences: {user_pref}
        - Special requests: {special_requests if special_requests else "None"}

        Please provide a detailed travel plan including:
        1. Recommended itinerary
        2. Transportation options
        3. Accommodation suggestions
        4. Activities and attractions
        5. Estimated costs
        6. Any special considerations based on the provided preferences
        """

        # Call run_agent
        response = run_agent(prompt, "conversation_1")

        return jsonify({"itinerary": response})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        prompt = data.get("prompt", "").strip()
        if not prompt:
            return jsonify({"error": "Prompt is required"}), 400

        # Call run_agent
        query, response, messages = run_agent(prompt, "conversation_1")

        return jsonify({"response": response})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
