import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = "flood-secret-key-2026"

    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, "flood_system.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    MODEL_PATH = os.path.join(BASE_DIR, "models", "flood_model_corrected.pkl")
    DATASET_PATH = os.path.join(BASE_DIR, "flood_prediction_dataset.xlsx")

    OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
    REPORT_DIR = os.path.join(BASE_DIR, "reports")

    # =========================
    # Email Configuration
    # =========================
    MAIL_SERVER = "smtp.gmail.com"
    MAIL_PORT = 587
    MAIL_USE_TLS = True

    MAIL_USERNAME = "nethradivyani0511@gmail.com"
    MAIL_PASSWORD = "ylokdxmajhrojhsp"

    MAIL_DEFAULT_SENDER = "nethradivyani0511@gmail.com"