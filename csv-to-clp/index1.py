from flask import Flask, request, jsonify
import os
import csv
import traceback
from werkzeug.utils import secure_filename
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# File paths and structure
# Project root: Medical-Diagnosis_ExpertSystem/
# ├── csv-to-clp/     <- Current directory (where this script runs)
# │   ├── index1.py   <- This file
# │   └── uploads/    <- Where uploaded CSVs are stored (created if doesn't exist)
# └── data/           <- Where generated files are stored (created if doesn't exist)
#     ├── disease-symptoms.clp  <- Generated CLIPS rules
#     └── symptoms.txt          <- Generated symptoms list

app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['ALLOWED_EXTENSIONS'] = {'csv'}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Limit upload size to 16MB

# Output paths (absolute)
UPLOAD_DIR_ABS = os.path.abspath(app.config['UPLOAD_FOLDER'])
DATA_DIR_ABS = os.path.abspath('data')
CLP_FILE_PATH = os.path.join(DATA_DIR_ABS, 'disease-symptoms.clp')
SYMPTOMS_FILE_PATH = os.path.join(DATA_DIR_ABS, 'symptoms.txt')

print(f"DEBUG: UPLOAD directory path: {UPLOAD_DIR_ABS}")
print(f"DEBUG: DATA directory path: {DATA_DIR_ABS}")
print(f"DEBUG: CLP file path: {CLP_FILE_PATH}")
print(f"DEBUG: Symptoms file path: {SYMPTOMS_FILE_PATH}")


