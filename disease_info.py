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
