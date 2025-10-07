from flask import Flask, request, jsonify, session, make_response
import csv
import io
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import os
import re
from datetime import datetime
import spacy
import train as train_module # <-- KEEP ONLY THIS ONE IMPORT

# --- Paths ---
APP_ROOT = os.path.dirname(__file__)
DB_PATH = os.path.join(APP_ROOT, "data.db")
MODEL_PATH = os.path.join(APP_ROOT, "models", "nlu_model")

# --- Flask app setup ---
app = Flask(__name__, static_folder="static", static_url_path="")
app.secret_key = "replace-with-a-random-secret-key"

# --- Load spaCy NLU model ---
# app.py (NEW MODEL LOADING BLOCK - START)
# Global variable holding the model (Initialize it to None)
nlp = None

def load_nlu_model(path):
    """Loads the spaCy model from the given path into the global nlp variable."""
    global nlp
    try:
        nlp = spacy.load(path) 
        print("Successfully loaded NLU model.")
    except OSError:
        nlp = None
        print(f"NLU model not found at {path}. Bot functionality will be limited.")
    except Exception as e:
        nlp = None
        print(f"Error loading NLU model: {e}")

# Call the function to load the model when the app starts
load_nlu_model(MODEL_PATH) 
# app.py (NEW MODEL LOADING BLOCK - END)
# --- Database setup ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Existing Users table
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

    # Existing Transactions table
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

    # NLU Training Data Table (for admin-added queries)
    c.execute("""
        CREATE TABLE IF NOT EXISTS nlu_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT UNIQUE,
            intent TEXT NOT NULL,
            bot_reply TEXT, -- <--- ADDED THIS COLUMN
            added_by TEXT DEFAULT 'admin',
            timestamp TEXT
        )
    """)
    
    # Chat History Table (Logins-Chat History)
    c.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            timestamp TEXT,
            user_message TEXT,
            bot_response TEXT,
            detected_intent TEXT,
            confidence REAL
        )
    """)

    # Simple Admin Table (for initial admin access)
    c.execute("""
        CREATE TABLE IF NOT EXISTS admin_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    """)
            
    # Create initial Admin user if table is empty (Username: admin, Password: admin)
    c.execute("SELECT COUNT(*) FROM admin_users")
    if c.fetchone()[0] == 0:
        admin_pass_hash = generate_password_hash("admin")
        c.execute("INSERT INTO admin_users (username, password) VALUES (?, ?)", ("admin", admin_pass_hash))


    conn.commit()
    conn.close()
# END OF init_db

# --- Database Helper (Must be defined before first use) ---
def query_db(query, args=(), one=False):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(query, args)
    rv = cur.fetchall()
    conn.commit()
    conn.close()
    return (rv[0] if rv else None) if one else rv

# Initialize database (Must run once)
init_db()


# --- Admin Helper: Check Admin Status ---
def is_admin():
    return session.get("admin_logged_in", False)
    
# --- Get Intents Helper (Reads both CSV and DB) ---
def get_all_intents():
    # Uses the helper function from train.py to get intents from combined source
    return train_module.get_intents_from_combined_source() 

# --- Helper: Extract entities (Used by NLU) ---
def extract_entities(text):
    ent = {}
    text_lower = text.lower()

    # Amount extraction
    m = re.search(r'(?:₹|\bINR\b|\bRs\b|\$)?\s?([0-9][0-9,.]*?)', text.replace(',', ''))
    if m:
        try:
            ent['amount'] = float(m.group(1).replace('₹', '').replace('$', '').strip())
        except:
            pass

    # Account number
    m2 = re.search(r'\b(\d{4,18})\b', text)
    if m2:
        ent['account_number'] = m2.group(1)

    return ent

# --- Intent recognition helper (Must be defined before chat route) ---
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

    # Confidence threshold
    if score < 0.3:  # Adjust this value as needed
        intent = "unknown"

    return intent, score, entities

# --- Transaction Helper ---
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

# =================================================================
# --- APPLICATION ROUTES ---
# =================================================================

@app.route("/")
def index():
    return app.send_static_file("index.html")

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
    identifier = data.get("email") or data.get("account_number")
    password = data.get("password")

    if not (identifier and password):
        return jsonify({"success": False, "message": "Provide email/account and password."}), 400

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    if "@" in identifier:
        c.execute("SELECT id, password, name, email, account_number, balance, card_last4 FROM users WHERE email=?", (identifier,))
    else:
        c.execute("SELECT id, password, name, email, account_number, balance, card_last4 FROM users WHERE account_number=?", (identifier,))

    row = c.fetchone()
    conn.close()

    if row and check_password_hash(row[1], password):
        user = {
            "id": row[0],
            "name": row[2],
            "email": row[3],
            "account_number": row[4],
            "balance": row[5],
            "card_last4": row[6]
        }
        session["user_id"] = user["id"]
        session["logged_in"] = True
        return jsonify({"success": True, "user": user})

    return jsonify({"success": False, "message": "Invalid credentials."}), 401

@app.route("/api/logout", methods=["POST"])
def logout():
    session.pop("user_id", None)
    session["logged_in"] = False
    session.pop("admin_logged_in", None) # Clear admin session too
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

# =================================================================
# --- ADMIN ROUTES (CONSOLIDATED BLOCK) ---
# =================================================================

# --- Admin Authentication ---
@app.route("/api/admin/login", methods=["POST"])
def admin_login():
    data = request.get_json() or {}
    username = data.get("username")
    password = data.get("password")

    row = query_db("SELECT password FROM admin_users WHERE username=?", (username,), one=True)
    
    if row and check_password_hash(row[0], password):
        session["admin_logged_in"] = True
        return jsonify({"success": True})
    
    return jsonify({"success": False, "message": "Invalid admin credentials."}), 401

# --- Admin: 1. Chat History (Logins-Chat History) ---
@app.route("/api/admin/history", methods=["GET"])
def get_chat_history():
    if not is_admin():
        return jsonify({"success": False, "message": "Admin access required."}), 403
    
    rows = query_db(
        """
        SELECT ch.timestamp, ch.user_message, ch.detected_intent, ch.confidence
        FROM chat_history ch
        ORDER BY ch.timestamp DESC
        """
    )
    
    history = []
    for r in rows:
        timestamp_str = r[0] 
        
        # Format timestamp to YYYY-MM-DD (Date only)
        try:
            date_only = datetime.fromisoformat(timestamp_str).strftime('%Y-%m-%d')
        except ValueError:
            date_only = "N/A" 

        history.append({
            "query": r[1],
            "intent": r[2],
            "confidence": r[3],
            "date": date_only 
        })
        
    return jsonify({"success": True, "history": history})

# --- Admin: 2. Edit/Add New Queries/Intents (Training Data) ---
@app.route("/api/admin/nlu", methods=["GET"])
def get_nlu_data():
    if not is_admin():
        return jsonify({"success": False, "message": "Admin access required."}), 403
    
    # Select id, text, bot_reply, intent, timestamp
    rows = query_db("SELECT id, text, bot_reply, intent, timestamp FROM nlu_data ORDER BY timestamp DESC")
    
    data = [
        {"id": r[0], "text": r[1], "bot_reply": r[2], "intent": r[3], "timestamp": r[4]} 
        for r in rows
    ]
    return jsonify({"success": True, "data": data, "intents": get_all_intents()})

# app.py (around line 324)

@app.route("/api/admin/nlu", methods=["POST"])
def add_nlu_query():
    if not is_admin():
        return jsonify({"success": False, "message": "Admin access required."}), 403
    
    data = request.get_json() or {}
    text = data.get("text")
    intent = data.get("intent")
    bot_reply = data.get("bot_reply") # <--- Get the bot_reply field
    
    # --- CRITICAL MODIFICATION: Check for all three required fields ---
    if not (text and intent and bot_reply):
        # This will now correctly trigger if any of the three fields is missing
        return jsonify({"success": False, "message": "Query text, Bot Reply, and Intent are required."}), 400
        
    try:
        # Insert the three fields into the database
        query_db(
            "INSERT INTO nlu_data (text, intent, bot_reply, timestamp) VALUES (?, ?, ?, ?)",
            (text, intent, bot_reply, datetime.utcnow().isoformat())
        )
        return jsonify({"success": True, "message": "Query added to DB. Please re-train."})
    except sqlite3.IntegrityError:
        # This occurs if the 'text' (query) already exists due to UNIQUE constraint
        return jsonify({"success": False, "message": "Query already exists."}), 400
    except Exception as e:
        # 🚨 TEMPORARY CHANGE: Return the exact error for debugging
        print(f"Database error during NLU insert: {e}")
        return jsonify({"success": False, "message": f"Database insertion failed. Error: {str(e)}"}), 500 # <--- THIS LINE IS CHANGED
@app.route("/api/admin/nlu/<int:data_id>", methods=["DELETE"])
def delete_nlu_query(data_id):
    if not is_admin():
        return jsonify({"success": False, "message": "Admin access required."}), 403
        
    query_db("DELETE FROM nlu_data WHERE id=?", (data_id,))
    return jsonify({"success": True, "message": "Query deleted from DB. Please re-train."})

# --- Admin: Export Training Data as CSV (Combined) ---
@app.route("/api/admin/nlu/export", methods=["GET"])
def export_nlu_data():
    if not is_admin():
        return make_response(jsonify({"success": False, "message": "Admin access required."}), 403)
    
    # Fetch all combined data from the train module
    combined_data = train_module.load_combined_nlu_data()
    
    # In-memory CSV generation
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header row (matching the original CSV structure)
    writer.writerow(['text', 'intent']) 
    
    # Write data rows
    for text, intent in combined_data:
        writer.writerow([text, intent])
        
    # Create the response to force a download
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=banking_queries_combined_export.csv"
    response.headers["Content-type"] = "text/csv"
    return response

# --- Admin: 3. Retrain BankBot ---
@app.route("/api/admin/retrain", methods=["POST"])
def retrain_model():
    if not is_admin():
        return jsonify({"success": False, "message": "Admin access required."}), 403
    
    # app.py (UPDATED retrain_model route)
# ...
    try:
        # Run the training script logic, which reads CSV + DB
        train_module.train() 
        
        # 🚨 CRITICAL: Use the dedicated load function to reload the new model
        load_nlu_model(MODEL_PATH)
        
        return jsonify({"success": True, "message": "Bot successfully re-trained and deployed."})
# ...
    except Exception as e:
        print(f"Retraining error: {e}")
        return jsonify({"success": False, "message": f"Retraining failed: {str(e)}."}), 500

# =================================================================
# --- CHAT ROUTE (SINGLE, COMPLETE DEFINITION) ---
# =================================================================
@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json() or {}
    message = data.get("message", "")

    # Convert message to lowercase for consistent NLU processing
    message = message.lower()

    uid = session.get("user_id")

    # --- Recognize intent ---
    intent, score, entities = recognize_intent(message)

    # --- Check login state ---
    logged_in = session.get("logged_in", False)
    response = ""

    # --- Dialogue Management ---
    if intent == "greeting" or intent == "greeting_hi":
        response = "Hello there! How can I help you today?"

    elif intent == "goodbye" or intent == "greeting_bye":
        response = "It was nice assisting you. Have a great day!"

    elif intent == "check_balance":
        if not logged_in:
            response = "⚠️ Please login to check your balance."
        else:
            row = query_db("SELECT balance FROM users WHERE id=?", (uid,), one=True)
            balance = row[0] if row else 0
            response = f"✅ Your current balance is ₹{balance:.2f}."

    elif intent == "transfer_money":
        if not logged_in:
            response = "⚠️ Please login first to transfer money."
        else:
            account = entities.get("account_number")
            amount = entities.get("amount")
            
            if not amount and not account:
                 response = "How much do you want to transfer, and to which account?"
            elif not amount:
                response = "How much do you want to transfer?"
            elif not account:
                response = "Please provide the account number."
            else:
                result = perform_transfer(uid, account, amount) 
                response = result["reply"]

    elif intent == "account_info":
        if not logged_in:
            response = "⚠️ Please login to view account information."
        else:
            row = query_db("SELECT account_number FROM users WHERE id=?", (uid,), one=True)
            account_num = row[0] if row else 'N/A'
            response = f"Your account number is {account_num}."

    elif intent == "mini_statement":
        if not logged_in:
            response = "⚠️ Please login to get a mini statement."
        else:
            rows = query_db(
                "SELECT type, amount, description, timestamp FROM transactions WHERE user_id=? ORDER BY id DESC LIMIT 5",
                (uid,)
            )
            if not rows:
                response = "You have no transactions yet."
            else:
                statement = "📃 Mini statement:<br>"
                for r in rows:
                    type_str = "Debit" if r[0] == "debit" else "Credit"
                    # NOTE: Ensure datetime is imported from datetime
                    statement += f"{type_str} of ₹{r[1]:.2f} for {r[2]} on {datetime.fromisoformat(r[3]).strftime('%Y-%m-%d')}<br>"
                response = statement

    elif intent == "card_details":
        if not logged_in:
            response = "⚠️ Please login to check card details."
        else:
            row = query_db("SELECT card_last4 FROM users WHERE id=?", (uid,), one=True)
            card_last4 = row[0] if row else 'N/A'
            response = f"💳 You have a card ending with {card_last4}."

    elif intent == "lost_card":
        response = "I'm sorry to hear that. To block your card, please call our 24/7 helpline at 1800-123-4567 or visit our nearest branch."

    elif intent == "apply_loan":
        response = "We offer a variety of loans including personal, home, and student loans. Please visit our website or a branch to discuss your options with a loan officer."

    elif intent == "get_interest_rate":
        response = "Interest rates vary based on the loan type and current market conditions. Please contact a loan advisor for a personalized quote."

    elif intent == "get_branch_details":
        response = "You can find your nearest branch by using our branch locator tool on the website. Please provide your city or zip code for the best results."

    elif intent == "create_account":
        response = "You can open a new account online in minutes! Click the 'Register' button on the homepage or visit a branch with your ID and address proof."

    elif intent == "close_account":
        response = "To close an account, you must visit a branch and submit a formal request. Please bring your ID and account documents."

    elif intent == "unknown":
        response = "Sorry, I didn't understand that. Could you please rephrase?"
    else:
        response = "Sorry, I didn’t understand that. Could you please rephrase?"

    # --- Log the interaction to the database (NEW LOGIC) ---
    try:
        # Use session's user ID (uid) or None if not logged in
        user_id_to_log = uid if uid else None 
        
        query_db(
            """
            INSERT INTO chat_history (user_id, timestamp, user_message, bot_response, detected_intent, confidence) 
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id_to_log, datetime.utcnow().isoformat(), message, response, intent, score)
        )
    except Exception as e:
        print(f"Error logging chat history: {e}")
        # Continue execution even if logging fails

    return jsonify({
        "intent": intent,
        "confidence": score,
        "entities": entities,
        "response": response
    })


# --- Run the Flask server ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)