def allowed_file(filename):
    print(f"DEBUG: Checking if file {filename} is allowed")
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def convert_csv_to_clp(csv_path, clp_output_path, symptoms_output_path):
    """Convert CSV data to CLIPS rule format and append to existing file if present"""
    print(f"DEBUG: Starting conversion from CSV to CLP")
    print(f"DEBUG: Input CSV: {csv_path}")
    print(f"DEBUG: Output CLP: {clp_output_path}")
    print(f"DEBUG: Output symptoms: {symptoms_output_path}")

    # Create output directories if they don't exist
    os.makedirs(os.path.dirname(clp_output_path), exist_ok=True)
    os.makedirs(os.path.dirname(symptoms_output_path), exist_ok=True)

    clp_note = """; ------------------------------------------------------------------------------
; this file is generated using Python
; dataset: https://www.kaggle.com/itachi9604/disease-symptom-description-dataset
; ------------------------------------------------------------------------------
"""

    # Collect all symptoms (start with existing ones if available)
    all_symptoms = set()
    diseases_processed = 0

    # Load existing symptoms if symptoms file exists
    if os.path.exists(symptoms_output_path):
        print(f"DEBUG: Loading existing symptoms from {symptoms_output_path}")
        try:
            with open(symptoms_output_path, 'r') as symptoms_file:
                existing_symptoms = symptoms_file.read().split(",\n")
                all_symptoms.update([s for s in existing_symptoms if s])
                print(f"DEBUG: Loaded {len(all_symptoms)} existing symptoms")
        except Exception as e:
            print(f"WARNING: Error loading existing symptoms: {str(e)}")

    # Check if CLP file exists and determine write mode
    file_exists = os.path.exists(clp_output_path)
    open_mode = 'a' if file_exists else 'w'
    print(f"DEBUG: CLP file {'exists' if file_exists else 'does not exist'}, opening in {open_mode} mode")

    try:
        with open(csv_path, 'r') as csvfile:
            # Read CSV data
            print(f"DEBUG: Reading CSV file: {csv_path}")
            csv_reader = csv.reader(csvfile)
            next(csv_reader)  # Skip header row
            print("DEBUG: Skipped header row")

            with open(clp_output_path, open_mode) as clp_file:
                # Write the header note only if creating a new file
                if not file_exists:
                    clp_file.write(clp_note)
                    print("DEBUG: Wrote header note to new CLP file")

                for line_number, row in enumerate(csv_reader, 1):
                    print(f"DEBUG: Processing row {line_number}: {row}")
                    line = [item.strip() for item in row if item.strip()]
                    print(f"DEBUG: Cleaned line: {line}")

                    if not line:
                        print("DEBUG: Empty line, skipping")
                        continue

                    disease = {
                        "name": line[0],
                        "nameWithUnderscore": line[0].replace(" ", "_"),
                        "symptoms": [symptom.replace(" ", "") for symptom in line[1:5] if symptom.strip()]
                    }
                    print(f"DEBUG: Disease object created: {disease}")

                    if not disease["symptoms"]:
                        print("DEBUG: No symptoms found, skipping disease")
                        continue

                    # Format exactly like in JS
                    symptoms_text = "\n  ".join([f"(has_symptom {symptom})" for symptom in disease["symptoms"]])
                    print(f"DEBUG: Formatted symptoms: {symptoms_text}")

                    clp_format = f"""
(defrule {disease["nameWithUnderscore"]}
  (disease_is {disease["nameWithUnderscore"]})
  =>
  (printout t "{disease["name"]}" crlf)
)

(defrule is_it_{disease["nameWithUnderscore"]}
  {symptoms_text}
  =>
  (assert (disease_is {disease["nameWithUnderscore"]}))
)
  """
                    print(f"DEBUG: Appending CLP rule for {disease['name']}")
                    clp_file.write(clp_format)
                    diseases_processed += 1

                    # Add to symptoms set
                    for symptom in disease["symptoms"]:
                        all_symptoms.add(symptom)

                print(f"DEBUG: Processed {diseases_processed} diseases in total")

        # Write symptoms file (always overwrite to ensure consistency)
        print(f"DEBUG: Writing {len(all_symptoms)} symptoms to {symptoms_output_path}")
        with open(symptoms_output_path, 'w') as symptoms_file:
            symptoms_file.write(",\n".join(sorted(all_symptoms)))
            print("DEBUG: Symptoms file written successfully")

        result = {
            'diseases_count': diseases_processed,
            'symptoms_count': len(all_symptoms),
            'symptoms': sorted(list(all_symptoms))[:10]  # Return first 10 for preview
        }
        print(f"DEBUG: Conversion completed with result: {result}")
        return result
    except Exception as e:
        print(f"ERROR: Exception in convert_csv_to_clp: {str(e)}")
        print(traceback.format_exc())
        error_message = f"Error converting CSV to CLP: {str(e)}"
        raise ValueError(error_message)


@app.route('/', methods=['GET'])
def index():
    print("DEBUG: Root endpoint accessed")
    return jsonify({'status': 'online', 'message': 'Server is running'}), 200

