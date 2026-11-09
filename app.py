import hashlib
import hmac
import logging
import os

import requests
from flask import Flask, jsonify, request

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("bot")

app = Flask(__name__)

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
APP_SECRET = os.getenv("APP_SECRET")  # opcional: valida la firma de Meta
GRAPH_URL = "https://graph.facebook.com/v21.0/{}/messages"

# ---------------- Contenido (formato WhatsApp: *negrita*, _cursiva_) ----------------

BIENVENIDA = (
    "¡Hola{nombre}! Qué gusto saludarte en *'Relaciones en Sintonía'* de YMCA y Castilla-La Mancha.\n\n"
    "Iniciamos nuestro ciclo de reflexiones semanales para construir entornos seguros e igualitarios "
    "en la UPZ 69 de Ciudad Bolívar.\n\n"
    "Por favor, elige una opción para comenzar:"
)

CONSEJOS = (
    "*Consejos Clave de la Campaña:*\n\n"
    "1. *NNA:* Escucha activa y crianza respetuosa sin castigos físicos.\n"
    "2. *Mujeres:* Fomenta la autonomía y establece redes de apoyo.\n"
    "3. *Hombres:* Gestiona la ira con pausas de 3 segundos y comparte las tareas del hogar.\n"
    "4. *Adultos Mayores:* Respeta su dignidad y autonomía patrimonial.\n\n"
    "Escribe *menu* para volver al inicio."
)

RUTAS = (
    "⚠️ *Líneas Oficiales de Atención y Emergencia:*\n\n"
    "• 🟣 *Línea Púrpura (Bogotá):* 018000 112 137 (24/7)\n"
    "• 👶 *Línea 141 (ICBF):* Reportes de NNA\n"
    "• 🚨 *Línea 123:* Emergencias inmediatas\n"
    "• 🧓 *Línea Dorada:* (601) 380 8331\n"
    "• 🟢 *Línea Calma (Hombres):* 018000 423 823\n\n"
    "Escribe *menu* para volver al inicio."
)

SEMANAS = [
    ("semana1", "Semana 1", "Niñez y Adolescencia"),
    ("semana2", "Semana 2", "Mujeres y Autonomía"),
    ("semana3", "Semana 3", "Hombres y Nuevas Masculinidades"),
    ("semana4", "Semana 4", "Personas Mayores y Convivencia"),
]

S1_PREGUNTA = (
    "*Semana 1: Niñez y Adolescencia*\n\n"
    "¿Mito o realidad? _'Una nalgada o un jalón de orejas a tiempo son necesarios para que los "
    "niños y niñas aprendan a respetar.'_"
)
S1_MITO = (
    "¡Así es, es un *mito*! El castigo físico genera miedo, no respeto, y enseña que la violencia "
    "es una forma válida de resolver problemas.\n\nEscribe *menu* para volver al inicio."
)
S1_REALIDAD = (
    "¡No es una realidad, es un *mito*! La violencia física vulnera los derechos de los niños y "
    "afecta su desarrollo emocional.\n\nEscribe *menu* para volver al inicio."
)
PROXIMAMENTE = "Esta trivia estará disponible pronto. Escribe *menu* para volver al inicio."

# ---------------- Envío ----------------


def send(payload):
    payload = {"messaging_product": "whatsapp", **payload}
    try:
        r = requests.post(
            GRAPH_URL.format(PHONE_NUMBER_ID),
            headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"},
            json=payload,
            timeout=15,
        )
        if not r.ok:
            log.error("Error enviando mensaje: %s %s", r.status_code, r.text)
    except requests.RequestException:
        log.exception("Fallo de red enviando mensaje")


def send_text(to, body):
    send({"to": to, "type": "text", "text": {"body": body}})


def send_buttons(to, body, buttons):
    """buttons: lista de (id, título); máximo 3, título hasta 20 caracteres."""
    send({
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": body},
            "action": {"buttons": [
                {"type": "reply", "reply": {"id": i, "title": t}} for i, t in buttons
            ]},
        },
    })


def send_menu(to, nombre=""):
    send_buttons(to, BIENVENIDA.format(nombre=f", {nombre}" if nombre else ""), [
        ("menu_trivias", "Trivia de la semana"),
        ("menu_consejos", "Consejos prevención"),
        ("menu_rutas", "Líneas de ayuda"),
    ])


def send_semanas(to):
    send({
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": "*Selecciona la semana que deseas consultar:*"},
            "action": {
                "button": "Ver semanas",
                "sections": [{"title": "Trivias", "rows": [
                    {"id": sid, "title": t, "description": d} for sid, t, d in SEMANAS
                ]}],
            },
        },
    })


def send_semana1(to):
    send_buttons(to, S1_PREGUNTA, [("s1_mito", "Mito"), ("s1_realidad", "Realidad")])


# ---------------- Lógica ----------------

TEXT_ALIASES = {
    "menu": "menu", "menú": "menu", "hola": "menu", "inicio": "menu", "start": "menu", "/start": "menu",
    "trivia": "menu_trivias", "trivias": "menu_trivias",
    "consejos": "menu_consejos", "ayuda": "menu_rutas", "rutas": "menu_rutas",
    "semana1": "semana1", "/semana1": "semana1", "semana 1": "semana1",
}


def handle_action(to, action, nombre=""):
    if action == "menu":
        send_menu(to, nombre)
    elif action == "menu_trivias":
        send_semanas(to)
    elif action == "menu_consejos":
        send_text(to, CONSEJOS)
    elif action == "menu_rutas":
        send_text(to, RUTAS)
    elif action == "semana1":
        send_semana1(to)
    elif action in ("semana2", "semana3", "semana4"):
        send_text(to, PROXIMAMENTE)
    elif action == "s1_mito":
        send_text(to, S1_MITO)
    elif action == "s1_realidad":
        send_text(to, S1_REALIDAD)
    else:
        send_menu(to, nombre)


def process_message(msg, nombre):
    to = msg["from"]
    mtype = msg.get("type")
    if mtype == "interactive":
        inter = msg["interactive"]
        action = (inter.get("button_reply") or inter.get("list_reply") or {}).get("id", "menu")
    elif mtype == "text":
        texto = msg["text"]["body"].strip().lower()
        action = TEXT_ALIASES.get(texto, "menu")
    else:
        action = "menu"
    handle_action(to, action, nombre)


def valid_signature(req):
    if not APP_SECRET:
        return True
    sig = req.headers.get("X-Hub-Signature-256", "")
    expected = "sha256=" + hmac.new(APP_SECRET.encode(), req.get_data(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig, expected)


@app.route("/")
def health():
    return "ok", 200


@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        if VERIFY_TOKEN and request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return request.args.get("hub.challenge", ""), 200
        return "Error de verificación", 403

    if not valid_signature(request):
        return "firma inválida", 403

    data = request.get_json(silent=True) or {}
    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            nombres = {c.get("wa_id"): c.get("profile", {}).get("name", "") for c in value.get("contacts", [])}
            for msg in value.get("messages", []):
                try:
                    process_message(msg, nombres.get(msg["from"], "").split(" ")[0])
                except Exception:
                    log.exception("Error procesando mensaje")
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
