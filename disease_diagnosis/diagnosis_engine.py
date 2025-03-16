import os
from clips import Environment

class DiseaseDiagnosis:
    def __init__(self):
        self.dataPath = os.path.abspath(os.path.join(os.getcwd(), 'data'))
        self.diseasePath = os.path.join(self.dataPath, 'disease-symptoms.clp')
        self.env = Environment()
        self.load_environment()

    def load_environment(self):
        self.env.clear()
        self.env.load(self.diseasePath)
        print("CLIPS environment loaded with rules from disease-symptoms.clp")

    def reset(self):
        self.env.reset()
        print("CLIPS environment reset.")

    def add_symptom(self, symptom):
        text = f'(assert (has_symptom {symptom}))'
        self.env.eval(text)

    def run(self):
        _ = self.env.run()

    def get_diseases(self):
        diseases = []
        for fact in self.env.facts():
            fact_str = str(fact)
            if "disease_is" in fact_str:
                disease = fact_str[1:-1].split(" ")[1].replace("_", " ").title()
                diseases.append(disease)
        return diseases

    def get_symptom_list(self):
        path = os.path.join(self.dataPath, 'symptoms.txt')
        symptoms = []
        with open(path, "r") as f:
            for line in f:
                symptom = line.strip().replace('_', ' ').title()
                symptoms.append(symptom)
        return symptoms

    def add_new_symptom(self, rule_name, symptom):
        # Update symptoms.txt
        symptom_path = os.path.join(self.dataPath, 'symptoms.txt')
        disease_path = os.path.join(self.dataPath, 'disease-symptoms.clp')

        with open(symptom_path, "a") as f:
            f.write(f"{symptom},\n")

        # Update disease-symptoms.clp
        self.update_clips_file(disease_path, rule_name, symptom)
        self.load_environment()

    def update_clips_file(self, disease_path, rule_name, symptom):
        with open(disease_path, "r") as f:
            lines = f.readlines()

        updated_lines = []
        found_rule = False

        for line in lines:
            if rule_name.lower() in line.lower():
                found_rule = True
            if "=>" in line and found_rule:
                line = line.replace("=>", f"(has_symptom {symptom})\n\t=>")
                found_rule = False
            updated_lines.append(line)

        with open(disease_path, "w") as f:
            f.writelines(updated_lines)

    def add_new_disease(self, disease_name, description, precautions, symptoms):
        disease_exists = self.check_disease_exists(disease_name)

        if disease_exists:
            return {'status': 'error', 'message': f"Disease '{disease_name.replace('_', ' ')}' already exists."}

        self.update_symptoms_file(symptoms)
        self.update_disease_description(disease_name, description)
        self.update_disease_precautions(disease_name, precautions)
        self.update_disease_rules(disease_name, symptoms)

        self.load_environment()

        return {'status': 'success'}

    def check_disease_exists(self, disease_name):
        with open(self.diseasePath, "r") as f:
            for line in f:
                if f"(defrule {disease_name}" in line:
                    return True
        return False

    def update_symptoms_file(self, symptoms):
        symptom_path = os.path.join(self.dataPath, 'symptoms.txt')
        with open(symptom_path, "a") as f:
            for symptom in symptoms:
                f.write(f"{symptom.strip().replace(' ', '_').lower()},\n")

    def update_disease_description(self, disease_name, description):
        description_path = os.path.join(self.dataPath, 'disease-description.csv')
        with open(description_path, "a") as f:
            f.write(f"{disease_name.replace('_', ' ')},{description}\n")

    def update_disease_precautions(self, disease_name, precautions):
        precaution_path = os.path.join(self.dataPath, 'disease-precaution.csv')
        with open(precaution_path, "a") as f:
            f.write(f"{disease_name.replace('_', ' ')},{','.join(precautions)}\n")

    def update_disease_rules(self, disease_name, symptoms):
        with open(self.diseasePath, "a") as f:
            f.write(f"\n(defrule {disease_name}\n")
            f.write(f"  (disease_is {disease_name})\n")
            f.write(f"  =>\n")
            f.write(f"  (printout t \"{disease_name.replace('_', ' ')}\" crlf)\n")
            f.write(f")\n")

            f.write(f"\n(defrule is_it_{disease_name}\n")
            for symptom in symptoms:
                f.write(f"  (has_symptom {symptom.strip().replace(' ', '_').lower()})\n")
            f.write(f"  =>\n")
            f.write(f"  (assert (disease_is {disease_name}))\n")
            f.write(f")\n")
