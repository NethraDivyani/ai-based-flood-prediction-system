from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, current_app
from app.models import Prediction, Subscriber, StationReading, is_valid_email, is_valid_phone, normalize_language
from app.extensions import db
from app.services.weather_api import get_weather_forecast
import smtplib
from email.mime.text import MIMEText

public_bp = Blueprint("public", __name__)



# Email Sending Function

def send_subscription_email(subscriber):
    if not subscriber.email:
        return

    if subscriber.preferred_language == "si":
        subject = "ඔබගේ දායකත්වයට ස්තුතියි"
        body = "Kelani Flood Alert පද්ධතියට ඔබ සාර්ථකව දායක වී ඇත."

    elif subscriber.preferred_language == "ta":
        subject = "உங்கள் பதிவு நன்றி"
        body = "Kelani Flood Alert அமைப்பில் நீங்கள் வெற்றிகரமாக பதிவு செய்யப்பட்டுள்ளீர்கள்."

    else:
        subject = "Thank you for subscribing"
        body = "You have successfully subscribed to Kelani Flood Alert notifications."

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = current_app.config["MAIL_DEFAULT_SENDER"]
    msg["To"] = subscriber.email

    try:
        server = smtplib.SMTP(current_app.config["MAIL_SERVER"], current_app.config["MAIL_PORT"])
        server.starttls()
        server.login(
            current_app.config["MAIL_USERNAME"],
            current_app.config["MAIL_PASSWORD"]
        )
        server.sendmail(msg["From"], [msg["To"]], msg.as_string())
        server.quit()
        print(f"Subscription email sent to {subscriber.email}")
    except Exception as e:
        print("Email error:", e)



# Home Page

@public_bp.route("/", methods=["GET"])
def home():
    return render_template("public/home.html")



# Forecast Page

@public_bp.route("/forecast", methods=["GET"])
def forecast_page():
    latest = Prediction.query.order_by(Prediction.created_at.desc()).first()

    forecast = None
    if latest:
        forecast = {
            "forecast_date": latest.forecast_date,
            "predicted_class": latest.predicted_class,
            "probabilities": {
                "Normal": latest.prob_normal,
                "Alert": latest.prob_alert,
                "Minor Flood": latest.prob_minor,
                "Major Flood": latest.prob_major
            }
        }

    return render_template("public/forecast.html", forecast=forecast)



# Latest Forecast API

@public_bp.route("/public/latest-forecast", methods=["GET"])
def latest_forecast():
    latest = Prediction.query.order_by(Prediction.created_at.desc()).first()

    if not latest:
        return jsonify({"error": "No forecast available"}), 404

    return jsonify({
        "forecast_date": str(latest.forecast_date),
        "predicted_class": latest.predicted_class,
        "probabilities": {
            "Normal": latest.prob_normal,
            "Alert": latest.prob_alert,
            "Minor Flood": latest.prob_minor,
            "Major Flood": latest.prob_major
        }
    })



# Public Subscription API

@public_bp.route("/public/subscribe", methods=["POST"])
def public_subscribe():
    data = request.get_json()

    full_name = data.get("full_name", "").strip()
    email = data.get("email", "").strip()
    phone = data.get("phone", "").strip()
    language = normalize_language(data.get("preferred_language", "en"))

    if not full_name:
        return jsonify({"error": "Name required"}), 400

    if not email:
        return jsonify({"error": "Email required"}), 400

    if not is_valid_email(email):
        return jsonify({"error": "Invalid email"}), 400

    if not phone:
        return jsonify({"error": "Phone required"}), 400

    if not is_valid_phone(phone):
        return jsonify({"error": "Invalid phone"}), 400

    existing = Subscriber.query.filter_by(email=email).first()
    if existing:
        return jsonify({"message": "Already subscribed"}), 200

    subscriber = Subscriber(
        full_name=full_name,
        email=email,
        phone=phone,
        preferred_language=language
    )

    db.session.add(subscriber)
    db.session.commit()

    send_subscription_email(subscriber)

    return jsonify({"message": "Subscription successful"}), 201



# Public Station Readings

