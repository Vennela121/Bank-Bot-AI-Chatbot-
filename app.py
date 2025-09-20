from flask import Flask, request, jsonify, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import os
import re
from datetime import datetime
import spacy

# --- Paths ---
APP_ROOT = os.path.dirname(__file__)
DB_PATH = os.path.join(APP_ROOT, "data.db")
MODEL_PATH = os.path.join(APP_ROOT, "models", "nlu_model")

# --- Flask app setup ---
app = Flask(__name__, static_folder="static", static_url_path="")
app.secret_key = "replace-with-a-random-secret-key"

# --- Load spaCy NLU model ---
if os.path.exists(MODEL_PATH):
    nlp = spacy.load(MODEL_PATH)
    print("Loaded NLU model from", MODEL_PATH)
else:
    nlp = None
    print("NLU model not found. Run train_nlu.py first.")

# --- Database setup ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Users table
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT UNIQUE,
            account_number TEXT UNIQUE,
            password TEXT,
            balance REAL,
            card_last4 TEXT
        )
    """)

    # Transactions table
    c.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            type TEXT,
            amount REAL,
            description TEXT,
            timestamp TEXT
        )
    """)

    conn.commit()
    conn.close()

def query_db(query, args=(), one=False):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(query, args)
    rv = cur.fetchall()
    conn.commit()
    conn.close()
    return (rv[0] if rv else None) if one else rv

init_db()

# --- Helper: Extract entities ---
def extract_entities(text):
    ent = {}
    text_lower = text.lower()

    # Amount extraction
    m = re.search(r'(?:₹|\bINR\b|\bRs\b|\$)?\s?([0-9][0-9,]\.?[0-9])', text.replace(',', ''))
    if m:
        try:
            ent['amount'] = float(m.group(1))
        except:
            pass

    # Account number
    m2 = re.search(r'\b(\d{4,18})\b', text)
    if m2:
        ent['account_number'] = m2.group(1)

    # Account types
    if "saving" in text_lower or "savings" in text_lower:
        ent['from_account'] = "savings"
    if "checking" in text_lower or "current" in text_lower:
        ent['to_account'] = "checking"

    return ent

# --- Intent recognition helper ---
def recognize_intent(message: str):
    """
    Runs the NLU model on user input and returns (intent, confidence, entities).
    """
    if not nlp:
        return "unknown", 0.0, {}

    doc = nlp(message)
    intent_scores = doc.cats if hasattr(doc, "cats") else {}
    intent = max(intent_scores, key=intent_scores.get) if intent_scores else "unknown"
    score = intent_scores.get(intent, 0.0)
    entities = extract_entities(message)

    return intent, score, entities

# --- Routes to serve frontend pages ---
@app.route("/")
def index():
    return app.send_static_file("index.html")

@app.route("/profile.html")
def profile_page():
    return app.send_static_file("profile.html")

# --- Authentication: Register & Login ---
@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    name = data.get("name")
    email = data.get("email")
    account_number = data.get("account_number")
    password = data.get("password")

    if not (name and email and account_number and password):
        return jsonify({"success": False, "message": "All fields required."}), 400

    hashed = generate_password_hash(password)
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "INSERT INTO users (name,email,account_number,password,balance,card_last4) VALUES (?,?,?,?,?,?)",
            (name, email, account_number, hashed, 50000.0, account_number[-4:])
        )
        user_id = c.lastrowid

        # Initial transaction
        c.execute(
            "INSERT INTO transactions (user_id,type,amount,description,timestamp) VALUES (?,?,?,?,?)",
            (user_id, "credit", 50000.0, "Initial balance", datetime.utcnow().isoformat())
        )
        conn.commit()
        conn.close()
    except sqlite3.IntegrityError:
        return jsonify({"success": False, "message": "Email or account already exists."}), 400

    return jsonify({"success": True, "message": "Registered successfully."})

@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    identifier = data.get("email") or data.get("account_number") or data.get("id")
    password = data.get("password")

    if not (identifier and password):
        return jsonify({"success": False, "message": "Provide email/account and password."}), 400

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    if "@" in identifier:  # login with email
        c.execute("SELECT id, password, name, account_number, balance, card_last4 FROM users WHERE email=?", (identifier,))
    else:  # login with account number
        c.execute("SELECT id, password, name, account_number, balance, card_last4 FROM users WHERE account_number=?", (identifier,))

    row = c.fetchone()
    conn.close()

    if row and check_password_hash(row[1], password):
        user = {
            "id": row[0],
            "name": row[2],
            "account_number": row[3],
            "balance": row[4],
            "card_last4": row[5]
        }
        session["user_id"] = user["id"]
        session["logged_in"] = True
        return jsonify({"success": True, "user": user})

    return jsonify({"success": False, "message": "Invalid credentials."}), 401

