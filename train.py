import csv
import os
import spacy
from spacy.training import Example
from spacy.util import minibatch, compounding

# --- Paths ---
APP_ROOT = os.path.dirname(__file__)
CSV_PATH = os.path.join(APP_ROOT, "banking_queries.csv")
MODEL_PATH = os.path.join(APP_ROOT, "models", "nlu_model")

# --- Helper function to get intents from CSV ---
def get_intents_from_csv():
    intents = set()
    try:
        with open(CSV_PATH, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if 'intent' in row and row['intent']:
                    intents.add(row['intent'])
    except FileNotFoundError:
        print(f"Error: {CSV_PATH} not found.")
        return None
    return list(intents)

# --- Training function ---
def train():
    if not os.path.exists(CSV_PATH):
        print(f"Error: The file '{CSV_PATH}' was not found. Please ensure it's in the correct directory.")
        return

    # Check for required columns
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        if 'text' not in reader.fieldnames or 'intent' not in reader.fieldnames:
            print("Error: The CSV file must contain 'text' and 'intent' columns.")
            return

    # Load data from CSV
    TRAIN_DATA = []
    try:
        with open(CSV_PATH, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                text = row['text']
                intent = row['intent']
                if text and intent:
                    cats = {i: 0.0 for i in get_intents_from_csv()}
                    cats[intent] = 1.0
                    TRAIN_DATA.append((text, {"cats": cats}))
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return

    if not TRAIN_DATA:
        print("No training data found in the CSV. Please check the file.")
        return

    print("Building and training NLU model...")

    # Build the model
    nlp = spacy.blank("en")
    nlp.add_pipe("textcat_multilabel", last=True)
    textcat = nlp.get_pipe("textcat_multilabel")

    # Add labels
    for text, annotations in TRAIN_DATA:
        for cat in annotations["cats"]:
            textcat.add_label(cat)

    # Convert to spaCy's training format
    examples = [Example.from_dict(nlp.make_doc(text), annotations) for text, annotations in TRAIN_DATA]

    # Start training
    optimizer = nlp.begin_training()
    for i in range(20):
        losses = {}
        batches = minibatch(examples, size=compounding(4.0, 32.0, 1.001))
        for batch in batches:
            nlp.update(batch, drop=0.2, losses=losses)

        print(f"Epoch {i+1} - Losses: {losses}")
    
    # Save the trained model
    nlp.to_disk(MODEL_PATH)
    print("\nTraining complete.")
    print(f"Model saved to: {MODEL_PATH}")

    # Test the model with some examples from the training data
    print("\nTesting the trained model...")
    test_texts = [
        "What is my balance?",
        "I need to transfer money.",
        "How can I apply for a loan?",
        "Hello",
        "bye",
        "..."
    ]
    for test_text in test_texts:
        doc = nlp(test_text)
        print(f"Text: {test_text}")
        print(f"Predicted Intent: {doc.cats}")
        print("-" * 20)

if __name__ == "__main__":
    train()

