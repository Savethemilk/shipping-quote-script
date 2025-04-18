from flask import Flask, request, jsonify
import os
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)

# Test route
@app.route("/", methods=["GET"])
def home():
    return "✅ Save The Milk quote server is running!"

# Main webhook route
@app.route("/", methods=["POST"])
def quote():
    data = request.get_json()

    # Grab values from FG Funnels form
    from_zip = data.get("from_zip")
    to_zip = data.get("to_zip")
    ounces = int(data.get("ounces", 0))
    shipping_speed = data.get("shipping_speed", "next_day_noon")
    need_kit = data.get("need_kit", "no").lower() == "yes"
    kit_size = data.get("kit_size", "mini")
    return_label = data.get("return_label", "no").lower() == "yes"
    customer_email = data.get("email")
    cc_email = data.get("cc", None)

    # Convert ounces to estimated lbs (roughly 8oz per 0.5 lb)
    estimated_weight = max(1, round(ounces / 16))

    # ShipStation API setup
    api_key = os.environ.get("SHIPSTATION_API_KEY")
    api_secret = os.environ.get("SHIPSTATION_API_SECRET")
    shipstation_url = "https://ssapi.shipstation.com/rates/shipments"

    # Build ShipStation request
    shipment_data = {
        "carrierCode": "ups",
        "serviceCode": "ups_next_day_air",
        "packageCode": "package",
        "fromPostalCode": from_zip,
        "toPostalCode": to_zip,
        "toCountry": "US",
        "weight": {
            "value": estimated_weight,
            "units": "pounds"
        },
        "confirmation": "none",
        "residential": True
    }

    response = requests.post(
        shipstation_url,
        json=shipment_data,
        auth=(api_key, api_secret)
    )

    if response.status_code != 200:
        return jsonify({"error": "Failed to get shipping quote"}), 400

    shipping_cost = response.json()["shipmentCost"]

    # Kit pricing
    kit_prices = {"mini": 52, "medium": 64, "standard": 74}
    kit_cost = kit_prices.get(kit_size.lower(), 0) if need_kit else 0
    return_label_cost = 26 if return_label else 0
    total = round(shipping_cost + kit_cost + return_label_cost, 2)

    # Compose quote message
    quote_msg = f"""
Hey there!

Thanks for reaching out — you’re doing something amazing, and I’m here to help make this process smooth and stress-free.

Based on what you shared, here’s your custom quote:

📍 From ZIP: {from_zip}  
📦 To ZIP: {to_zip}  
🍼 Milk Volume: {ounces} oz  
⚖️ Estimated Weight: {estimated_weight} lbs  
🚚 Shipping Speed: {shipping_speed.replace('_', ' ').title()}  
💰 Shipping Cost: ${shipping_cost:.2f}  
📦 Kit Cost: ${kit_cost:.2f}  
🔁 Return Label: ${return_label_cost:.2f}

----------------------------------------
💰 **Estimated Total: ${total:.2f}**
----------------------------------------

✅ I recommend shipping Monday–Wednesday to avoid weekend delays.  
📄 Please review the Shipping Disclaimer: https://savethemilk.com/disclaimer.pdf

When you're ready, just reply to this email and I’ll send the next steps — whether it’s ordering the kit, sending the label, or answering any questions.

You've got this 💪 — and I’ve got your back!

Warmly,  
Crystal  
Save The Milk  
crystal@savethemilk.com
"""

    # Email sending
    email_user = os.environ.get("EMAIL_USER")
    email_pass = os.environ.get("EMAIL_PASS")
    send_from_name = os.environ.get("SEND_FROM_NAME")

    msg = MIMEMultipart()
    msg['From'] = f"{send_from_name} <{email_user}>"
    msg['To'] = customer_email
    msg['Subject'] = "Your Save The Milk Shipping Quote"
    if cc_email:
        msg['Cc'] = cc_email

    msg.attach(MIMEText(quote_msg, 'plain'))

    try:
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(email_user, email_pass)
        server.sendmail(email_user, [customer_email] + ([cc_email] if cc_email else []), msg.as_string())
        server.quit()
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"status": "quote sent successfully!"})
