import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    model_path: str = os.getenv("MODEL_PATH", "xgboost_model.pkl")
    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    api_port: int = int(os.getenv("API_PORT", 8000))
    api_title: str = "Fraud Detection API"
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

settings = Settings()