from flask import Flask
from config import Config
from disease_diagnosis import DiseaseDiagnosis
from disease_info import DiseaseInfo
from routes import main_routes
from flask_cors import CORS
def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    CORS(app)
    engine = DiseaseDiagnosis()
    info = DiseaseInfo()

    app.register_blueprint(main_routes(engine, info))

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
