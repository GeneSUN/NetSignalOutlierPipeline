import sys
import os

# =========================================
# Dynamically add /src to sys.path
# =========================================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
SRC_PATH = os.path.join(PROJECT_ROOT, "src")
sys.path.append(SRC_PATH)

from modeling.detectors.ewma_detector import EWMAAnomalyDetector

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import mlflow
import matplotlib.pyplot as plt


# =========================================
# Setup MLflow Tracking
# =========================================
mlflow.set_tracking_uri("http://njbbvmaspd11:5001")
mlflow.set_experiment("NetSignal_EWMA_DetectionTest")


# =========================================
# Synthetic Dataset Generator
# =========================================
def generate_synthetic_data(for_novelty=True):
    """
    Generate synthetic dataframe with anomalies.
    - If for_novelty=True → last 20 points have anomalies.
    - Else → anomalies across entire series.
    """
    n_points = 200
    timestamps = [datetime.now() - timedelta(hours=i) for i in range(n_points)][::-1]

    # Normal sinusoidal base
    values = np.sin(np.linspace(0, 6 * np.pi, n_points)) + np.random.normal(0, 0.2, n_points)

    df = pd.DataFrame({
        "sn": ["TEST_SN_1"] * n_points,
        "time": timestamps,
        "avg_5gsnr": values
    })

    # Inject anomalies
    if for_novelty:
        df.loc[n_points-25:n_points-10, "avg_5gsnr"] += 3
        df.loc[n_points-10:, "avg_5gsnr"] -= 3
    else:
        anomaly_idx = np.random.choice(n_points, size=12, replace=False)
        df.loc[anomaly_idx, "avg_5gsnr"] += np.random.choice([3, -3], size=12)

    return df


# =========================================
# Novelty (Recent-Points) Detection Test
# =========================================
def test_ewma_novelty():
    df = generate_synthetic_data(for_novelty=True)

    with mlflow.start_run(run_name="EWMA_Novelty_Test"):
        params = {
            "window": 50,
            "no_of_stds": 2.5,
            "recent_window_size": 30,
            "anomaly_direction": "both",
            "scaler": "minmax",
            "use_weighted_std": False,
        }
        mlflow.log_params(params)

        detector = EWMAAnomalyDetector(
            df=df,
            feature="avg_5gsnr",
            timestamp_col="time",
            recent_window_size=params["recent_window_size"],  # Novelty detection
            window=params["window"],
            no_of_stds=params["no_of_stds"],
            anomaly_direction=params["anomaly_direction"],
            scaler=params["scaler"],
            use_weighted_std=params["use_weighted_std"],
        )

        result = detector.fit()
        fig = detector.plot()
        mlflow.log_figure(fig, "ewma_novelty_detection.png")

        mlflow.log_metric("n_total_samples", len(df))
        mlflow.log_metric("n_anomalies_detected", len(result))

        print("\n📌 EWMA Novelty Detection Results:")
        print(result)

    return result


# =========================================
# Outlier Detection (Full-Series)
# =========================================
def test_ewma_outlier():
    df = generate_synthetic_data(for_novelty=False)

    with mlflow.start_run(run_name="EWMA_Outlier_Test"):
        params = {
            "window": 60,
            "no_of_stds": 3.0,
            "recent_window_size": "all",
            "anomaly_direction": "both",
            "scaler": "standard",
            "use_weighted_std": True,
        }
        mlflow.log_params(params)

        detector = EWMAAnomalyDetector(
            df=df,
            feature="avg_5gsnr",
            timestamp_col="time",
            recent_window_size=params["recent_window_size"],
            window=params["window"],
            no_of_stds=params["no_of_stds"],
            anomaly_direction=params["anomaly_direction"],
            use_weighted_std=params["use_weighted_std"],
            scaler=params["scaler"],
        )

        result = detector.fit()
        fig = detector.plot()
        mlflow.log_figure(fig, "ewma_outlier_detection.png")

        mlflow.log_metric("n_total_samples", len(df))
        mlflow.log_metric("n_anomalies_detected", len(result))

        print("\n📌 EWMA Outlier Detection Results:")
        print(result)

    return result


# =========================================
# Entry Point
# =========================================
if __name__ == "__main__":
    print("\n========== Running EWMA Novelty Detection Test ==========")
    novelty_results = test_ewma_novelty()

    print("\n========== Running EWMA Outlier Detection Test ==========")
    outlier_results = test_ewma_outlier()

    print("\n🎯 EWMA Detector Testing Completed.")
