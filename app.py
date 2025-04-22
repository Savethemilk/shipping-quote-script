from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

SHIPENGINE_API_KEY = os.getenv("SHIPENGINE_API_KEY") or "92f3aIClE0e/4KxBgycNHvBReKr0XbruLuwwIVjRaOs"

@app.route("/")
def index():
    return "Shipping quote API is running"

@app.route("/get-quote", methods=["POST"])
def get_quote():
    data = request.json

    from_zip = data.get("contact.from_zip")
    to_zip = data.get("contact.to_zip")
    weight = data.get("contact.how_many_ounces")

    if not from_zip or not to_zip or not weight:
        return jsonify({"error": "Missing required fields"}), 400

    payload = {
        "rate_options": {
            "carrier_ids": []  # Default carriers
        },
        "shipment": {
            "validate_address": "no_validation",
            "ship_to": {
                "postal_code": to_zip,
                "country_code": "US"
            },
            "ship_from": {
                "postal_code": from_zip,
                "country_code": "US"
            },
            "packages": [{
                "weight": {
                    "value": float(weight),
                    "unit": "ounce"
                }
            }]
        }
    }

    headers = {
        "Content-Type": "application/json",
        "API-Key": SHIPENGINE_API_KEY
    }

    response = requests.post(
        "https://api.shipengine.com/v1/rates/estimate",
        json=payload,
        headers=headers
    )

    if response.status_code != 200:
        return jsonify({"error": "Failed to get quote", "details": response.json()}), response.status_code

    return jsonify(response.json())

if __name__ == "__main__":
    app.run(debug=True)
