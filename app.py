from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# Use environment variable or hardcoded API key (for now)
SHIPENGINE_API_KEY = os.getenv("92f3aIClE0e/4KxBgycNHvBReKr0XbruLuwwIVjRaOs") or "92f3aIClE0e/4KxBgycNHvBReKr0XbruLuwwIVjRaOs"

@app.route("/")
def index():
    return "Shipping quote API is running"

@app.route("/get-quote", methods=["POST"])
def get_quote():
    data = request.json

    # Expecting these fields from the FG form or test tool
    from_zip = data.get("from_zip")
    to_zip = data.get("to_zip")
    weight_oz = data.get("weight")  # weight in ounces

    if not from_zip or not to_zip or not weight_oz:
        return jsonify({"error": "Missing required fields"}), 400

    payload = {
        "rate_options": {
            "carrier_ids": [],  # Leave empty to use default carriers
        },
        "shipment": {
            "validate_address": "no_validation",
            "ship_from": {
                "postal_code": from_zip,
                "country_code": "US"
            },
            "ship_to": {
                "postal_code": to_zip,
                "country_code": "US"
            },
            "packages": [
                {
                    "weight": {
                        "value": weight_oz,
                        "unit": "ounce"
                    }
                }
            ]
        }
    }

    headers = {
        "Content-Type": "application/json",
        "API-Key": 92f3aIClE0e/4KxBgycNHvBReKr0XbruLuwwIVjRaOs
    }

    response = requests.post(
        "https://api.shipengine.com/v1/rates/estimate",
        json=payload,
        headers=headers
    )

    if response.status_code != 200:
        return jsonify({"error": "Failed to get rates", "details": response.json()}), response.status_code

    return jsonify(response.json())

if __name__ == "__main__":
    app.run(debug=True)
