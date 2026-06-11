from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from app.extensions import db
from app.models import StationReading, Subscriber, Prediction, AlertLog
from app.services.predictor import predict_for_date
from app.services.alerts import build_alert_message
from app.utils import STATIONS
import smtplib
from email.mime.text import MIMEText

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

# Email Sending Function

def send_alert_email(subscriber, alert_level, message):
    if not subscriber.email:
        return False

    if alert_level == "Normal":
        return False

    if subscriber.preferred_language == "si":
        subject = f"ගංවතුර අනතුරු ඇඟවීම - {alert_level}"
        body = f"අනතුරු මට්ටම: {alert_level}\n\n{message}"

    elif subscriber.preferred_language == "ta":
        subject = f"வெள்ள எச்சரிக்கை - {alert_level}"
        body = f"எச்சரிக்கை நிலை: {alert_level}\n\n{message}"

    else:
        subject = f"Flood Alert - {alert_level}"
        body = f"Alert Level: {alert_level}\n\n{message}"

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
        print(f"Alert email sent to {subscriber.email}")
        return True
    except Exception as e:
        print("Alert email error:", e)
        return False

# Dashboard

@admin_bp.route("/dashboard", methods=["GET"])
@login_required
def dashboard():
    latest_prediction = Prediction.query.order_by(Prediction.created_at.desc()).first()
    return render_template("admin/dashboard.html", latest_prediction=latest_prediction)


# Add Station Reading

@admin_bp.route("/add-reading", methods=["GET", "POST"])
@login_required
def add_reading_page():
    if request.method == "POST":
        station_name = (request.form.get("station_name") or "").strip()
        reading_date = (request.form.get("reading_date") or "").strip()
        water_level = (request.form.get("water_level") or "").strip()
        rainfall = (request.form.get("rainfall") or "").strip()
        discharge = (request.form.get("discharge") or "").strip()

        if not station_name or station_name not in STATIONS:
            flash("Invalid station name.", "danger")
            return redirect(url_for("admin.add_reading_page"))

        if not reading_date:
            flash("Reading date is required.", "danger")
            return redirect(url_for("admin.add_reading_page"))

        try:
            reading_date_obj = datetime.strptime(reading_date, "%Y-%m-%d").date()
        except ValueError:
            flash("Reading date must be in YYYY-MM-DD format.", "danger")
            return redirect(url_for("admin.add_reading_page"))

        try:
            water_level_val = float(water_level)
            rainfall_val = float(rainfall)
            discharge_val = float(discharge)
        except ValueError:
            flash("Water level, rainfall, and discharge must be numeric values.", "danger")
            return redirect(url_for("admin.add_reading_page"))

        if water_level_val < 0 or rainfall_val < 0 or discharge_val < 0:
            flash("Water level, rainfall, and discharge cannot be negative.", "danger")
            return redirect(url_for("admin.add_reading_page"))

        existing = StationReading.query.filter_by(
            station_name=station_name,
            reading_date=reading_date_obj
        ).first()

        if existing:
            existing.water_level = water_level_val
            existing.rainfall = rainfall_val
            existing.discharge = discharge_val
            existing.created_by = current_user.id
            flash("Existing reading updated successfully.", "success")
        else:
            row = StationReading(
                station_name=station_name,
                reading_date=reading_date_obj,
                water_level=water_level_val,
                rainfall=rainfall_val,
                discharge=discharge_val,
                created_by=current_user.id
            )
            db.session.add(row)
            flash("Reading saved successfully.", "success")

        db.session.commit()
        return redirect(url_for("admin.add_reading_page"))

    readings = StationReading.query.order_by(
        StationReading.reading_date.desc(),
        StationReading.station_name.asc()
    ).limit(30).all()

    return render_template(
        "admin/add_reading.html",
        stations=STATIONS,
        readings=readings
    )



# Sample/Test Data for Station Form

