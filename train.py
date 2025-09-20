# train_nlu.py
import random
import spacy
from spacy.util import minibatch, compounding
from spacy.training import Example
import os

# Define labels (intents)
LABELS = [
    "transfer_money",
    "check_balance",
    "mini_statement",
    "card_details",
    "greeting",
    "account_info"
]

# Training dataset
TRAIN_DATA = [
    # --- check_balance ---
    ("What's my account balance?", {"cats": {"check_balance": 1.0, "transfer_money": 0.0, "mini_statement": 0.0, "card_details": 0.0, "greeting": 0.0, "account_info": 0.0}}),
    ("Show balance", {"cats": {"check_balance": 1.0, "transfer_money": 0.0, "mini_statement": 0.0, "card_details": 0.0, "greeting": 0.0, "account_info": 0.0}}),
    ("How much money do I have?", {"cats": {"check_balance": 1.0, "transfer_money": 0.0, "mini_statement": 0.0, "card_details": 0.0, "greeting": 0.0, "account_info": 0.0}}),
    ("Tell me my balance", {"cats": {"check_balance": 1.0, "transfer_money": 0.0, "mini_statement": 0.0, "card_details": 0.0, "greeting": 0.0, "account_info": 0.0}}),
    ("Current balance please", {"cats": {"check_balance": 1.0, "transfer_money": 0.0, "mini_statement": 0.0, "card_details": 0.0, "greeting": 0.0, "account_info": 0.0}}),

    # --- transfer_money ---
    ("Please transfer ₹500 to account 4532", {"cats": {"transfer_money": 1.0, "check_balance": 0.0, "mini_statement": 0.0, "card_details": 0.0, "greeting": 0.0, "account_info": 0.0}}),
    ("Send 200 rupees to 9876", {"cats": {"transfer_money": 1.0, "check_balance": 0.0, "mini_statement": 0.0, "card_details": 0.0, "greeting": 0.0, "account_info": 0.0}}),
    ("Move 1000 from my savings to checking", {"cats": {"transfer_money": 1.0, "check_balance": 0.0, "mini_statement": 0.0, "card_details": 0.0, "greeting": 0.0, "account_info": 0.0}}),
    ("Transfer five hundred to account number 6543", {"cats": {"transfer_money": 1.0, "check_balance": 0.0, "mini_statement": 0.0, "card_details": 0.0, "greeting": 0.0, "account_info": 0.0}}),
    ("Send ₹2500 to my friend’s account 1122", {"cats": {"transfer_money": 1.0, "check_balance": 0.0, "mini_statement": 0.0, "card_details": 0.0, "greeting": 0.0, "account_info": 0.0}}),
    ("I want to transfer $500 from my savings account to checking account 4532", {"cats": {"transfer_money": 1.0, "check_balance": 0.0, "mini_statement": 0.0, "card_details": 0.0, "greeting": 0.0, "account_info": 0.0}}),

    # --- mini_statement ---
    ("Give me mini statement", {"cats": {"mini_statement": 1.0, "check_balance": 0.0, "transfer_money": 0.0, "card_details": 0.0, "greeting": 0.0, "account_info": 0.0}}),
    ("Last three transactions", {"cats": {"mini_statement": 1.0, "check_balance": 0.0, "transfer_money": 0.0, "card_details": 0.0, "greeting": 0.0, "account_info": 0.0}}),
    ("Show my recent activity", {"cats": {"mini_statement": 1.0, "check_balance": 0.0, "transfer_money": 0.0, "card_details": 0.0, "greeting": 0.0, "account_info": 0.0}}),
    ("What are my last 5 debits?", {"cats": {"mini_statement": 1.0, "check_balance": 0.0, "transfer_money": 0.0, "card_details": 0.0, "greeting": 0.0, "account_info": 0.0}}),
    ("Show me my latest transactions", {"cats": {"mini_statement": 1.0, "check_balance": 0.0, "transfer_money": 0.0, "card_details": 0.0, "greeting": 0.0, "account_info": 0.0}}),

    # --- card_details ---
    ("Card details", {"cats": {"card_details": 1.0, "check_balance": 0.0, "transfer_money": 0.0, "mini_statement": 0.0, "greeting": 0.0, "account_info": 0.0}}),
    ("What’s my card number?", {"cats": {"card_details": 1.0, "check_balance": 0.0, "transfer_money": 0.0, "mini_statement": 0.0, "greeting": 0.0, "account_info": 0.0}}),
    ("Tell me my card info", {"cats": {"card_details": 1.0, "check_balance": 0.0, "transfer_money": 0.0, "mini_statement": 0.0, "greeting": 0.0, "account_info": 0.0}}),
    ("I lost my debit card", {"cats": {"card_details": 1.0, "check_balance": 0.0, "transfer_money": 0.0, "mini_statement": 0.0, "greeting": 0.0, "account_info": 0.0}}),
    ("Show me last four digits of my card", {"cats": {"card_details": 1.0, "check_balance": 0.0, "transfer_money": 0.0, "mini_statement": 0.0, "greeting": 0.0, "account_info": 0.0}}),

    # --- greeting ---
    ("Hey", {"cats": {"greeting": 1.0, "check_balance": 0.0, "transfer_money": 0.0, "mini_statement": 0.0, "card_details": 0.0, "account_info": 0.0}}),
    ("Hello", {"cats": {"greeting": 1.0, "check_balance": 0.0, "transfer_money": 0.0, "mini_statement": 0.0, "card_details": 0.0, "account_info": 0.0}}),
    ("Hi bot", {"cats": {"greeting": 1.0, "check_balance": 0.0, "transfer_money": 0.0, "mini_statement": 0.0, "card_details": 0.0, "account_info": 0.0}}),
    ("Good morning", {"cats": {"greeting": 1.0, "check_balance": 0.0, "transfer_money": 0.0, "mini_statement": 0.0, "card_details": 0.0, "account_info": 0.0}}),
    ("Yo!", {"cats": {"greeting": 1.0, "check_balance": 0.0, "transfer_money": 0.0, "mini_statement": 0.0, "card_details": 0.0, "account_info": 0.0}}),

    # --- account_info ---
    ("What is my account number", {"cats": {"account_info": 1.0, "check_balance": 0.0, "transfer_money": 0.0, "mini_statement": 0.0, "card_details": 0.0, "greeting": 0.0}}),
    ("Tell me my account details", {"cats": {"account_info": 1.0, "check_balance": 0.0, "transfer_money": 0.0, "mini_statement": 0.0, "card_details": 0.0, "greeting": 0.0}}),
    ("Show account info", {"cats": {"account_info": 1.0, "check_balance": 0.0, "transfer_money": 0.0, "mini_statement": 0.0, "card_details": 0.0, "greeting": 0.0}}),
    ("What’s my account ID?", {"cats": {"account_info": 1.0, "check_balance": 0.0, "transfer_money": 0.0, "mini_statement": 0.0, "card_details": 0.0, "greeting": 0.0}}),
    ("Account number please", {"cats": {"account_info": 1.0, "check_balance": 0.0, "transfer_money": 0.0, "mini_statement": 0.0, "card_details": 0.0, "greeting": 0.0}}),
]

def train(output_dir="models/nlu_model", n_iter=20):
    """Train a spaCy NLU model for intent classification."""

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    nlp = spacy.blank("en")

    if "textcat" not in nlp.pipe_names:
        textcat = nlp.add_pipe("textcat", last=True)
    else:
        textcat = nlp.get_pipe("textcat")

    for label in LABELS:
        textcat.add_label(label)

    optimizer = nlp.begin_training()
    print("Training the intent classifier...")

    for epoch in range(n_iter):
        random.shuffle(TRAIN_DATA)
        losses = {}
        batches = minibatch(TRAIN_DATA, size=compounding(4.0, 32.0, 1.5))

        for batch in batches:
            examples = []
            for text, annotations in batch:
                doc = nlp.make_doc(text)
                example = Example.from_dict(doc, annotations)
                examples.append(example)

            nlp.update(examples, sgd=optimizer, drop=0.2, losses=losses)

        print(f"Epoch {epoch+1}/{n_iter} - Losses: {losses}")

    nlp.to_disk(output_dir)
    print(f"Saved trained model to: {output_dir}")

if __name__ == "__main__":
    train()