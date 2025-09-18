import os, uuid
from flask import Flask, redirect, request, session, jsonify, send_from_directory
from flask import url_for
from dotenv import load_dotenv
import msal
from .token_store import token_store
from .agent_runner import run_agent

load_dotenv()
app = Flask(__name__, static_folder="../static", static_url_path="/static")
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change")  # Replace in prod

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
TENANT_ID = os.getenv("TENANT_ID")
REDIRECT_URI = os.getenv("REDIRECT_URI")
GRAPH_SCOPES = os.getenv("GRAPH_SCOPES", "openid profile User.Read").split()
AI_FOUNDRY_ENDPOINT = os.getenv("AI_FOUNDRY_ENDPOINT")

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"

def _build_msal_app():
    return msal.ConfidentialClientApplication(
        client_id=CLIENT_ID,
        client_credential=CLIENT_SECRET,
        authority=AUTHORITY
    )

@app.route("/")
def index():
    if "session_id" in session:
        return send_from_directory(app.static_folder, "index.html")
    return redirect(url_for("login"))

@app.route("/login")
def login():
    session["state"] = str(uuid.uuid4())
    auth_app = _build_msal_app()
    auth_url = auth_app.get_authorization_request_url(
        scopes=GRAPH_SCOPES,
        redirect_uri=REDIRECT_URI,
        state=session["state"],
        prompt="select_account"
    )
    return redirect(auth_url)

@app.route("/callback")
def callback():
    if request.args.get("state") != session.get("state"):
        return "State  mismatch", 400
    code = request.args.get("code")
    if not code:
        return "No code", 400
    auth_app = _build_msal_app()
    result = auth_app.acquire_token_by_authorization_code(
        code=code,
        scopes=GRAPH_SCOPES,
        redirect_uri=REDIRECT_URI
    )
    if "access_token" in result:
        session_id = f"sess_{uuid.uuid4()}"
        session["session_id"] = session_id
        token_store.save_tokens(session_id, result)
        return redirect(url_for("home"))
    return f"Authentication failed: {result.get('error_description')}", 400

@app.route("/home")
def home():
    if "session_id" not in session:
        return redirect(url_for("login"))
    return send_from_directory(app.static_folder, "index.html")

@app.route("/api/agent/run", methods=["POST"])
def api_run_agent():
    if "session_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    data = request.get_json(force=True, silent=True) or {}
    prompt = data.get("prompt", "Give me my profile information.")
    res = run_agent(session["session_id"], prompt, endpoint=AI_FOUNDRY_ENDPOINT)
    return jsonify(res)

@app.route("/logout")
def logout():
    sid = session.pop("session_id", None)
    if sid:
        token_store.delete(sid)
    return redirect(url_for("login"))

# Optional: health check
@app.route("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    app.run(port=5000, debug=True)