@admin_bp.route("/sample-reading", methods=["GET"])
@login_required
def sample_reading():
    today = datetime.today().date()

    samples = [
        {
            "station_name": "Hanwella" if "Hanwella" in STATIONS else STATIONS[0],
            "reading_date": str(today),
            "water_level": 6.20,
            "rainfall": 110.00,
            "discharge": 720.00
        },
        {
            "station_name": "Glencourse" if "Glencourse" in STATIONS else STATIONS[0],
            "reading_date": str(today - timedelta(days=1)),
            "water_level": 4.80,
            "rainfall": 85.00,
            "discharge": 510.00
        },
        {
            "station_name": "Holombuwa" if "Holombuwa" in STATIONS else STATIONS[0],
            "reading_date": str(today - timedelta(days=2)),
            "water_level": 5.40,
            "rainfall": 95.00,
            "discharge": 610.00
        }
    ]

    return jsonify(samples)



# Subscribers Page

@admin_bp.route("/subscribers", methods=["GET"])
@login_required
def subscribers_page():
    subscribers = Subscriber.query.order_by(Subscriber.subscribed_at.desc()).all()
    return render_template("admin/subscribers.html", subscribers=subscribers)


# Run Forecast

@admin_bp.route("/run-forecast", methods=["POST"])
@login_required
def run_forecast_form():
    base_date_str = (request.form.get("base_date") or "").strip()

    if not base_date_str:
        flash("Base date is required.", "danger")
        return redirect(url_for("admin.dashboard"))

    try:
        base_date = datetime.strptime(base_date_str, "%Y-%m-%d").date()
    except ValueError:
        flash("Invalid date format. Use YYYY-MM-DD.", "danger")
        return redirect(url_for("admin.dashboard"))

    result = predict_for_date(base_date)

    if result is None:
        flash("Not enough station data for current and previous 3 days.", "danger")
        return redirect(url_for("admin.dashboard"))

    predicted_class = result["predicted_class"]

    prediction = Prediction(
        forecast_date=datetime.strptime(result["forecast_for"], "%Y-%m-%d").date(),
        predicted_class=predicted_class,
        prob_normal=result["probabilities"].get("Normal", 0.0),
        prob_alert=result["probabilities"].get("Alert", 0.0),
        prob_minor=result["probabilities"].get("Minor Flood", 0.0),
        prob_major=result["probabilities"].get("Major Flood", 0.0)
    )

    db.session.add(prediction)
    db.session.commit()

    # Optional automatic alert sending
    if predicted_class in ["Alert", "Minor Flood", "Major Flood"]:
        message = build_alert_message(predicted_class)
        subscribers = Subscriber.query.filter_by(is_active=True).all()

        sent_count = 0

        for sub in subscribers:
            destination = sub.email or sub.phone or "unknown"

            email_sent = send_alert_email(sub, predicted_class, message)
            if email_sent:
                sent_count += 1

            log = AlertLog(
                alert_level=predicted_class,
                message=message,
                sent_to=destination
            )
            db.session.add(log)

        db.session.commit()
        flash(f"Forecast generated and {sent_count} alert email(s) sent.", "success")
    else:
        flash("Forecast generated successfully. No alert email sent because prediction is Normal.", "success")

    return redirect(url_for("public.forecast_page"))



# Send Alert Manually

@admin_bp.route("/send-alert", methods=["POST"])
@login_required
def send_alert():
    alert_level = (request.form.get("alert_level") or "").strip()

    if not alert_level:
        flash("Alert level is required.", "danger")
        return redirect(url_for("admin.dashboard"))

    if alert_level == "Normal":
        flash("No alert email is sent for Normal prediction.", "info")
        return redirect(url_for("admin.dashboard"))

    message = build_alert_message(alert_level)
    subscribers = Subscriber.query.filter_by(is_active=True).all()

    if not subscribers:
        flash("No active subscribers found.", "warning")
        return redirect(url_for("admin.dashboard"))

    sent_count = 0

    for sub in subscribers:
        destination = sub.email or sub.phone or "unknown"

        email_sent = send_alert_email(sub, alert_level, message)
        if email_sent:
            sent_count += 1

        log = AlertLog(
            alert_level=alert_level,
            message=message,
            sent_to=destination
        )
        db.session.add(log)

    db.session.commit()
    flash(f"Alert processed successfully. Emails sent: {sent_count}", "success")
    return redirect(url_for("admin.dashboard"))