@public_bp.route("/public/station-readings", methods=["GET"])
def public_station_readings():
    date_value = request.args.get("date")

    if not date_value:
        return jsonify({"error": "date is required"}), 400

    rows = StationReading.query.filter_by(reading_date=date_value).all()

    return jsonify([
        {
            "station_name": row.station_name,
            "water_level": row.water_level,
            "rainfall": row.rainfall,
            "discharge": row.discharge
        }
        for row in rows
    ])



# Weather Forecast API

@public_bp.route("/weather/<float:lat>/<float:lon>", methods=["GET"])
def weather_forecast(lat, lon):
    data = get_weather_forecast(lat, lon)
    return data


# Graph Page 

@public_bp.route("/graphs", methods=["GET"])
def graphs_page():
    weather = get_weather_forecast(6.9271, 79.8612)

    weather_labels = weather["daily"]["time"]
    weather_rain = weather["daily"]["precipitation_sum"]
    temp_max = weather["daily"]["temperature_2m_max"]
    temp_min = weather["daily"]["temperature_2m_min"]

    # Fetch latest 7 predictions and reverse for chronological order
    predictions = Prediction.query.order_by(Prediction.forecast_date.desc()).limit(7).all()
    predictions = list(reversed(predictions))

    flood_labels = [str(p.forecast_date) for p in predictions]
    flood_values = [round((p.prob_alert + p.prob_minor + p.prob_major) * 100, 1) for p in predictions]

    return render_template(
        "public/graphs.html",
        weather_labels=weather_labels,
        weather_rain=weather_rain,
        temp_max=temp_max,
        temp_min=temp_min,
        flood_labels=flood_labels,
        flood_values=flood_values
    )


# Subscription Page

@public_bp.route("/subscribe", methods=["GET", "POST"])
def subscribe_page():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        language = normalize_language(request.form.get("preferred_language", "en"))

        if not full_name:
            flash("Full name is required.", "danger")
            return redirect(url_for("public.subscribe_page"))

        if len(full_name) < 3:
            flash("Full name must be at least 3 characters long.", "danger")
            return redirect(url_for("public.subscribe_page"))

        if not email:
            flash("Email is required.", "danger")
            return redirect(url_for("public.subscribe_page"))

        if not is_valid_email(email):
            flash("Please enter a valid email address.", "danger")
            return redirect(url_for("public.subscribe_page"))

        if not phone:
            flash("Phone number is required.", "danger")
            return redirect(url_for("public.subscribe_page"))

        if not is_valid_phone(phone):
            flash("Please enter a valid Sri Lankan mobile number.", "danger")
            return redirect(url_for("public.subscribe_page"))

        existing = Subscriber.query.filter_by(email=email).first()
        if existing:
            flash("You are already subscribed with this email.", "warning")
            return redirect(url_for("public.subscribe_page"))

        subscriber = Subscriber(
            full_name=full_name,
            email=email,
            phone=phone,
            preferred_language=language
        )

        db.session.add(subscriber)
        db.session.commit()

        send_subscription_email(subscriber)

        flash("Subscription successful!", "success")
        return redirect(url_for("public.subscribe_page"))

    return render_template("public/subscribe.html")



# Flood Guidance Page

@public_bp.route("/guidance", methods=["GET"])
def guidance_page():
    latest = Prediction.query.order_by(Prediction.created_at.desc()).first()

    level = "Normal"
    if latest:
        level = latest.predicted_class

    guidance_map = {
        "Normal": {
            "title": "Normal Condition Guidance",
            "points": [
                "Continue normal daily activities.",
                "Monitor official updates if rain increases.",
                "Keep emergency contacts available."
            ]
        },
        "Alert": {
            "title": "Alert Level Guidance",
            "points": [
                "Monitor river and rainfall updates closely.",
                "Prepare emergency kits and important documents.",
                "Stay aware of possible downstream flooding."
            ]
        },
        "Minor Flood": {
            "title": "Minor Flood Guidance",
            "points": [
                "Move valuables to safer higher places.",
                "Avoid low-lying roads and flood-prone routes.",
                "Prepare for short-notice evacuation if required."
            ]
        },
        "Major Flood": {
            "title": "Major Flood Guidance",
            "points": [
                "Evacuate immediately if instructed by authorities.",
                "Move to safe shelters or emergency centers.",
                "Do not attempt to cross flood waters."
            ]
        }
    }

    return render_template(
        "public/guidance.html",
        level=level,
        guidance=guidance_map[level]
    )