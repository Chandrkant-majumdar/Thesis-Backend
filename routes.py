import os

from flask import Blueprint, render_template, request, jsonify, redirect
import logging

def main_routes(engine, info):
    routes = Blueprint('routes', __name__)

    @routes.route('/', methods=['GET', 'POST'])
    def home():
        return render_template('index.html', symptomList=engine.getSymptomList())

    @routes.route('/addNewSymptom', methods=['POST'])
    def addNewSymptom():
        try:
            new_symptom = request.form['new_symptom'].replace(' ', '_').lower()
            disease_name = f"is_it_{request.form['diseaseName'].replace(' ', '_').lower()}"

            engine.add_new_symptom(disease_name, new_symptom)
            return redirect('/')
        except Exception as e:
            logging.error(f"Error adding new symptom: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500

    @routes.route('/addNewDisease', methods=['POST'])
    def addNewDisease():
        try:
            data = request.json
            disease_name = data['diseaseName'].strip().replace(' ', '_').lower()
            disease_description = data['diseaseDescription'].strip()
            disease_precautions = [prec.strip() for prec in data['diseasePrecautions'].split(',')]
            new_symptoms = [sym.strip().replace(' ', '_').lower() for sym in data['newSymptoms'].split(',')]

            disease_exists = any(f"(defrule {disease_name}" in line for line in open(engine.diseasePath))
            if disease_exists:
                return jsonify({'status': 'error', 'message': f"Disease '{disease_name.replace('_', ' ')}' already exists."}), 409

            with open(os.path.join(engine.dataPath, 'symptoms.txt'), "a") as f:
                for symptom in new_symptoms:
                    if symptom not in engine.getSymptoms():
                        f.write(f"{symptom},\n")

            with open(os.path.join(engine.dataPath, 'disease-description.csv'), "a") as f:
                f.write(f"{disease_name.replace('_', ' ')},{disease_description}\n")

            with open(os.path.join(engine.dataPath, 'disease-precaution.csv'), "a") as f:
                f.write(f"{disease_name.replace('_', ' ')},{','.join(disease_precautions)}\n")

            with open(os.path.join(engine.dataPath, 'disease-symptoms.clp'), "a") as f:
                f.write(f"\n(defrule {disease_name}\n")
                f.write(f"  (disease_is {disease_name})\n")
                f.write(f"  =>\n")
                f.write(f"  (printout t \"{disease_name.replace('_', ' ')}\" crlf)\n")
                f.write(f")\n")

                f.write(f"\n(defrule is_it_{disease_name}\n")
                for symptom in new_symptoms:
                    f.write(f"  (has_symptom {symptom})\n")
                f.write(f"  =>\n")
                f.write(f"  (assert (disease_is {disease_name}))\n")
                f.write(f")\n")

            engine.load_environment()

            return jsonify({'status': 'success'}), 201
        except Exception as e:
            logging.error(f"Error adding new disease: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500

    @routes.route('/diagnose', methods=['POST'])
    def diagnose():
        try:
            engine.reset()

            data = request.get_json()
            symptoms = [symptom.replace(' ', '_').lower() for symptom in data['symptoms']]

            for symptom in symptoms:
                engine.addSymptom(symptom)

            engine.run()
            diseases = engine.getDiseases()

            if not diseases:
                return jsonify({
                    'status': 'success',
                    'diseases': [],
                    'message': 'No diseases detected, please add more symptoms.'
                })

            return jsonify({
                'status': 'success',
                'diseases': info.detail(diseases)
            })
        except Exception as e:
            logging.error(f"Error during diagnosis: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500

    return routes
