from flask import Flask, render_template, request, jsonify, redirect
from clips import Environment
import os
import json
import logging
from flask_cors import CORS

app = Flask(__name__)
CORS(app)


class DiseaseDiagnosis:
    def __init__(self):
        self.dataPath = os.path.abspath(os.path.join(os.getcwd(), 'data'))
        self.diseasePath = os.path.join(self.dataPath, 'disease-symptoms.clp')
        self.env = Environment()
        self.load_environment()

    def load_environment(self):
        self.env.clear()  # Clear the environment before reloading
        self.env.load(self.diseasePath)
        logging.info("CLIPS environment loaded with rules from disease-symptoms.clp")

    def reset(self):
        self.env.reset()
        logging.info("CLIPS environment reset.")

    def addSymptom(self, symptom):
        text = f'(assert (has_symptom {symptom}))'
        self.env.eval(text)

    def run(self):
        _ = self.env.run()

    def getDiseases(self):
        diseases = []
        for fact in self.env.facts():
            fact = str(fact)
            if "disease_is" in fact:
                disease = fact[1:-1].split(" ")[1]
                disease = disease.replace("_", " ")
                disease = disease.title()
                diseases.append(disease)
        return diseases

    def getSymptoms(self):
        symptoms = []
        for fact in self.env.facts():
            fact = str(fact)
            if "has_symptom" in fact:
                symptom = fact[1:-1].split(" ")[1]
                symptom = symptom.replace("_", " ")
                symptom = symptom.title()
                symptoms.append(symptom)
        return symptoms

    def getSymptomList(self):
        path = os.path.join(self.dataPath, 'symptoms.txt')
        with open(path, "r") as f:
            symptoms = [x.strip().replace('_', ' ').title() for x in f if x.strip()]
        return symptoms

    def add_new_symptom(self, rule_name, symptom):
        path = os.path.join(self.dataPath, 'symptoms.txt')
        diseasePath = os.path.join(self.dataPath, 'disease-symptoms.clp')

        # Update symptoms.txt
        with open(path, "r") as f:
            symptoms = [line.strip() for line in f]

        if symptom not in symptoms:
            with open(path, "a") as f:
                f.write(f"{symptom}\n")

        # Update CLIPS file
        with open(diseasePath, "r") as f:
            lines = f.readlines()

        found_disease = False
        new_lines = []
        for line in lines:
            new_line = line
            if rule_name.lower() in line.lower():
                found_disease = True
            if "=>" in line and found_disease:
                new_line = line.replace("=>", f"(has_symptom {symptom})\n\t=>")
                found_disease = False
            new_lines.append(new_line)

        with open(diseasePath, "w") as f:
            f.writelines(new_lines)

        self.load_environment()  # Reload the environment with the updated knowledge base


class DiseaseInfo:
    def __init__(self):
        self.descriptions = self._getDescriptions()
        self.precautions = self._getPrecautions()

    def detail(self, diseases):
        data = []
        for disease in diseases:
            disease_key = disease.lower().strip().replace(" ", "_")
            oneData = {
                'name': disease,
                'description': self.descriptions.get(disease_key, "Description not available."),
                'precautions': self.precautions.get(disease_key, [])
            }
            data.append(oneData)
        return data

    def _getDescriptions(self):
        data = {}
        with open("./data/disease-description.csv", "r") as f:
            for line in f:
                parts = line.strip().split(',')
                disease_key = parts[0].lower().strip().replace(" ", "_")
                data[disease_key] = ",".join(parts[1:]).replace("\"", "")
        return data

    def _getPrecautions(self):
        data = {}
        with open("./data/disease-precaution.csv", "r") as f:
            for line in f:
                parts = line.strip().split(',')
                disease_key = parts[0].lower().strip().replace(" ", "_")
                precautions = [prec.strip().capitalize() for prec in parts[1:] if prec.strip()]
                data[disease_key] = precautions
        return data


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.urandom(24).hex()

    engine = DiseaseDiagnosis()

    @app.route('/', methods=['GET', 'POST'])
    def home():
        return render_template('index.html', symptomList=engine.getSymptomList())

    @app.route('/addNewSymptom', methods=['POST'])
    def addNewSymptom():
        try:
            new_symptom = request.form['new_symptom'].replace(' ', '_').lower()
            disease_name = f"is_it_{request.form['diseaseName'].replace(' ', '_').lower()}"

            engine.add_new_symptom(disease_name, new_symptom)
            return redirect('/')
        except Exception as e:
            logging.error(f"Error adding new symptom: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500

    @app.route('/addNewDisease', methods=['POST'])
    def addNewDisease():
        try:
            data = request.json
            disease_name = data['diseaseName'].strip().replace(' ', '_').lower()
            disease_description = data['diseaseDescription'].strip()
            disease_precautions = [prec.strip() for prec in data['diseasePrecautions'].split(',')]
            new_symptoms = [sym.strip().replace(' ', '_').lower() for sym in data['newSymptoms'].split(',')]

            # Check if the disease already exists
            disease_exists = any(f"(defrule {disease_name}" in line for line in open(engine.diseasePath))
            if disease_exists:
                return jsonify(
                    {'status': 'error', 'message': f"Disease '{disease_name.replace('_', ' ')}' already exists."}), 409

            # Update files
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

            # Reload environment
            engine.load_environment()

            return jsonify({'status': 'success'}), 201
        except Exception as e:
            logging.error(f"Error adding new disease: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500

    @app.route('/', methods=['GET'])
    def home():
        symptom_list = engine.getSymptomList()
        return jsonify({'symptomList': symptom_list})

    @app.route('/diagnose', methods=['POST'])
    def diagnose():
        try:
            engine.reset()

            data = request.get_json()
            symptoms = [symptom.replace(' ', '_').lower() for symptom in data['symptoms']]

            for symptom in symptoms:
                engine.addSymptom(symptom)

            engine.run()
            diseases = engine.getDiseases()
            info = DiseaseInfo()

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

    return app


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
