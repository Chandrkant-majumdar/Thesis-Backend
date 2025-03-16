import os
import logging
from clips import Environment

class DiseaseDiagnosis:
    def __init__(self):
        self.dataPath = os.path.abspath(os.path.join(os.getcwd(), 'data'))
        self.diseasePath = os.path.join(self.dataPath, 'disease-symptoms.clp')
        self.env = Environment()
        self.load_environment()
        super().__init__()
        self.matched_diseases = set()

    def load_environment(self):
        self.env.clear()
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

    def get_known_symptoms(self):
        # This method returns a list of known symptoms
        # Assuming you have a method to get symptoms from a file
        return self.getSymptomList()

    def add_new_symptom(self, rule_name, symptom):
        path = os.path.join(self.dataPath, 'symptoms.txt')
        diseasePath = os.path.join(self.dataPath, 'disease-symptoms.clp')

        with open(path, "r") as f:
            symptoms = [line.strip() for line in f]

        if symptom not in symptoms:
            with open(path, "a") as f:
                f.write(f"{symptom}\n")

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

        self.load_environment()
