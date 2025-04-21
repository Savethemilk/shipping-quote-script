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

    from_zip = data.get("from_zip")
    to_zip = data.get("to_zip")
    weight_oz = data.get("weight")

    if not all([from_zip, to_zip, weight_oz]):
        return jsonify({"error": "Missing one or more required fields: from_zip, to_zip, weight"}), 400

    payload = {
        "rate_options": {
            "carrier_ids": []
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
        "API-Key": SHIPENGINE_API_KEY
    }

    response = requests.post("https://api.shipengine.com/v1/rates/estimate", json=payload, headers=headers)

    if response.status_code != 200:
        return jsonify({"error": "ShipEngine API request failed", "details": response.json()}), response.status_code

    return jsonify(response.json())

if __name__ == "__main__":
    app.run(debug=True)
