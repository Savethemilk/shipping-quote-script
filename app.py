from flask import Flask, request, jsonify
import os
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return "✅ Save The Milk quote server is running (Tiny Kit only)."

@app.route("/", methods=["POST"])
def quote():
    data = request.get_json()

    # Collect form data
    from_zip = data.get("from_zip")
    to_zip = data.get("to_zip")
    ounces = int(data.get("ounces", 0))
    need_return_label = data.get("need_return_label", "no").lower() == "yes"
    has_freezer = data.get("has_freezer", "yes").lower()
    hotel_phone = data.get("hotel_phone", "")
    needs_saturday = data.get("needs_saturday", "no").lower() == "yes"
    customer_email = data.get("email")
    cc_email = data.get("cc", None)

    # Estimate full kit weight based on ounces
    def get_tiny_weight(oz, is_return):
        if is_return:
            return 2.0
        elif oz <= 30:
            return 5.0
        elif oz >= 50:
            return 7.0
        else:
            return round(5.0 + (oz - 30) * (2.0 / 20), 1)

    full_weight = get_tiny_weight(ounces, False)
    return_weight = 2.0

    # Tiny Kit dimensions
    dimensions = {"length": 9, "width": 7, "height": 7}

    # Build API request to ShipStation
    def get_quote(weight, service_filter):
        shipstation_url = "https://ssapi.shipstation.com/rates/shipments"
        api_key = os.environ.get("SHIPSTATION_API_KEY")
        api_secret = os.environ.get("SHIPSTATION_API_SECRET")

        shipment = {
            "carrierCode": "",  # left blank to return all
            "fromPostalCode": from_zip,
            "toPostalCode": to_zip,
            "toCountry": "US",
            "weight": {
                "value": weight,
                "units": "pounds"
            },
            "dimensions": {
                "units": "inches",
                "length": dimensions["length"],
                "width": dimensions["width"],
                "height": dimensions["height"]
            },
            "confirmation": "none",
            "residential": True
        }

        response = requests.post(
            shipstation_url,
            json=shipment,
            auth=(api_key, api_secret)
        )

        if response.status_code != 200:
            return None, "Error from ShipStation: " + response.text

        rates = response.json().get("rateResponse", {}).get("rates", [])
        if not rates:
            return None, "No shipping rates found."

        filtered = []
        for rate in rates:
            service = rate["serviceCode"].lower()
            if service_filter == "next_day":
                if "next" in service or "overnight" in service:
                    filtered.append({
                        "carrier": rate["carrierCode"],
                        "service": rate["serviceCode"],
                        "cost": float(rate["shipmentCost"])
                    })
            elif service_filter == "ground":
                if "ground" in service:
                    filtered.append({
                        "carrier": rate["carrierCode"],
                        "service": rate["serviceCode"],
                        "cost": float(rate["shipmentCost"])
                    })

        return filtered, None

    # Get full shipment options (next day only)
    full_quotes, full_error = get_quote(full_weight, "next_day")
    if full_error:
        return jsonify({"error": full_error}), 400

    # Get return label quote (ground only, if needed)
    return_quote = {}
    if need_return_label:
        return_quotes, return_error = get_quote(return_weight, "ground")
        if return_error:
            return jsonify({"error": return_error}), 400
        return_quote = return_quotes[0] if return_quotes else {}

    # Compose email message
    quote_lines = []
    for option in full_quotes:
        saturday_note = " + Saturday Delivery" if needs_saturday else ""
        line = f"{option['carrier']} {option['service']}: ${option['cost']:.2f}{saturday_note}"
        quote_lines.append(line)

    quote_body = f"""
Hey there!

Thanks for reaching out — here’s your custom shipping quote for a Tiny Kit. Due to its size, this kit must be shipped using an **overnight service**.

🍼 Milk Volume: {ounces} oz  
📦 Estimated Weight: {full_weight} lbs  
📍 From: {from_zip}  
📬 To: {to_zip}  

💰 **Overnight Shipping Options**:
{chr(10).join(quote_lines)}

"""

    if need_return_label:
        quote_body += f"""
🔁 **Return Label (Empty Kit)**  
📦 Weight: 2 lbs  
🛣️ {return_quote.get('carrier')} {return_quote.get('service')}: ${return_quote.get('cost', 0):.2f}
"""

    if has_freezer == "no":
        quote_body += f"""

⚠️ Since you indicated there’s no freezer at the destination, I will need to call the hotel to confirm freezer access.  
Please confirm this number is correct: {hotel_phone}
"""

    quote_body += f"""

🗓️ **Important Notes**  
• Best days to ship are **Monday through Wednesday**  
• Please review our disclaimer before selecting your label:  
  👉 https://savethemilk.com/disclaimer.pdf  

When you're ready, reply to this email and I’ll get everything set up 💛  
Warmly,  
Crystal  
Save The Milk
"""

    # Send the email
    email_user = os.environ.get("EMAIL_USER")
    email_pass = os.environ.get("EMAIL_PASS")
    send_from_name = os.environ.get("SEND_FROM_NAME")

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
