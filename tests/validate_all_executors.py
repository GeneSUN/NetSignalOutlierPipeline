from pyspark.sql import SparkSession
if __name__ == "__main__":
    spark = SparkSession.builder.getOrCreate()
    sc = spark.sparkContext

    # Distribute the module to executors
    sc.addPyFile("/usr/apps/vmas/scripts/ZS/NetSignalOutlierPipeline/src/")

    # Try importing on executors
    def test_import(_):
        try:
            from kde_ewma_runtime import mlflow_tracked_kde_ewma_ensemble, both_schema
            return "SUCCESS: Module imported on executor"
        except Exception as e:
            return f"FAILED: {str(e)}"

    # Run test across executors
    results = sc.parallelize(range(5), 5).map(test_import).collect()

    for res in results:
        print(res)



    sc.addPyFile("/usr/apps/vmas/scripts/ZS/NetSignalOutlierPipeline/src/modeling/detectors/kde_detector.py")

    # Try importing on executors
    def test_import(_):
        try:
            from kde_detector import FeaturewiseKDENoveltyDetector
            return "SUCCESS: Module imported on executor"
        except Exception as e:
            return f"FAILED: {str(e)}"

    # Run test across executors
    results = sc.parallelize(range(5), 5).map(test_import).collect()

    for res in results:
        print(res)
