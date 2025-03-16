from flask import Flask, request, jsonify
from flask_cors import CORS
import re

app = Flask(__name__)
CORS(app)

# File paths
RULES_FILE_PATH = 'csv-to-clp/data/disease-symptoms.clp'

# Function to load rules from a file
def load_rules(file_path):
    """Load the rules from the given file path."""
    try:
        with open(file_path, 'r') as file:
            rules = file.read()
            print(f"Loaded rules from {file_path}")
            return rules
    except FileNotFoundError:
        print(f"Rules file not found at path: {file_path}")
        return ""

# Function to parse rules and extract disease-symptom relationships
def parse_rules(rules_text):
    """Parse the rules text to extract symptoms and diseases."""
    print("Parsing rules...")
    # Extract disease rules using regular expressions
    rules = re.findall(r'\(defrule is_it_(\w+)(.*?)=>', rules_text, re.DOTALL)
    disease_symptoms = {}

    for disease, rule in rules:
        # Extract symptoms for each disease
        symptoms = re.findall(r'\(has_symptom (\w+)\)', rule)
        disease_symptoms[disease] = set(symptoms)
        print(f"Parsed disease '{disease}' with symptoms: {symptoms}")

    return disease_symptoms

# Function to get all unique symptoms from the rules
def get_all_symptoms_from_rules(disease_symptoms):
    """Extract all unique symptoms from the rules."""
    print("Extracting all symptoms from parsed rules...")
    all_symptoms = set()
    for symptoms in disease_symptoms.values():
        all_symptoms.update(symptoms)
    print(f"All symptoms: {sorted(list(all_symptoms))}")
    return sorted(list(all_symptoms))

# Function to filter symptoms not selected yet for possible diseases
def filter_remaining_symptoms(possible_diseases, disease_symptoms, selected_symptoms):
    """Get relevant symptoms for possible diseases that haven't been selected yet."""
    if not possible_diseases:
        print("No possible diseases found, returning empty symptom list.")
        return []

    relevant_symptoms = set()
    for disease in possible_diseases:
        # Get the symptoms specific to this disease
        disease_specific_symptoms = disease_symptoms[disease]
        # Filter out already selected symptoms
        remaining = disease_specific_symptoms - set(selected_symptoms)
        relevant_symptoms.update(remaining)
    print(f"Remaining symptoms: {sorted(list(relevant_symptoms))}")
    return sorted(list(relevant_symptoms))

# Function to calculate match percentages for each disease
def calculate_disease_matches(possible_diseases, disease_symptoms, selected_symptoms):
    """Calculate match percentages for each disease."""
    print("Calculating disease match percentages...")
    matches = []
    for disease in possible_diseases:
        required_symptoms = disease_symptoms[disease]
        matched = len(set(selected_symptoms).intersection(required_symptoms))
        total = len(required_symptoms)
        match_percentage = (matched / total) * 100 if total > 0 else 0
        print(f"Disease '{disease}' match: {match_percentage}% ({matched}/{total} symptoms matched)")
        matches.append({
            'disease': disease,
            'match_percentage': match_percentage,
            'matched_symptoms': matched,
            'total_symptoms': total
        })
    return sorted(matches, key=lambda x: x['match_percentage'], reverse=True)

# API endpoint to get the initial list of symptoms
@app.route('/api/get_initial_symptoms', methods=['GET'])
def get_initial_symptoms():
    """Return initial set of symptoms."""
    try:
        all_symptoms = get_all_symptoms_from_rules(disease_symptoms)
        print("Returning initial symptoms list.")
        return jsonify({
            'status': 'success',
            'all_symptoms': all_symptoms,
            'total_symptoms': len(all_symptoms)
        })
    except Exception as e:
        print(f"Error loading initial symptoms: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# API endpoint to process selected symptoms and return possible diagnoses
@app.route('/api/diagnose', methods=['POST'])
def diagnose():
    """Process symptoms and return diagnosis with filtered symptoms."""
    try:
        data = request.get_json()
        selected_symptoms = set(data.get('symptoms', []))
        print(f"Selected symptoms for diagnosis: {selected_symptoms}")

        # Find diseases that match current symptoms
        possible_diseases = []
        for disease, symptoms in disease_symptoms.items():
            if selected_symptoms.issubset(symptoms):  # Check if all selected symptoms match this disease
                possible_diseases.append(disease)
                print(f"Possible disease found: {disease}")

        # Calculate matches and confidence
        matches = calculate_disease_matches(
            possible_diseases,
            disease_symptoms,
            selected_symptoms
        )

        # Get remaining symptoms only if we have possible diseases
        remaining_symptoms = []
        if possible_diseases:
            remaining_symptoms = filter_remaining_symptoms(
                possible_diseases,
                disease_symptoms,
                selected_symptoms
            )

        response = {
            'possible_diseases': [m['disease'] for m in matches],
            'remaining_symptoms': remaining_symptoms,
            'is_final_diagnosis': len(remaining_symptoms) == 0 and len(possible_diseases) > 0,
            'matched_symptoms': len(selected_symptoms),
            'matches': matches,
            'symptoms_per_disease': {
                d: list(disease_symptoms[d])
                for d in possible_diseases
            } if possible_diseases else {}
        }

        print(f"Diagnosis result: {response}")
        return jsonify(response)

    except Exception as e:
        print(f"Error in diagnosis: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'possible_diseases': [],
            'remaining_symptoms': [],
            'matches': [],
            'symptoms_per_disease': {}
        }), 500

if __name__ == '__main__':
    # Load rules at startup
    rules_text = load_rules(RULES_FILE_PATH)
    disease_symptoms = parse_rules(rules_text)
    print(f"Loaded {len(disease_symptoms)} diseases from rules")
    app.run(debug=True)