@app.route('/api/feedback', methods=['POST'])
def process_feedback():
    try:
        data = request.get_json()

        # Extract data from request
        disease_name = data.get('disease')
        is_satisfied = data.get('isSatisfied')
        missed_symptoms = data.get('missedSymptoms', '')

        print(f"Processing feedback for {disease_name}, satisfied: {is_satisfied}")

        # If satisfied or no missed symptoms, just log and return success
        if is_satisfied or not missed_symptoms:
            return jsonify({
                'status': 'success',
                'message': 'Feedback recorded successfully'
            })

        # Convert disease name to expected format in rules
        rule_disease_name = disease_name.replace(' ', '_')

        # Path to the rules file
        clp_file_path = CLP_FILE_PATH

        # Read the current file content
        with open(clp_file_path, 'r') as file:
            content = file.read()

        # Find the disease rule
        import re
        pattern = rf'(\(defrule is_it_{rule_disease_name}\s*[^=]*=>)'
        rule_match = re.search(pattern, content, re.DOTALL)

        if not rule_match:
            return jsonify({
                'status': 'error',
                'message': f'Disease rule for {disease_name} not found'
            }), 404

        # Process the symptoms to add - properly handle comma separated values
        raw_symptoms = [s.strip() for s in missed_symptoms.split(',') if s.strip()]
        # Format symptoms according to CLIPS rules (replace spaces with nothing, add suffix '1')
        symptoms_to_add = [f"{symptom.replace(' ', '')}" for symptom in raw_symptoms]

        # Generate symptom lines to add
        symptom_lines = '\n  '.join([f"(has_symptom {symptom})" for symptom in symptoms_to_add])

        # Insert the new symptoms before the "=>" part
        current_rule = rule_match.group(1)
        insertion_point = current_rule.rfind(')')
        updated_rule = current_rule[:insertion_point + 1] + f"\n  {symptom_lines}" + current_rule[insertion_point + 1:]

        # Replace the old rule with the updated one
        updated_content = content.replace(rule_match.group(1), updated_rule)

        # Write the updated content back to the file
        with open(clp_file_path, 'w') as file:
            file.write(updated_content)

        return jsonify({
            'status': 'success',
            'message': f'Added {len(symptoms_to_add)} symptoms to {disease_name}',
            'added_symptoms': symptoms_to_add
        })

    except Exception as e:
        print(f"Error processing feedback: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
@app.route('/api/healthcheck', methods=['GET'])
def healthcheck():
    """Health check endpoint to verify server status"""
    try:
        return jsonify({
            'status': 'ok',
            'message': 'Server is running'
        }), 200
    except Exception as e:
        print(f"ERROR: Health check failed: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
@app.route('/api/upload_csv', methods=['POST'])
def upload_csv():
    print("DEBUG: Upload CSV endpoint accessed")

    if 'file' not in request.files:
        print("ERROR: No file part in the request")
        return jsonify({'message': 'No file part in the request'}), 400

    file = request.files['file']
    print(f"DEBUG: File received: {file.filename}")

    if file.filename == '':
        print("ERROR: No selected file")
        return jsonify({'message': 'No selected file'}), 400

    if not file or not allowed_file(file.filename):
        print(f"ERROR: Invalid file type: {file.filename}")
        return jsonify({'message': 'Invalid file type. Only CSV files are allowed.'}), 400

    try:
        # Create upload folder if it doesn't exist
        os.makedirs(UPLOAD_DIR_ABS, exist_ok=True)
        print(f"DEBUG: Upload directory ensured: {UPLOAD_DIR_ABS}")

        # Secure and save the file
        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_DIR_ABS, filename)
        file.save(file_path)
        print(f"DEBUG: File saved at: {file_path}")

        # Verify file exists and has content
        if not os.path.exists(file_path):
            print(f"ERROR: File not found after save: {file_path}")
            return jsonify({'message': 'File upload failed or file is empty'}), 400

        file_size = os.path.getsize(file_path)
        print(f"DEBUG: File size: {file_size} bytes")
        if file_size == 0:
            print("ERROR: Uploaded file is empty")
            return jsonify({'message': 'File upload failed or file is empty'}), 400

        # Process the CSV file and generate CLIPS rules
        os.makedirs(DATA_DIR_ABS, exist_ok=True)
        print(f"DEBUG: Data directory ensured: {DATA_DIR_ABS}")

        print("DEBUG: Starting CSV to CLP conversion")
        result = convert_csv_to_clp(file_path, CLP_FILE_PATH, SYMPTOMS_FILE_PATH)
        print(f"DEBUG: Conversion completed successfully: {result}")

        return jsonify({
            'message': f'File uploaded and processed successfully! Generated rules for {result["diseases_count"]} diseases with {result["symptoms_count"]} unique symptoms.',
            'details': {
                'diseasesCount': result["diseases_count"],
                'symptomsCount': result["symptoms_count"],
                'symptomsSample': result["symptoms"]
            }
        }), 200
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"ERROR: Exception in upload_csv: {str(e)}")
        print(error_trace)
        return jsonify({
            'message': f'Failed to process file: {str(e)}',
            'error_detail': error_trace
        }), 500