@app.route("/api/logout", methods=["POST"])
def logout():
    session.pop("user_id", None)
    session["logged_in"] = False
    return jsonify({"success": True})

@app.route("/api/profile", methods=["GET"])
def get_profile():
    uid = session.get("user_id")
    if not uid:
        return jsonify({"success": False, "message": "Not logged in."}), 401

    row = query_db("SELECT id, name, account_number, balance, card_last4 FROM users WHERE id=?", (uid,), one=True)
    if not row:
        return jsonify({"success": False, "message": "User not found."}), 404

    user = {"id": row[0], "name": row[1], "account": row[2], "balance": row[3], "card_last4": row[4]}
    return jsonify({"success": True, "user": user})

# --- Transactions ---
def perform_transfer(from_user_id, to_account_number, amount):
    if amount <= 0:
        return {"success": False, "reply": "Enter a valid amount."}

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Get sender balance
    c.execute("SELECT balance FROM users WHERE id=?", (from_user_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return {"success": False, "reply": "Sender not found."}

    from_balance = row[0]
    if from_balance < amount:
        conn.close()
        return {"success": False, "reply": "Insufficient balance."}

    # Get recipient
    c.execute("SELECT id FROM users WHERE account_number=?", (to_account_number,))
    rec = c.fetchone()
    if not rec:
        conn.close()
        return {"success": False, "reply": "Recipient account not found."}

    to_user_id = rec[0]

    # Update balances
    c.execute("UPDATE users SET balance = balance - ? WHERE id=?", (amount, from_user_id))
    c.execute("UPDATE users SET balance = balance + ? WHERE id=?", (amount, to_user_id))

    ts = datetime.utcnow().isoformat()

    # Record transactions
    c.execute("INSERT INTO transactions (user_id,type,amount,description,timestamp) VALUES (?,?,?,?,?)",
              (from_user_id, "debit", amount, f"Transfer to {to_account_number}", ts))
    c.execute("INSERT INTO transactions (user_id,type,amount,description,timestamp) VALUES (?,?,?,?,?)",
              (to_user_id, "credit", amount, f"Transfer from user {from_user_id}", ts))

    conn.commit()
    conn.close()

    return {"success": True, "reply": f"Transferred ₹{amount:.2f} to account {to_account_number}."}

@app.route("/api/mini_statement", methods=["GET"])
def mini_statement():
    uid = session.get("user_id")
    if not uid:
        return jsonify({"success": False, "message": "Login required."}), 401

    rows = query_db(
        "SELECT type, amount, description, timestamp FROM transactions WHERE user_id=? ORDER BY id DESC LIMIT 5",
        (uid,)
    )
    items = [{"type": r[0], "amount": r[1], "desc": r[2], "ts": r[3]} for r in rows]
    return jsonify({"success": True, "transactions": items})

# --- Chat endpoint (now uses recognize_intent helper) ---
@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json() or {}
    message = data.get("message", "")
    uid = session.get("user_id")

    # --- Recognize intent ---
    intent, score, entities = recognize_intent(message)

    # --- Check login state ---
    logged_in = session.get("logged_in", False)
    response = ""

    # --- Dialogue Management ---
    if intent == "greeting":
        response = "Hello! 👋 How can I help you today?"

    elif intent == "check_balance":
        if not logged_in:
            response = "⚠️ Please login to check your balance."
            session["pending_intent"] = "check_balance"
        else:
            response = "✅ Your current balance is ₹50,000.00."

    elif intent == "transfer_money":
        if not logged_in:
            response = "⚠️ Please login first to transfer money."
            session["pending_intent"] = "transfer_money"
        else:
            account = entities.get("account_number")
            amount = entities.get("amount")

            if not amount:
                response = "How much do you want to transfer?"
                session["awaiting"] = "amount"
            elif not account:
                response = "Please provide the account number."
                session["awaiting"] = "account"
            else:
                result = perform_transfer(uid, account, amount)
                response = result["reply"]

    elif intent == "account_info":
        if not logged_in:
            response = "⚠️ Please login to view account information."
        else:
            response = "Your account number is 123456789 (Savings)."

    elif intent == "mini_statement":
        if not logged_in:
            response = "⚠️ Please login to get mini statement."
        else:
            response = "📃 Mini statement: -₹500 ATM, +₹2000 Salary, -₹700 Shopping."

    elif intent == "card_details":
        if not logged_in:
            response = "⚠️ Please login to check card details."
        else:
            response = "💳 You have a Visa Credit Card ending with 4321."

    else:
        response = "Sorry, I didn’t understand that. Could you rephrase?"

    return jsonify({
        "intent": intent,
        "confidence": score,
        "entities": entities,
        "response": response
    })

# --- Default test route (optional) ---
@app.route("/ping")
def ping():
    return jsonify({"message": "Server is running ✅"})

# --- Run the Flask server ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)