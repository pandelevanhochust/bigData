import asyncio
import threading
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from model.config import settings
from model.model_service import model_service
from kafka.consumer import kafka_consumer_service
from model.schemas import PredictionInput, PredictionOutput, HealthCheck

# Setup logging
logger.add("logs/app.log", rotation="500 MB", level=settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting XGBoost ML Service...")

    # Start Kafka consumer in background thread
    kafka_thread = threading.Thread(target=kafka_consumer_service.start_consuming, daemon=True)
    kafka_thread.start()

    yield

    # Shutdown
    logger.info("Shutting down XGBoost ML Service...")
    kafka_consumer_service.stop_consuming()


# Create FastAPI app
app = FastAPI(
    title=settings.api_title,
    description="XGBoost Model Service with Kafka Integration",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "XGBoost ML Service is running", "timestamp": datetime.utcnow()}


@app.get("/health", response_model=HealthCheck)
async def health_check():
    """Health check endpoint"""
    return HealthCheck(
        status="healthy" if model_service.is_model_loaded() else "unhealthy",
        timestamp=datetime.utcnow(),
        model_loaded=model_service.is_model_loaded(),
        kafka_connected=kafka_consumer_service.is_connected()
    )


@app.post("/predict", response_model=PredictionOutput)
async def predict(prediction_input: PredictionInput):
    """Direct prediction endpoint (for testing or direct API calls)"""
    try:
        if not model_service.is_model_loaded():
            raise HTTPException(status_code=503, detail="Model not loaded")

        result = model_service.predict(prediction_input)
        return result

    except Exception as e:
        logger.error(f"Prediction error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/model/info")
async def model_info():
    """Get model information"""
    return {
        "model_loaded": model_service.is_model_loaded(),
        "model_version": model_service.model_version,
        "feature_names": model_service.feature_names,
        "model_path": settings.model_path
    }


@app.post("/model/reload")
async def reload_model():
    """Reload the model"""
    try:
        success = model_service.load_model()
        if success:
            return {"message": "Model reloaded successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to reload model")
    except Exception as e:
        logger.error(f"Model reload error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
        log_level=settings.log_level.lower()
    )