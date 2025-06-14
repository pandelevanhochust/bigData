import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Kafka settings
    kafka_bootstrap_servers: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "13.228.128.157:9092")
    kafka_topic_input: str = os.getenv("KAFKA_TOPIC_INPUT", "ml_input_data")
    kafka_group_id: str = os.getenv("KAFKA_GROUP_ID", "fraud_detection_consumer_group")

    # API settings
    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    api_port: int = int(os.getenv("API_PORT", "8000"))
    api_title: str = os.getenv("API_TITLE", "Fraud Detection XGBoost Service")

    # Model settings
    model_path: str = os.getenv("MODEL_PATH", "./xgboost_model.pkl")

    # Server settings
    model_server_host: str = os.getenv("MODEL_SERVER_HOST", "13.214.239.8")
    model_server_port: int = int(os.getenv("MODEL_SERVER_PORT", "8000"))

    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    class Config:
        env_file = ".env"


settings = Settings()