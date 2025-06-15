from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from model_service import model_service
from schemas import PredictionInput, PredictionOutput, HealthCheck
from datetime import datetime
from loguru import logger
import requests

app = FastAPI(title=settings.api_title, version="1.0.0")
TRANSACTION_API_URL = "http://54.251.172.36:8000/api/transactions"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Service running", "timestamp": datetime.utcnow()}

@app.get("/health", response_model=HealthCheck)
async def health():
    return HealthCheck(status="healthy", timestamp=datetime.utcnow(), model_loaded=model_service.is_model_loaded(), kafka_connected=True)

@app.post("/predict", response_model=PredictionOutput)
async def predict(input: PredictionInput):
    try:
        return model_service.predict(input)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/transactions")
async def process_transaction(transaction_data: dict):
    """
    Receive transaction → predict fraud → send result to external Transaction API
    """
    try:
        logger.info(f"Received transaction: {transaction_data.get('transaction_id', 'unknown')}")

        # Build PredictionInput and predict
        prediction_input = PredictionInput(**transaction_data)
        result = model_service.predict(prediction_input)

        # Prepare enriched data
        enriched_transaction = {
            **transaction_data,
            "prediction": result.prediction,
            "fraud_probability": result.probability,
            "predicted_at": datetime.utcnow().isoformat()
        }

        # POST to external Transaction API
        response = requests.post(TRANSACTION_API_URL, json=enriched_transaction)
        if response.status_code == 200:
            logger.info(f"[✓] Sent prediction to Transaction API")
        else:
            logger.warning(f"[!] Failed to forward prediction: {response.status_code} {response.text}")

        return {
            "status": "success",
            "transaction_id": prediction_input.transaction_id,
            "prediction": result.dict()
        }

    except Exception as e:
        logger.error(f"Prediction and forwarding error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")