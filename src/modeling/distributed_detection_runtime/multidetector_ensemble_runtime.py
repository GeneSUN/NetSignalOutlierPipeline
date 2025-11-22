
import pandas as pd
from modeling.distributed_detection_runtime.arima_runtime import ARIMAAnomalyDetectorSM
from modeling.distributed_detection_runtime.ewma_runtime import EWMAAnomalyDetector
from modeling.distributed_detection_runtime.kde_runtime import FeaturewiseKDENoveltyDetector

from pyspark.sql.types import StructType, StructField, StringType, TimestampType, FloatType, BooleanType

# =============================

all_schema = StructType([
    StructField("sn", StringType(), True),
    StructField("time", TimestampType(), True),
    StructField("feature", StringType(), True),
    StructField("value", FloatType(), True),
    StructField("is_outlier_kde", BooleanType(), True),
    StructField("is_outlier_ewma", BooleanType(), True),
    StructField("is_outlier_arima", BooleanType(), True),
    StructField("forecast", FloatType(), True),
    StructField("lo", FloatType(), True),
    StructField("hi", FloatType(), True),
])

def apply_kde_ewma_arima_ensemble_with_mlflow(pdf: pd.DataFrame, params: dict = None) -> pd.DataFrame:
    """
    Apply KDE, EWMA, and ARIMA anomaly detectors to a single (sn, feature) group.
    Logs separate and combined anomaly metrics to MLflow.
    Returns only rows where at least one detector marks the observation as an outlier.
    """

    import mlflow
    mlflow.set_tracking_uri("http://njbbvmaspd11:5001")
    mlflow.set_experiment("Novelty_Detection_All_Models")

    if pdf.empty:
        return pd.DataFrame(columns=[
            "sn","time","feature","value",
            "is_outlier_kde","is_outlier_ewma",
            "is_outlier_arima","forecast","lo","hi"
        ])

    pdf = pdf.copy()
    pdf["time"] = pd.to_datetime(pdf["time"], errors="coerce")
    pdf["value"] = pd.to_numeric(pdf["value"], errors="coerce")
    pdf = pdf.sort_values("time").reset_index(drop=True)

    sn_id = pdf["sn"].iloc[0]
    feature_id = pdf["feature"].iloc[0]

    with mlflow.start_run(nested=True, run_name=f"Ensemble-{sn_id}-{feature_id}"):

        try:
            # Log basic parameters
            mlflow.log_param("sn", sn_id)
            mlflow.log_param("feature", feature_id)
            mlflow.log_metric("n_points", len(pdf))

            # Track threshold parameters if provided
            if params:
                for k, v in params.items():
                    mlflow.log_param(k, v)

            if len(pdf) < params.get("min_training_points", 10):
                mlflow.log_metric("ensemble_anomalies_detected", 0)
                return pd.DataFrame(columns=all_schema.names)

            # ===== KDE Detector =====
            kde = FeaturewiseKDENoveltyDetector(
                df=pdf,
                feature_col="value",
                time_col="time",
                train_idx="all",
                new_idx=slice(-1, None),
                filter_percentile=params.get("filter_percentile", 99),
                threshold_percentile=params.get("threshold_percentile", 95),
                anomaly_direction=params.get("anomaly_direction", "low"),
            )
            out_kde = kde.fit()[["sn","time","value","is_outlier"]].rename(columns={"is_outlier": "is_outlier_kde"})
            mlflow.log_metric("kde_anomalies", out_kde["is_outlier_kde"].sum())

            # ===== EWMA Detector =====
            ewma = EWMAAnomalyDetector(
                df=pdf,
                feature="value",
                timestamp_col="time",
                recent_window_size=params.get("recent_window_size", 1),
                window=params.get("window", 100),
                no_of_stds=params.get("no_of_stds", 3.0),
                n_shift=params.get("n_shift", 1),
                anomaly_direction=params.get("anomaly_direction", "low"),
                scaler=params.get("scaler", None),
                min_std_ratio=params.get("min_std_ratio", 0.01),
                use_weighted_std=params.get("use_weighted_std", False),
            )
            out_ewma = ewma.fit()[["sn","time","value","is_outlier"]].rename(columns={"is_outlier": "is_outlier_ewma"})
            mlflow.log_metric("ewma_anomalies", out_ewma["is_outlier_ewma"].sum())

            # ===== ARIMA Detector =====
            detector = ARIMAAnomalyDetectorSM(
                df=pdf,
                time_col="time",
                feature="value",
                order=(1,0,1),
                confidence_level=params.get("confidence_level", 0.995),
                anomaly_direction='lower',
                horizon=1,
                freq=params.get("freq", "5min"),
                fill_method=params.get("fill_method", "ffill")
            )
            result_df = detector.run()
            column_map = {
                "sn":"sn", "ds":"time", "actual":"value",
                "anomaly":"is_outlier_arima",
                "forecast":"forecast", "lo":"lo", "hi":"hi"
            }

            if result_df.empty:
                out_arima = pd.DataFrame(columns=column_map.values())
                mlflow.log_metric("arima_anomalies", 0)
            else:
                out_arima = result_df[list(column_map.keys())].rename(columns=column_map)
                mlflow.log_metric("arima_anomalies", out_arima["is_outlier_arima"].sum())

            # ===== Merge All Outputs =====
            base = pdf[["sn","time","feature","value"]]
            out = (
                base.merge(out_kde, on=["sn","time","value"], how="left")
                    .merge(out_ewma, on=["sn","time","value"], how="left")
                    .merge(out_arima, on=["sn","time","value"], how="left")
            )

            # Fill missing with defaults
            out["is_outlier_kde"] = out["is_outlier_kde"].fillna(False)
            out["is_outlier_ewma"] = out["is_outlier_ewma"].fillna(False)
            out["is_outlier_arima"] = out["is_outlier_arima"].fillna(False)

            # Filter anomalies
            out_anomalies = out[
                out["is_outlier_kde"] | out["is_outlier_ewma"] | out["is_outlier_arima"]
            ]

            # Log final count of anomalies (ensemble union)
            mlflow.log_metric("ensemble_anomalies_detected", len(out_anomalies))

            return out_anomalies[all_schema.names]

        except Exception as e:
            mlflow.log_param("error", str(e))
            mlflow.log_metric("ensemble_anomalies_detected", 0)
            return pd.DataFrame(columns=all_schema.names)
