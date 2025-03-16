import os

class DiseaseInfo:
    def __init__(self):
        self.descriptions = self.get_descriptions()
        self.precautions = self.get_precautions()

    def detail(self, diseases):
        data = []
        for disease in diseases:
            disease_key = disease.lower().strip().replace(" ", "_")
            data.append({
                'name': disease,
                'description': self.descriptions.get(disease_key, 'Description not available'),
                'precautions': self.precautions.get(disease_key, ['Precautions not available'])
            })
        return data

    def get_descriptions(self):
        data = {}
        with open("./data/disease-description.csv", "r") as f:
            next(f)  # Skip header
            for line in f:
                parts = line.strip().split(',')
                disease_key = parts[0].lower().strip().replace(" ", "_")
                description = ",".join(parts[1:]).replace("\"", "")
                data[disease_key] = description
        return data

    def get_precautions(self):
        data = {}
        with open("./data/disease-precaution.csv", "r") as f:
            next(f)  # Skip header
            for line in f:
                parts = line.strip().split(',')
                disease_key = parts[0].lower().strip().replace(" ", "_")
                precautions = [precaution.strip().capitalize() for precaution in parts[1:] if precaution.strip()]
                data[disease_key] = precautions
        return data
