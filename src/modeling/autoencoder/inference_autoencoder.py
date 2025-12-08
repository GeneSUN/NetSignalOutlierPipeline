import mlflow

if __name__ == "__main__":
    mlflow.set_tracking_uri("http://njbbvmaspd11:5001")
    mlflow.set_experiment("Autoencoder_Anomaly_Detection")
    # Load the registered model
    model = mlflow.pyfunc.load_model("models:/Autoencoder_Anomaly_Detection/1")
    print(model.metadata)
    # Now you can use model.predict() with appropriate input