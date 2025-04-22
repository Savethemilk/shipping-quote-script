from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# Use environment variable or hardcoded API key
SHIPENGINE_API_KEY = os.getenv("SHIPENGINE_API_KEY") or "92f3aIClE0e/4KxBgycNHvBReKr0XbruLuwwIVjRaOs"

@app.route("/")
def index():
    return "Shipping quote API is running"

@app.route("/get-quote", methods=["POST"])
def get_quote():
    data = request.json
    print("Received data:", data)  # 👈 Debug line: shows data in Render logs

    from_zip = data.get("contact.from_zip")
    to_zip = data.get("contact.to_zip")
    weight = data.get("contact.how_many_ounces")

    # Validate required fields
    if not from_zip or not to_zip or not weight:
        return jsonify({"error": "Missing required fields"}), 400

    try:
        weight = float(weight)
    except ValueError:
        return jsonify({"error": "Invalid weight format"}), 400

    payload = {
        "rate_options": {
            "carrier_ids": []  # Leave empty to use default carriers
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
            "packages": [
                {
                    "weight": {
                        "value": weight,
                        "unit": "ounce"
                    }
                }
            ]
        }
    }

    headers = {
        "Content-Type": "application/json",
        "API-Key": SHIPENGINE_API_KEY
    }

    response = requests.post("https://api.shipengine.com/v1/rates/estimate", json=payload, headers=headers)

    if response.status_code == 200:
        rates = response.json()
        return jsonify(rates), 200
    else:
        return jsonify({"error": "Failed to fetch quote", "details": response.text}), 500
