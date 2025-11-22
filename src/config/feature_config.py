
# ============================================================
# Configuration
# ============================================================
HDFS_NAMENODE = 'hdfs://njbbepapa1.nss.vzwnet.com:9000'
BASE_DIR = "/user/kovvuve/owl_history_v3/date="
TIME_COL = "time"

feature_groups = {
    "signal_quality": ["4GRSRP", "4GRSRQ", "SNR", "4GSignal", "BRSRP", "RSRQ", "5GSNR", "CQI"],
    "throughput_data": [
        "LTEPDSCHPeakThroughput", "LTEPDSCHThroughput",
        "LTEPUSCHPeakThroughput", "LTEPUSCHThroughput",
        "5GNRPDSCHThroughput", "5GNRPUSCHThroughput",
        "5GNRPDSCHPeakThroughput", "5GNRPUSCHPeakThroughput",
    ],
}
ALL_FEATURES = feature_groups["signal_quality"] + feature_groups["throughput_data"]
ZERO_LIST = ["RSRQ", "4GRSRQ", "4GRSRP", "BRSRP"]

