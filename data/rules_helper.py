from flask import Flask, request, jsonify
from flask_cors import CORS
import re

app = Flask(__name__)
CORS(app)

# File paths
RULES_FILE_PATH = 'data/disease-symptoms.clp'
SYMPTOMS_FILE_PATH = 'data/symptoms.txt'

def load_rules(file_path):
    """Load the rules from the given file path."""
    try:
        with open(file_path, 'r') as file:
            return file.read()
    except FileNotFoundError:
        print(f"Rules file not found at path: {file_path}")
        return ""

def parse_rules(rules_text):
    """Parse the rules text to extract symptoms and diseases."""
    rules = re.findall(r'\(defrule is_it_(\w+)(.*?)=>', rules_text, re.DOTALL)
    disease_symptoms = {}

    for disease, rule in rules:
        symptoms = re.findall(r'\(has_symptom (\w+)\)', rule)
        disease_symptoms[disease] = set(symptoms)

    return disease_symptoms

def suggest_diseases(symptoms, disease_symptoms):
    """Suggest possible diseases based on the input symptoms."""
    possible_diseases = []
    for disease, symptoms_set in disease_symptoms.items():
        if symptoms_set.issuperset(symptoms):
            possible_diseases.append(disease)
    return possible_diseases

def filter_symptoms(diseases, disease_symptoms, selected_symptoms):
    """Return relevant symptoms for the possible diseases, excluding already selected ones."""
    if not diseases:
        return []

    # Get all symptoms for possible diseases
    relevant_symptoms = set()
    for disease in diseases:
        relevant_symptoms.update(disease_symptoms[disease])

    # Remove already selected symptoms
    available_symptoms = relevant_symptoms - selected_symptoms
    return sorted(available_symptoms)

# Load rules at startup
rules_text = load_rules(RULES_FILE_PATH)
disease_symptoms = parse_rules(rules_text)


@app.route('/api/get_initial_symptoms', methods=['GET'])
def get_initial_symptoms():
    """Return all unique symptoms from the rules."""
    all_symptoms = set()
    for symptoms_set in disease_symptoms.values():
        all_symptoms.update(symptoms_set)
    return jsonify({'all_symptoms': sorted(list(all_symptoms))})


@app.route('/api/diagnose', methods=['POST'])
def diagnose():
    """Process symptoms and return diagnosis information."""
    data = request.get_json()
    selected_symptoms = set(data.get('symptoms', []))

    # Get possible diseases based on current symptoms
    possible_diseases = suggest_diseases(selected_symptoms, disease_symptoms)

    # Check which diseases have all their required symptoms matched
    final_diseases = []
    for disease in possible_diseases:
        required_symptoms = disease_symptoms[disease]
        if selected_symptoms.issuperset(required_symptoms):
            final_diseases.append(disease)

    # Get filtered symptoms based on possible diseases
    filtered_symptoms = []
    if not final_diseases:
        remaining_symptoms = filter_symptoms(possible_diseases, disease_symptoms, selected_symptoms)
        filtered_symptoms = [s for s in remaining_symptoms if s not in selected_symptoms]

    print(f"Debug - Selected symptoms: {selected_symptoms}")
    print(f"Debug - Possible diseases: {possible_diseases}")
    print(f"Debug - Final diseases: {final_diseases}")
    print(f"Debug - Filtered symptoms: {filtered_symptoms}")

    response = {
        'possible_diseases': final_diseases if final_diseases else possible_diseases,
        'remaining_symptoms': filtered_symptoms,
        'is_final_diagnosis': len(final_diseases) > 0,
        'selected_symptoms': list(selected_symptoms),
        'matched_symptoms': len(selected_symptoms),
        'symptoms_per_disease': {d: list(disease_symptoms[d]) for d in possible_diseases}
    }

    return jsonify(response)
if __name__ == '__main__':
    app.run(debug=True)
