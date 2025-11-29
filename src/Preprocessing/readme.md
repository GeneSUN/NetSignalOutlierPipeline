# 📘 Feature Engineering for Real-Time ML Anomaly Detection

## 📑 Table of Contents

- [📘 Feature Engineering for Real-Time ML Anomaly Detection](#-feature-engineering-for-real-time-ml-anomaly-detection)
  - [Preprocessing Overview](#preprocessing-overview)
  - [🥉 Bronze Layer — Raw Data Ingestion](#-1-bronze-layer--raw-data-ingestion-data-engineering-layer)
  - [🥈 Silver Layer — Preprocessing & Data Quality Enforcement](#-2-silver-layer--preprocessing--data-quality-enforcement)
  - [🟡 Gold Layer — Model-Ready Feature Tensor Construction](#-3-gold-layer--model-ready-feature-tensor-construction)
    - [3.1 Sequence-Based Models Input](#31-sequence-based-models)
    - [3.2 Unpivot Transformation for Distributed Computing](#32-unpivot-transformation-for-distributed-computing)
  - [Reference Code & Notebook Links](#example)

## Preprocessing Overview

Real-time anomaly detection needs clean and model-ready data — especially when the upstream source is raw  device logs.

| rowkey | ts | Tplg_Data_model_name | Station_Data_stats_data | Station_Data_connect_data | Diag_Result_link_rate |
|--------|----|-----------------------|--------------------------|----------------------------|------------------------|
| 3473-ACE43913473_... | 1764212396000 | FWF100V5L | {"rt":"0","es":"0...} | {1764212396000, 8...} | {720Mbps, 6Mbps, ...} |
| 2357-ACZ44502357_... | 1764212397000 | CR1000A | {"rt":"0","es":"0...} | {1764212397000, 1...} | {309Mbps, 720Mbps...} |
| 3303-G40212203120... | 1764212402000 | G3100 | {"rt":"0","es":"0...} | {1764212402000, 4...} | {72Mbps, 1Mbps, 7...} |

```
root
|-- rowkey: string (nullable = true)
|-- ts: string (nullable = true)
|-- Tplg_Data_model_name: string (nullable = true)
|-- Tplg_Data_fw_ver: string (nullable = true)
|-- Diag_Result_band_steer: struct (nullable = true)
| |-- ts: string (nullable = true)
| |-- from: string (nullable = true)
| |-- to: string (nullable = true)
| |-- sta_type: string (nullable = true)
| |-- ...
| |-- intend: struct (nullable = true)
| | |-- name: string (nullable = true)
| | |-- mac: string (nullable = true)
| | |-- essid: string (nullable = true)
| | |-- band: string (nullable = true)
| | |-- channel: string (nullable = true)
| | |-- ch_load: string (nullable = true)
| | |-- rssi: string (nullable = true)
| | |-- phyrate: string (nullable = true)
| |-- orig: struct (nullable = true)
| | |-- name: string (nullable = true)
| | |-- mac: string (nullable = true)
| | |-- essid: string (nullable = true)
| | |-- ...
| |-- target: struct (nullable = true)
| | |-- name: string (nullable = true)
| | |-- mac: string (nullable = true)
| | |-- ...
|-- Diag_Result_ap_steer: struct (nullable = true)
| |-- ...
|-- Diag_Result_association: struct (nullable = true)
| |-- ...
|-- Diag_Result_roaming: struct (nullable = true)
| |-- ...
|-- Diag_Result_beacon_report: struct (nullable = true)
| |-- ...
|-- Station_Data_connect_data: struct (nullable = true)
| |-- ...
|-- Diag_Result_link_rate: struct (nullable = true)
| |-- ...
```


This document explains the feature engineering workflow used in our 5G Home real-time novelty detection pipeline, following a simple Bronze → Silver → Gold structure.

- **Bronze:** Raw logs pulled from S3 into HDFS by Data Engineering  
- **Silver:** Cleaned, normalized, and reshaped device metrics  
- **Gold:** Final model features ready for real-time detection

<img width="800" height="1100" alt="image" src="https://github.com/user-attachments/assets/d709b2f7-29c6-4082-99d3-2783f2a9c323" />

The **goal** is to convert noisy device logs into clean and model-ready features for real-time anomaly detection.


```
=== 3. Testing Wide → Long Transformation ===
+-----------+-------------------+-----------+-------------------+
|sn         |time               |feature    |value              |
+-----------+-------------------+-----------+-------------------+
|ACR42006080|2025-11-21 19:05:18|4GRSRP     |-55.639322157434435|
|ACR42006080|2025-11-21 19:05:18|4GRSRQ     |-5.658491253644314 |
|ACR42006080|2025-11-21 19:05:18|SNR        |null               |
|ACR42006080|2025-11-21 19:05:18|4GSignal   |0.0                |
|ACR42006080|2025-11-21 19:05:18|BRSRP      |-98.0              |
|ACR42006080|2025-11-21 19:05:18|RSRQ       |-11.2              |
|ACR42006080|2025-11-21 19:05:18|5GSNR      |10.8               |
|ACR42006080|2025-11-21 19:05:18|CQI        |10.0               |
|ACR42006080|2025-11-21 19:05:18|TxPDCPBytes|null               |
|ACR42006080|2025-11-21 19:05:18|RxPDCPBytes|null               |
+-----------+-------------------+-----------+-------------------+
```

```
=== 4. Testing Subseries Splitting ===
| time            | RSRQ  | 5GSNR | CQI | series_id                 |
|-----------------|-------|-------|-----|---------------------------|
| 11/21/25 19:05  | -11.2 | 10.8  | 10  | ACR42006080_20251121190518 |
| 11/21/25 19:10  | -12   | 9     | 14  | ACR42006080_20251121190518 |
| 11/21/25 19:15  | -11.2 | 14.8  | 9   | ACR42006080_20251121190518 |
| 11/21/25 19:21  | -11.5 | 9.8   | 14  | ACR42006080_20251121190518 |
| 11/21/25 19:26  | -11.5 | 12.5  | 7   | ACR42006080_20251121190518 |
| 11/21/25 19:31  | -11.5 | 10.2  | 14  | ACR42006080_20251121190518 |
| 11/21/25 19:36  | -11.2 | 12.5  | 5   | ACR42006080_20251121190518 |
| 11/21/25 19:42  | -11.2 | 14.5  | 13  | ACR42006080_20251121190518 |
| 11/21/25 19:47  | -11.2 | 10    | 6   | ACR42006080_20251121190518 |
| 11/21/25 19:52  | -11.5 | 9.2   | 15  | ACR42006080_20251121190518 |

```



---

## 🥉 1. Bronze Layer — Raw Data Ingestion (Data Engineering Layer)

The raw data is ingested by Data Engineering from S3 → HDFS, using scheduled ingestion jobs.

At this stage, no feature engineering occurs.
- Preserve data exactly as received
- Provide a stable foundation for downstream ML pipeline
- Timestamp + partition checks

---

## 🥈 2. Silver Layer — Preprocessing & Data Quality Enforcement

✔ Key Goals

1. Convert Strings to Numerical Types
2. Forward Fill (ffill): Used when instrumentation gaps or network delays produce missing values:
3. zeros are treated as nulls: like age, zero is not impossible; some machine use fill null with zero
  <img width="489" height="389" alt="image" src="https://github.com/user-attachments/assets/6e728555-4ad7-49dd-b7bc-58f36ed2a609" />

4. Aggregation (agg): Aggregate raw events into a fixed frequency (default: hourly):
  <img width="463" height="547" alt="image" src="https://github.com/user-attachments/assets/73c478e5-2b23-4247-8bfa-573918a2fd35" />

5. Differencing (diff): Compute smoothed increments
  
  <img width="405" height="547" alt="image" src="https://github.com/user-attachments/assets/5cb20652-7db1-4de7-a959-ef4108fa3edc" />

6. Log Transform (log)

  <img width="489" height="490" alt="image" src="https://github.com/user-attachments/assets/4da92a80-8c3a-4178-9bd6-bcaa081f4a6c" />

  



The full preprocessing implementation is available in the repository:

- **[TimeSeriesFeatureTransformerPandas.py](https://github.com/GeneSUN/Anomaly_Detection_toolkit/blob/main/Preprocess/TimeSeriesFeatureTransformerPandas.py#L6
)**  
  → Core preprocessing logic (aggregation, diff, log1p, ffill, zero→null handling, etc.)  
  → [Source code](https://github.com/GeneSUN/Anomaly_Detection_toolkit/blob/main/Preprocess/TimeSeriesFeatureTransformerPandas.py#L6
):  
  
To see how the transformer is used end-to-end, refer to the demo notebook:

- **[Colab Usage Example](https://colab.research.google.com/drive/1z6PtK9nOo6h2e05E_UZAjFHDD-esBA-T)**  
  → Walks through loading raw data, running the transformer, visualizing outputs, and preparing series for anomaly detection  
  → [Notebook](https://colab.research.google.com/drive/1z6PtK9nOo6h2e05E_UZAjFHDD-esBA-T):  
  

---

## 🟡 3. Gold Layer — Model-Ready Feature Tensor Construction

The Gold layer prepares data for real-time anomaly detection models, 

### 3.1. sequence-based models

This is for Deep learning model such as LSTM AE, GRU, CNN, ARIMA, seasonal decomposition, etc.).
- https://github.com/GeneSUN/Anomaly_Detection_toolkit/blob/main/Preprocess/TimeSeriesFeatureTransformerPandas.py#L177
- https://colab.research.google.com/drive/1z6PtK9nOo6h2e05E_UZAjFHDD-esBA-T#scrollTo=DNx790E7D097
  
<img width="503" height="990" alt="image" src="https://github.com/user-attachments/assets/d571d506-620f-4253-8c01-b016e80c5584" />

### 3.2. unpivot transformation for distributed computing

```python

def unpivot_wide_to_long(df, time_col, feature_cols):
    # Build a stack(expr) for unpivot: (feature, value)
    n = len(feature_cols)
    expr = "stack({n}, {pairs}) as (feature, value)".format(
        n=n,
        pairs=", ".join([f"'{c}', `{c}`" for c in feature_cols])
    )
    return df.select("sn", time_col, F.expr(expr))
```

**❌ Original Wide Dataset (Not Suitable for Distributed Processing)**

| Serial Number | feature_1 | feature_2 | feature_3 |
|--------------|-----------|-----------|-----------|
| 1            | x1        | y1        | z1        |
| 2            | x2        | y2        | z2        |
| 3            | x3        | y3        | z3        |
| 4            | x4        | y4        | z4        |
| 5            | x5        | y5        | z5        |

Problems with this format: PySpark cannot **parallelize feature columns** — each feature becomes a separate column, not a separate row.

**✔ Unpivoted (Long Format) Dataset — Ready for Distributed Computing**

| Serial Number | feature     | value |
|--------------|-------------|-------|
| 1            | feature_1   | x1    |
| 1            | feature_2   | y1    |
| 1            | feature_3   | z1    |
| 2            | feature_1   | x2    |
| 2            | feature_2   | y2    |
| 2            | feature_3   | z2    |
| ...          | ...         | ...   |


Once unpivoted, PySpark can split the work, Executors can now process every feature in parallel:

- Executor A → all rows of `feature_1`

| Serial Number | feature   | value |
|--------------|-----------|-------|
| 1            | feature_1 | x1    |
| 5            | feature_1 | x2    |
| 10           | feature_1 | x3    |
  
- Executor B → all rows of `feature_2`
- Executor C → all rows of `feature_3`
- ...
- Executor N → all rows of `feature_k`


---

## Example:

**[test_preprocess.py](https://github.com/GeneSUN/NetSignalOutlierPipeline/blob/main/tests/test_preprocess.py)**


This script runs an end-to-end test of the preprocessing pipeline by 
- loading raw HDFS logs,
- cleaning and conditioning features,
- transforming wide data into long series, and
- splitting them into model-ready subseries for anomaly detection.