import re


@app.route('/api/knowledge_base', methods=['GET'])
def get_knowledge_base():
    """Fetch all diseases and their symptoms from the CLIPS file"""
    try:
        # Check if file exists
        if not os.path.exists(CLP_FILE_PATH):
            print(f"DEBUG: Knowledge base file not found at {CLP_FILE_PATH}")
            return jsonify([]), 200

        # Read the CLIPS file
        with open(CLP_FILE_PATH, 'r') as file:
            content = file.read()
            print(f"DEBUG: Loaded CLIPS file, size: {len(content)} bytes")

        # Parse the rules to extract diseases and their symptoms
        knowledge_base = []
        print("DEBUG: Extracting diseases and symptoms from CLIPS rules")

        # More flexible regex pattern to handle different formatting in the file
        disease_pattern = r'\(defrule\s+is_it_([A-Za-z0-9_-]+)\s+(.*?)\s*=>'
        disease_matches = re.finditer(disease_pattern, content, re.DOTALL)

        disease_count = 0
        for idx, match in enumerate(disease_matches):
            disease_count += 1
            disease_id = idx + 1
            disease_name = match.group(1).replace('_', ' ')
            symptom_pattern = r'\(has_symptom\s+([A-Za-z0-9_-]+)\)'
            symptoms = re.findall(symptom_pattern, match.group(2))

            print(f"DEBUG: Found disease #{disease_id}: {disease_name} with {len(symptoms)} symptoms")

            knowledge_base.append({
                'id': disease_id,
                'disease': disease_name,
                'symptoms': symptoms
            })

        print(f"DEBUG: Total diseases extracted: {disease_count}")

        # Check for potential missed patterns
        all_rules = re.findall(r'\(defrule\s+is_it_([A-Za-z0-9_-]+)', content)
        print(f"DEBUG: Total 'is_it_' rules found in file: {len(all_rules)}")

        if len(all_rules) > disease_count:
            print(
                f"DEBUG: Warning! Not all diseases were captured. Found {len(all_rules)} rule definitions but only extracted {disease_count}")

        return jsonify(knowledge_base), 200
    except Exception as e:
        print(f"ERROR: Failed to fetch knowledge base: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500
@app.route('/api/add_symptom', methods=['POST'])
def add_symptom():
    """Add a symptom to a disease"""
    try:
        data = request.get_json()
        disease_id = data.get('diseaseId')
        symptom = data.get('symptom', '').replace(' ', '')

        if not symptom:
            return jsonify({'error': 'Symptom cannot be empty'}), 400

        # Get current knowledge base
        response = app.test_client().get('/api/knowledge_base')
        knowledge_base = response.get_json()

        # Find the disease by ID
        disease = next((d for d in knowledge_base if d['id'] == disease_id), None)
        if not disease:
            return jsonify({'error': f'Disease with ID {disease_id} not found'}), 404

        # Format disease name for the rule pattern
        rule_disease_name = disease['disease'].replace(' ', '_')

        # Read the current file content
        with open(CLP_FILE_PATH, 'r') as file:
            content = file.read()

        # Find the complete disease rule with a more robust pattern
        pattern = rf'\(defrule\s+is_it_{re.escape(rule_disease_name)}([\s\S]*?)=>\s*([\s\S]*?)\)'
        rule_match = re.search(pattern, content, re.DOTALL)

        if not rule_match:
            return jsonify({'error': f'Disease rule for {disease["disease"]} not found'}), 404

        # Check if symptom already exists
        symptom_pattern = rf'\(has_symptom\s+{re.escape(symptom)}\)'
        if re.search(symptom_pattern, rule_match.group(0)):
            return jsonify({'status': 'info', 'message': f'Symptom {symptom} already exists for {disease["disease"]}'}), 200

        # Get the whole rule and parts for reconstruction
        whole_rule = rule_match.group(0)
        before_arrow = rule_match.group(1)
        after_arrow = rule_match.group(2)

        # Create updated rule with new symptom
        new_rule = f'(defrule is_it_{rule_disease_name}{before_arrow}  (has_symptom {symptom})\n=>{after_arrow})'

        # Replace the old rule with the updated one
        updated_content = content.replace(whole_rule, new_rule)

        # Write back to file
        with open(CLP_FILE_PATH, 'w') as file:
            file.write(updated_content)

        return jsonify({
            'status': 'success',
            'message': f'Added symptom {symptom} to {disease["disease"]}'
        }), 200
    except Exception as e:
        print(f"Error adding symptom: {str(e)}")
        print(traceback.format_exc())  # Add for better debugging
        return jsonify({'error': str(e)}), 500
@app.route('/api/remove_symptom', methods=['POST'])
def remove_symptom():
    """Remove a symptom from a disease"""
    try:
        data = request.get_json()
        disease_id = data.get('diseaseId')
        symptom = data.get('symptom')

        # Get current knowledge base
        response = app.test_client().get('/api/knowledge_base')
        knowledge_base = response.get_json()

        # Find the disease by ID
        disease = next((d for d in knowledge_base if d['id'] == disease_id), None)
        if not disease:
            return jsonify({'error': f'Disease with ID {disease_id} not found'}), 404

        # Format disease name for rule matching
        rule_disease_name = disease['disease'].replace(' ', '_')

        # Read the current file content
        with open(CLP_FILE_PATH, 'r') as file:
            content = file.read()

        # Pattern to match the symptom line in the specific disease rule
        symptom_pattern = rf'(\(defrule is_it_{rule_disease_name}\s*[^=]*)(\n\s*\(has_symptom\s+{symptom}\))(.*=>)'
        content = re.sub(symptom_pattern, r'\1\3', content, flags=re.DOTALL)

        # Write updated content back
        with open(CLP_FILE_PATH, 'w') as file:
            file.write(content)

        return jsonify({'status': 'success', 'message': f'Removed symptom {symptom} from {disease["disease"]}'}), 200
    except Exception as e:
        print(f"Error removing symptom: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/add_disease', methods=['POST'])
def add_disease():
    """Add a new disease with symptoms"""
    try:
        data = request.get_json()
        disease_name = data.get('name', '').strip()
        symptoms = [s.strip().replace(' ', '') for s in data.get('symptoms', []) if s.strip()]

        if not disease_name or not symptoms:
            return jsonify({'error': 'Disease name and at least one symptom are required'}), 400

        # Format disease name for CLIPS
        rule_disease_name = disease_name.replace(' ', '_')

        # Format symptoms for the rule
        symptoms_text = "\n  ".join([f"(has_symptom {symptom})" for symptom in symptoms])

        # Create the new disease rule
        new_rule = f"""
(defrule {rule_disease_name}
  (disease_is {rule_disease_name})
  =>
  (printout t "{disease_name}" crlf)
)

(defrule is_it_{rule_disease_name}
  {symptoms_text}
  =>
  (assert (disease_is {rule_disease_name}))
)
"""

        # Append the new rule to the file
        with open(CLP_FILE_PATH, 'a') as file:
            file.write(new_rule)

        return jsonify({
            'status': 'success',
            'message': f'Added new disease: {disease_name} with {len(symptoms)} symptoms'
        }), 200
    except Exception as e:
        print(f"Error adding disease: {str(e)}")
        return jsonify({'error': str(e)}), 500
if __name__ == '__main__':
    print("\n" + "="*80)
    print("DEBUG: Starting Flask server on port 5001")
    print("DEBUG: Server paths:")
    print(f"- Upload directory: {UPLOAD_DIR_ABS}")
    print(f"- Data directory: {DATA_DIR_ABS}")
    print("="*80 + "\n")
    app.run(debug=True, port=5001)