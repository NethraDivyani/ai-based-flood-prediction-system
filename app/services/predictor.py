import joblib
import numpy as np
import pandas as pd
from flask import current_app
from app.models import StationReading
from app.utils import STATIONS
from datetime import timedelta

_model_bundle = None


def load_model_bundle():
    global _model_bundle
    if _model_bundle is None:
        _model_bundle = joblib.load(current_app.config["MODEL_PATH"])
    return _model_bundle


def get_day_readings_map(target_date):
    rows = StationReading.query.filter_by(reading_date=target_date).all()
    data = {}
    for row in rows:
        data[row.station_name] = {
            "wl": row.water_level,
            "rain": row.rainfall,
            "q": row.discharge
        }
    return data


def validate_station_set(day_map):
    return all(st in day_map for st in STATIONS)


def build_feature_row(today, yesterday, two_days_ago, three_days_ago, date):
    bundle = load_model_bundle()
    feat_cols = bundle["feature_cols"]

    row = {}
    month = date.month
    day_of_year = date.timetuple().tm_yday

    for st in STATIONS:
        row[f"{st}_WL_gauge_m"] = today[st]["wl"]
        row[f"{st}_Rainfall_mm"] = today[st]["rain"]
        row[f"{st}_Discharge_cumecs"] = today[st]["q"]

    row["Month"] = month
    row["DayOfYear"] = day_of_year
    row["Is_SW_Monsoon"] = 1 if month in [5, 6, 7, 8, 9] else 0
    row["Is_NE_Monsoon"] = 1 if month in [10, 11, 12, 1] else 0
    row["Sin_Month"] = np.sin(2 * np.pi * month / 12)
    row["Cos_Month"] = np.cos(2 * np.pi * month / 12)

    lag_data = {
        1: yesterday,
        2: two_days_ago,
        3: three_days_ago
    }

    for st in STATIONS:
        for lag, data in lag_data.items():
            row[f"{st}_WL_gauge_m_lag{lag}"] = data[st]["wl"]
            row[f"{st}_Rainfall_mm_lag{lag}"] = data[st]["rain"]
            row[f"{st}_Discharge_cumecs_lag{lag}"] = data[st]["q"]

    for st in STATIONS:
        row[f"{st}_WL_change_1d"] = today[st]["wl"] - yesterday[st]["wl"]
        row[f"{st}_WL_change_2d"] = yesterday[st]["wl"] - two_days_ago[st]["wl"]
        row[f"{st}_WL_change_3d"] = today[st]["wl"] - three_days_ago[st]["wl"]

    for st in STATIONS:
        r0 = today[st]["rain"]
        r1 = yesterday[st]["rain"]
        r2 = two_days_ago[st]["rain"]
        r3 = three_days_ago[st]["rain"]

        row[f"{st}_Rain_2d_sum"] = r0 + r1
        row[f"{st}_Rain_3d_sum"] = r0 + r1 + r2
        row[f"{st}_Rain_5d_sum"] = r0 + r1 + r2 + r3
        row[f"{st}_Rain_7d_sum"] = r0 + r1 + r2 + r3

    rain_vals = [today[s]["rain"] for s in STATIONS]
    q_vals = [today[s]["q"] for s in STATIONS]

    row["Basin_Rainfall_sum"] = float(np.sum(rain_vals))
    row["Basin_Rainfall_mean"] = float(np.mean(rain_vals))
    row["Basin_Discharge_sum"] = float(np.sum(q_vals))
    row["Basin_Discharge_mean"] = float(np.mean(q_vals))

    upstream = ["Norwood", "Kithulgala"]
    midstream = ["Holombuwa", "Deraniyagala"]
    downstream = ["Glencourse", "Hanwella"]

    row["Upstream_Rainfall_sum"] = sum(today[s]["rain"] for s in upstream)
    row["Midstream_Rainfall_sum"] = sum(today[s]["rain"] for s in midstream)
    row["Downstream_Rainfall_sum"] = sum(today[s]["rain"] for s in downstream)

    row["Upstream_Discharge_sum"] = sum(today[s]["q"] for s in upstream)
    row["Midstream_Discharge_sum"] = sum(today[s]["q"] for s in midstream)
    row["Downstream_Discharge_sum"] = sum(today[s]["q"] for s in downstream)

    row_df = pd.DataFrame([row])

    for col in feat_cols:
        if col not in row_df.columns:
            row_df[col] = 0.0

    return row_df[feat_cols]


def predict_for_date(base_date):
    bundle = load_model_bundle()
    model = bundle["model"]
    scaler = bundle["scaler"]
    le = bundle["label_encoder"]

    today = get_day_readings_map(base_date)
    yesterday = get_day_readings_map(base_date - timedelta(days=1))
    two_days_ago = get_day_readings_map(base_date - timedelta(days=2))
    three_days_ago = get_day_readings_map(base_date - timedelta(days=3))

    print("BASE DATE:", base_date)
    print("TODAY:", list(today.keys()))
    print("YESTERDAY:", list(yesterday.keys()))
    print("TWO DAYS AGO:", list(two_days_ago.keys()))
    print("THREE DAYS AGO:", list(three_days_ago.keys()))

    if not all([
        validate_station_set(today),
        validate_station_set(yesterday),
        validate_station_set(two_days_ago),
        validate_station_set(three_days_ago)
    ]):
        return None

    X_df = build_feature_row(today, yesterday, two_days_ago, three_days_ago, base_date)
    X_scaled = scaler.transform(X_df)

    pred = model.predict(X_scaled)[0]
    probs = model.predict_proba(X_scaled)[0]
    pred_label = le.inverse_transform([pred])[0]

    class_names = list(le.classes_)
    class_probs = {class_names[i]: float(probs[i]) for i in range(len(class_names))}

    return {
        "forecast_for": str(base_date + timedelta(days=1)),
        "predicted_class": pred_label,
        "probabilities": class_probs
    }