from flask import Flask
from flask_executor import Executor

import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

executor = Executor()

# firestore
cred = credentials.Certificate("./firebase_key.json")
firebase_admin.initialize_app(cred)
db = firestore.client()


def create_app():
    app = Flask(__name__)

    executor.init_app(app)

    from .views import input, report_views
    app.register_blueprint(input.bp)
    app.register_blueprint(report_views.bp)

    return app
