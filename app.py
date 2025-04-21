from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# Your actual ShipEngine API Key
SHIPENGINE_API_KEY = "92f3aIClE0e/4KxBgycNHvBReKr0XbruLuwwIVjRaOs"

@app.route("/")
def home():
    return "ShipEngine API is live."

@app.route("/get-quote", methods=["POST"])
def get_quote():
    data = request.json

    contact.from_zip_code = data.get("contact.from_zip_code")
    contact.to_zip_code = data.get("contact.to_zip_code")
    contact.how_many_ounces = data.get("contact.how_many_ounces")

    if not all([ontact.from_zip_code, contact.to_zip_code, contact.how_many_ounces]):
        return jsonify({"error": "Missing one or more required fields: contact.from_zip_code, contact.to_zip_code, contact.how_many_ounces"}), 400

    payload = {
        "rate_options": {
            "carrier_ids": []
        },
        "shipment": {
            "validate_address": "no_validation",
            "ship_from": {
                "postal_code": contact.from_zip_code,
                "country_code": "US"
            },
            "ship_to": {
                "postal_code": contact.to_zip_code,
                "country_code": "US"
            },
            "packages": [
                {
                    "contact.how_many_ounces": {
                        "value": contact.how_many_ounces,
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

    if response.status_code != 200:
        return jsonify({"error": "ShipEngine API request failed", "details": response.json()}), response.status_code

    return jsonify(response.json())

if __name__ == "__main__":
    app.run(debug=True)
