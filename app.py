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
    return "✅ Save The Milk quote server is running with markup + Mini Kit support!"

@app.route("/", methods=["POST"])
def quote():
    data = request.get_json()

    from_zip = data.get("from_zip")
    to_zip = data.get("to_zip")
    ounces = int(data.get("ounces", 0))
    customer_email = data.get("email")
    cc_email = data.get("cc", None)
    need_return_label = data.get("need_return_label", "no").lower() == "yes"
    kit_size = data.get("kit_size", "tiny").lower()

    # Define your kit profiles
    kit_profiles = {
        "tiny": {
            "dimensions": {"length": 9, "width": 7, "height": 7},
            "weight_func": lambda oz: 5 if oz <= 30 else 7 if oz >= 50 else round(5 + (oz - 30) * (2 / 20), 1),
            "return_weight": 2,
            "kit_label": "Tiny Kit",
        },
        "mini": {
            "dimensions": {"length": 14, "width": 11, "height": 11},
            "weight_func": lambda oz: 7 if oz <= 90 else 12,
            "return_weight": 2,
            "kit_label": "Mini Kit",
        }
    }

    # Grab the right profile
    kit = kit_profiles.get(kit_size, kit_profiles["tiny"])
    weight = kit["weight_func"](ounces)
    dimensions = kit["dimensions"]
    return_weight = kit["return_weight"]
    kit_label = kit["kit_label"]

    api_key = os.environ.get("SHIPENGINE_API_KEY")
    headers = {
        "Content-Type": "application/json",
        "API-Key": api_key
    }

    # Prepare ShipEngine payload
    payload = {
        "rate_options": {
            "carrier_ids": ["se-2347705"],  # Your UPS carrier ID
            "ship_date": datetime.today().strftime('%Y-%m-%d')
        },
        "shipment": {
            "validate_address": "no_validation",
            "ship_from": {"postal_code": from_zip, "country_code": "US"},
            "ship_to": {"postal_code": to_zip, "country_code": "US", "address_residential_indicator": "yes"},
            "packages": [{
                "weight": {"value": weight, "unit": "pound"},
                "dimensions": {
                    "unit": "inch",
                    "length": dimensions["length"],
                    "width": dimensions["width"],
                    "height": dimensions["height"]
                }
            }]
        }
    }

    # Get main quotes
    response = requests.post("https://api.shipengine.com/v1/rates/estimate", headers=headers, json=payload)

    if response.status_code != 200:
        return jsonify({"error": "ShipEngine API error", "details": response.text}), 400

    rates = response.json().get("rate_response", {}).get("rates", [])
    if not rates:
        return jsonify({"error": "No rates found"}), 404

    # Apply markup logic
    quote_lines = []
    for rate in rates:
        carrier = rate["carrier_friendly_name"]
        service = rate["service_code"]
        base_cost = rate["shipping_amount"]["amount"]

        markup = 0
        if "next_day" in service.lower() or "overnight" in service.lower():
            markup = 50
        elif "2nd_day" in service.lower() or "two_day" in service.lower():
            markup = 45

        customer_cost = round(base_cost + markup, 2)
        quote_lines.append(f"🚚 {carrier} {service}: **${customer_cost:.2f}**")

    # Return label quote
    return_line = ""
    if need_return_label:
        payload["shipment"]["packages"][0]["weight"]["value"] = return_weight
        return_response = requests.post("https://api.shipengine.com/v1/rates/estimate", headers=headers, json=payload)
        if return_response.status_code == 200:
            return_rates = return_response.json().get("rate_response", {}).get("rates", [])
            if return_rates:
                cheapest = min(return_rates, key=lambda r: r["shipping_amount"]["amount"])
                base_return = cheapest["shipping_amount"]["amount"]
                return_total = round(base_return + 16, 2)
                return_line = f"\n🔁 Return Label (Ground, 2 lbs): **${return_total:.2f}**"

    # Compose email
    quote_body = f"""
Hi there! 👋

Here’s your custom shipping quote for a **{kit_label}**:

📦 From ZIP: {from_zip}  
📬 To ZIP: {to_zip}  
🍼 Volume: {ounces} oz  
⚖️ Estimated Weight: {weight} lbs

💰 **Shipping Options**:  
{chr(10).join(quote_lines)}{return_line}

📄 Don’t forget to check our shipping disclaimer:  
👉 https://savethemilk.com/disclaimer.pdf

✅ Best days to ship are Monday–Wednesday.

When you're ready to book, just reply to this email and I’ll get everything handled for you 💛

– Crystal  
Save The Milk  
"""

    email_user = os.environ.get("EMAIL_USER")
    email_pass = os.environ.get("EMAIL_PASS")
    send_from_name = os.environ.get("SEND_FROM_NAME")

    msg = MIMEMultipart()
    msg['From'] = f"{send_from_name} <{email_user}>"
    msg['To'] = customer_email
    msg['Subject'] = f"Your Save The Milk Shipping Quote – {kit_label}"
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
