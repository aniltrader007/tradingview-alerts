from flask import Flask, request, jsonify
from flask_cors import CORS
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from twilio.rest import Client
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

signals = []

def send_email(subject, body):
    try:
        sender   = os.environ.get("GMAIL_USER")
        password = os.environ.get("GMAIL_APP_PASSWORD")
        receiver = os.environ.get("ALERT_EMAIL")
        msg = MIMEMultipart()
        msg["From"]    = sender
        msg["To"]      = receiver
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, receiver, msg.as_string())
        server.quit()
        print("Email sent")
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False

def send_sms(body):
    try:
        account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
        auth_token  = os.environ.get("TWILIO_AUTH_TOKEN")
        from_number = os.environ.get("TWILIO_FROM")
        to_number   = os.environ.get("TWILIO_TO")
        client = Client(account_sid, auth_token)
        message = client.messages.create(
            body=body,
            from_=from_number,
            to=to_number
        )
        print(f"SMS sent: {message.sid}")
        return True
    except Exception as e:
        print(f"SMS error: {e}")
        return False

@app.route("/")
def home():
    return jsonify({"status": "RSI Signal Server Running", "signals": len(signals)})

@app.route("/webhook", methods=["POST"])
def webhook():
    data        = request.json or {}
    signal_type = data.get("type", "UNKNOWN")
    rsi         = data.get("rsi", "--")
    strength    = data.get("strength", "--")
    ticker      = data.get("ticker", "SPY")
    price       = data.get("price", "--")
    time_et     = datetime.now().strftime("%I:%M %p ET")

    signal = {
        "type":      signal_type,
        "rsi":       rsi,
        "strength":  strength,
        "ticker":    ticker,
        "price":     price,
        "time":      time_et,
        "timestamp": datetime.now().isoformat()
    }

    signals.append(signal)
    if len(signals) > 50:
        signals.pop(0)

    subject = f"🚨 {ticker} {signal_type} — RSI {rsi}"
    body = f"""RSI DIVERGENCE SIGNAL

Ticker:   {ticker}
Signal:   {signal_type}
RSI:      {rsi}
Strength: {strength}%
Price:    ${price}
Time:     {time_et}"""

    send_email(subject, body)
    send_sms(f"🚨 {ticker} {signal_type}\nRSI {rsi} | ${price}\n{time_et}")

    return jsonify({"status": "ok", "signal": signal})

@app.route("/signals", methods=["GET"])
def get_signals():
    return jsonify(signals)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
