import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# Estas variables las configuraremos en Render por seguridad
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = "token_secreto_123" 

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        if request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return request.args.get("hub.challenge"), 200
        return "Error de verificación", 403
    
    if request.method == "POST":
        data = request.json
        print(f"Mensaje recibido: {data}")
        return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
