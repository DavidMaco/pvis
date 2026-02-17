import spacy

# Load NLP model (download en_core_web_sm if needed)
nlp = spacy.load('en_core_web_sm')

def analyze_contract(text):
    """Extract key information from contract text using NLP."""
    doc = nlp(text)
    entities = {'ORG': [], 'MONEY': [], 'DATE': []}
    for ent in doc.ents:
        if ent.label_ in entities:
            entities[ent.label_].append(ent.text)
    # Simple keyword extraction for terms
    terms = []
    if 'penalty' in text.lower():
        terms.append('Penalty Clause')
    if 'termination' in text.lower():
        terms.append('Termination Clause')
    return {'entities': entities, 'key_terms': terms}

def generate_rfp_response(requirements):
    """Simulate RFP response generation."""
    # In real, use templates or AI
    response = f"Proposal for {requirements}: We offer competitive pricing and reliable delivery."
    return response

if __name__ == '__main__':
    sample_contract = "This contract with Supplier A for $10,000 is effective from 2023-01-01. Includes penalty for late delivery."
    analysis = analyze_contract(sample_contract)
    print("Contract Analysis:", analysis)
    rfp_resp = generate_rfp_response("Raw Materials Supply")
    print("RFP Response:", rfp_resp)