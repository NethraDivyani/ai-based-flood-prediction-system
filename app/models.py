import re
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db, login_manager



# Validation Helpers

def is_valid_email(email: str) -> bool:
    if not email:
        return False
    pattern = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
    return re.match(pattern, email) is not None


def is_valid_phone(phone: str) -> bool:
    if not phone:
        return False

    phone = phone.strip()

    # Valid Sri Lankan mobile formats:
    # 0771234567
    # 0712345678
    # +94771234567
    # 94771234567
    pattern = r"^(?:\+94|94|0)?7[01245678]\d{7}$"

    return re.match(pattern, phone) is not None


def normalize_language(lang: str) -> str:
    if not lang:
        return "en"

    lang = lang.strip().lower()

    if lang in ["si", "sinhala", "sinhalese"]:
        return "si"
    if lang in ["ta", "tamil"]:
        return "ta"

    return "en"



# Admin User Model

class AdminUser(UserMixin, db.Model):
    __tablename__ = "admin_users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password: str):
        if not password or len(password.strip()) < 6:
            raise ValueError("Password must be at least 6 characters long.")
        self.password_hash = generate_password_hash(password.strip())

    def check_password(self, password: str) -> bool:
        if not password:
            return False
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<AdminUser {self.username}>"


@login_manager.user_loader
def load_user(user_id):
    try:
        return AdminUser.query.get(int(user_id))
    except (ValueError, TypeError):
        return None



# Station Reading Model

class StationReading(db.Model):
    __tablename__ = "station_readings"

    id = db.Column(db.Integer, primary_key=True)
    reading_date = db.Column(db.Date, nullable=False, index=True)
    station_name = db.Column(db.String(50), nullable=False, index=True)
    water_level = db.Column(db.Float, nullable=False)
    rainfall = db.Column(db.Float, nullable=False)
    discharge = db.Column(db.Float, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey("admin_users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<StationReading {self.station_name} {self.reading_date}>"



# Prediction Model

class Prediction(db.Model):
    __tablename__ = "predictions"

    id = db.Column(db.Integer, primary_key=True)
    forecast_date = db.Column(db.Date, nullable=False, index=True)
    predicted_class = db.Column(db.String(50), nullable=False)
    prob_normal = db.Column(db.Float, default=0.0)
    prob_alert = db.Column(db.Float, default=0.0)
    prob_minor = db.Column(db.Float, default=0.0)
    prob_major = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def max_probability(self) -> float:
        return max(
            self.prob_normal or 0.0,
            self.prob_alert or 0.0,
            self.prob_minor or 0.0,
            self.prob_major or 0.0,
        )

    def flood_probability(self) -> float:
        # Flood-related probability
        return (self.prob_alert or 0.0) + (self.prob_minor or 0.0) + (self.prob_major or 0.0)

    def __repr__(self):
        return f"<Prediction {self.forecast_date} {self.predicted_class}>"



# Subscriber Model

class Subscriber(db.Model):
    __tablename__ = "subscribers"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(30), nullable=True)
    preferred_language = db.Column(db.String(20), default="en")
    is_active = db.Column(db.Boolean, default=True)
    subscribed_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_language(self, lang: str):
        self.preferred_language = normalize_language(lang)

    def __repr__(self):
        return f"<Subscriber {self.email}>"



# Alert Log Model

class AlertLog(db.Model):
    __tablename__ = "alert_logs"

    id = db.Column(db.Integer, primary_key=True)
    alert_level = db.Column(db.String(50), nullable=False)
    message = db.Column(db.Text, nullable=False)
    sent_to = db.Column(db.String(120), nullable=True)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<AlertLog {self.alert_level} {self.sent_to}>"