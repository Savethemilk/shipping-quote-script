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
    print("FULL PAYLOAD:", data)

    # ✅ Required fields
    from_zip = data.get("contact.sender_zip_code")
    to_zip = data.get("contact.receiver_zip_code")
    weight = data.get("contact.enter_ounces")

    if not from_zip or not to_zip or not weight:
        return jsonify({"error": "Missing required fields"}), 400

    try:
        weight = float(weight)
    except ValueError:
        return jsonify({"error": "Invalid weight format"}), 400

    # 🟣 Optional fields for concierge service or tagging
    kit_size = data.get("contact.multi_kit_size")
    custom_kit = data.get("contact.custom_kit")
    return_label = data.get("contact.return_label")
    saturday_delivery = data.get("contact.saturday_delivery")
    freezer = data.get("contact.hotel_freezer")
    hotel_phone = data.get("contact.hotel_phone_number")
    notes = data.get("contact.anything_else")
    email = data.get("contact.email")
    phone = data.get("contact.phone")

    # Debug logging (optional - remove in production)
    print("Kit Size:", kit_size)
    print("Return Label:", return_label)
    print("Saturday Delivery:", saturday_delivery)
    print("Freezer Available:", freezer)
    print("Hotel Phone:", hotel_phone)
    print("Notes:", notes)
    print("Customer Email:", email)
    print("Customer Phone:", phone)

    payload = {
        "rate_options": {
            "carrier_ids": []
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
        return jsonify(response.json()), 200
    else:
        return jsonify({"error": "Failed to fetch quote", "details": response.text}), 500

if __name__ == "__main__":
    app.run(debug=True)
