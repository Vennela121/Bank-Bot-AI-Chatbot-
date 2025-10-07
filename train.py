import csv
import os
import spacy
from spacy.training import Example
from spacy.util import minibatch, compounding
import sqlite3
from pathlib import Path
# --- Paths ---
APP_ROOT = os.path.dirname(__file__)
CSV_PATH = os.path.join(APP_ROOT, "banking_queries.csv")
DB_PATH = os.path.join(APP_ROOT, "data.db")
MODEL_PATH = os.path.join(APP_ROOT, "models", "nlu_model")
Path(os.path.dirname(MODEL_PATH)).mkdir(parents=True, exist_ok=True) # Ensure models directory exists



# --- Helper function to load data from CSV ---
def load_csv_nlu_data():
    csv_data = []
    try:
        with open(CSV_PATH, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                text = row.get('text', '').strip()
                intent = row.get('intent', '').strip()
                if text and intent:
                    csv_data.append((text, intent))
    except FileNotFoundError:
        print(f"Warning: {CSV_PATH} not found. Using only DB data.")
    except Exception as e:
        print(f"Error reading CSV file: {e}")
    return csv_data

# --- Helper function to load data from DB (Admin-added) ---
def load_db_nlu_data():
    db_data = []
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT text, intent FROM nlu_data")
        db_data = c.fetchall()
        conn.close()
    except sqlite3.OperationalError:
        print("Warning: Database or nlu_data table not found. Using only CSV data.")
    except Exception as e:
        print(f"Error reading DB nlu_data: {e}")
    return db_data

# --- Helper function to load ALL data (CSV + DB) ---
def load_combined_nlu_data():
    csv_data = load_csv_nlu_data()
    db_data = load_db_nlu_data()
    
    # Use a dictionary to store combined data and automatically handle duplicates
    combined = {}
    for text, intent in csv_data + db_data:
        # Ensure text is lowercase for consistency
        combined[text.lower()] = intent
        
    return list(combined.items()) # Returns [(text, intent), ...]

# --- Helper function to get intents from ALL data ---
def get_intents_from_combined_source():
    intents = set()
    for _, intent in load_combined_nlu_data():
        if intent:
            intents.add(intent)
    return list(intents)

# --- Training function ---

# --- Training function (Modified) ---
def train(iterations=20):
    # Load all training data (CSV + DB)
    TRAIN_DATA_LIST = load_combined_nlu_data()
    ALL_INTENTS = get_intents_from_combined_source()

    if not TRAIN_DATA_LIST:
        print("No training data found in CSV or DB. Training aborted.")
        return

    print(f"Building and training NLU model with {len(TRAIN_DATA_LIST)} combined examples...")
    
    # Prepare data for spaCy
    TRAIN_DATA = []
    for text, intent in TRAIN_DATA_LIST:
        cats = {i: 0.0 for i in ALL_INTENTS} 
        if intent in cats:
            cats[intent] = 1.0
            TRAIN_DATA.append((text, {"cats": cats}))
        else:
             print(f"Warning: Intent '{intent}' not in ALL_INTENTS set.")

    # Build the model
    nlp = spacy.blank("en")
    textcat = nlp.add_pipe("textcat_multilabel", last=True)

    # Add labels
    for intent in ALL_INTENTS:
        textcat.add_label(intent)

    # Convert to spaCy's training format
    examples = [Example.from_dict(nlp.make_doc(text), annotations) for text, annotations in TRAIN_DATA]

    # Start training
    optimizer = nlp.begin_training()
    for i in range(iterations):
        losses = {}
        batches = minibatch(examples, size=compounding(4.0, 32.0, 1.001))
        for batch in batches:
            nlp.update(batch, drop=0.2, losses=losses)
    
        # print(f"Epoch {i+1} - Losses: {losses}") # Keep this print optional for clarity
    
    # Save the trained model
    nlp.to_disk(MODEL_PATH)
    print("\nTraining complete.")
    print(f"Model saved to: {MODEL_PATH}")

    # Test the model... (Your existing test logic remains)

if __name__ == "__main__":
    train()

