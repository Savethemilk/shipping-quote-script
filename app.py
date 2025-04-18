from flask import Flask, request, jsonify
import os
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return "✅ Save The Milk quote server is running with markup logic!"

@app.route("/", methods=["POST"])
def quote():
    data = request.get_json()

    from_zip = data.get("from_zip")
    to_zip = data.get("to_zip")
    ounces = int(data.get("ounces", 0))
    customer_email = data.get("email")
    cc_email = data.get("cc", None)
    need_return_label = data.get("need_return_label", "no").lower() == "yes"

    # Estimate weight for Tiny Kit
    if ounces <= 30:
        weight = 5
    elif ounces >= 50:
        weight = 7
    else:
        weight = round(5 + (ounces - 30) * (2 / 20), 1)

    dimensions = {"length": 9, "width": 7, "height": 7}

    api_key = os.environ.get("SHIPENGINE_API_KEY")

    headers = {
        "Content-Type": "application/json",
        "API-Key": api_key
    }

    # ShipEngine request payload for UPS only
    payload = {
        "rate_options": {
            "carrier_ids": ["se-2347705"],  # Your UPS carrier ID
            "ship_date": datetime.today().strftime('%Y-%m-%d')
        },
        "shipment": {
            "validate_address": "no_validation",
            "ship_from": {
                "postal_code": from_zip,
                "country_code": "US"
            },
            "ship_to": {
                "postal_code": to_zip,
                "country_code": "US",
                "address_residential_indicator": "yes"
            },
            "packages": [
                {
                    "weight": {
                        "value": weight,
                        "unit": "pound"
                    },
                    "dimensions": {
                        "unit": "inch",
                        "length": dimensions["length"],
                        "width": dimensions["width"],
                        "height": dimensions["height"]
                    }
                }
            ]
        }
    }

    response = requests.post(
        "https://api.shipengine.com/v1/rates/estimate",
        headers=headers,
        json=payload
    )

    if response.status_code != 200:
        print("❌ ShipEngine Error:", response.status_code, response.text)
        return jsonify({"error": "ShipEngine API error", "details": response.text}), 400

    rates = response.json().get("rate_response", {}).get("rates", [])
    if not rates:
        return jsonify({"error": "No shipping rates found"}), 404

    quote_lines = []
    for rate in rates:
        carrier = rate["carrier_friendly_name"]
        service = rate["service_code"]
        base_cost = rate["shipping_amount"]["amount"]

        # Markup logic
        markup = 0
        if "next_day" in service.lower() or "overnight" in service.lower():
            markup = 50
        elif "2nd_day" in service.lower() or "two_day" in service.lower():
            markup = 45

        customer_cost = round(base_cost + markup, 2)
        quote_lines.append(f"{carrier} {service}: ${customer_cost:.2f}")

    # Build the email
    email_user = os.environ.get("EMAIL_USER")
    email_pass = os.environ.get("EMAIL_PASS")
    send_from_name = os.environ.get("SEND_FROM_NAME")

    quote_body = f"""
Hey there! 🍼

Here’s your custom shipping quote for a Tiny Kit.

📦 From ZIP: {from_zip}  
📬 To ZIP: {to_zip}  
🍼 Estimated Volume: {ounces} oz  
⚖️ Estimated Weight: {weight} lbs

💰 **Overnight Shipping Options (UPS)**:
{chr(10).join(quote_lines)}

🗓️ Best shipping days: Monday–Wednesday  
📄 Please review our disclaimer:  
👉 https://savethemilk.com/disclaimer.pdf

Just reply to this email to choose a label 💛  
– Crystal @ Save The Milk
"""

    msg = MIMEMultipart()
    msg['From'] = f"{send_from_name} <{email_user}>"
    msg['To'] = customer_email
    msg['Subject'] = "Your Save The Milk Quote – Tiny Kit"
    if cc_email:
        msg['Cc'] = cc_email

    msg.attach(MIMEText(quote_body, 'plain'))

    try:
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(email_user, email_pass)
        server.sendmail(email_user, [customer_email] + ([cc_email] if cc_email else []), msg.as_string())
        server.quit()
    except Exception as e:
        return jsonify({"error": f"Email failed: {str(e)}"}), 500

    return jsonify({"status": "Quote email sent successfully!"})
