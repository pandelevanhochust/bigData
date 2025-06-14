import asyncio
import threading
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from config import settings
from model_service import model_service
from schemas import PredictionInput, PredictionOutput, HealthCheck

# Setup logging
logger.add("logs/fraud_detection.log", rotation="500 MB", level=settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting Fraud Detection Model Service...")

    # Load the model on startup
    try:
        model_loaded = model_service.load_model()
        if model_loaded:
            logger.info("Model loaded successfully on startup")
        else:
            logger.error("Failed to load model on startup")
    except Exception as e:
        logger.error(f"Error loading model on startup: {e}")

    yield

    # Shutdown
    logger.info("Shutting down Fraud Detection Model Service...")


# Create FastAPI app
app = FastAPI(
    title=settings.api_title,
    description="XGBoost Fraud Detection Model Service",
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
    return {
        "message": "Fraud Detection Model Service is running",
        "timestamp": datetime.utcnow(),
        "status": "active"
    }


@app.get("/health", response_model=HealthCheck)
async def health_check():
    """Health check endpoint"""
    model_loaded = model_service.is_model_loaded()
    return HealthCheck(
        status="healthy" if model_loaded else "unhealthy",
        timestamp=datetime.utcnow(),
        model_loaded=model_loaded,
        kafka_connected=True  # This should be updated if you have Kafka health check logic
    )


@app.post("/predict", response_model=PredictionOutput)
async def predict(prediction_input: PredictionInput):
    """Prediction endpoint for receiving data from Kafka consumer"""
    try:
        logger.info(f"Received prediction request for transaction: {prediction_input.transaction_id}")

        if not model_service.is_model_loaded():
            logger.error("Model not loaded")
            raise HTTPException(status_code=503, detail="Model not loaded")

        result = model_service.predict(prediction_input)

        logger.info(f"Prediction completed for transaction {prediction_input.transaction_id}: "
                    f"fraud_probability={result.fraud_probability}, is_fraud={result.is_fraud}")

        return result

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(
            f"Prediction error for transaction {getattr(prediction_input, 'transaction_id', 'unknown')}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


# Updated endpoint to match what your Kafka consumer expects
@app.post("/api/transactions")
async def process_transaction(transaction_data: dict):
    """
    Process transaction data from Kafka consumer
    This endpoint matches what your Kafka consumer is calling
    """
    try:
        logger.info(f"Received transaction data: {transaction_data.get('transaction_id', 'unknown')}")

        # Convert transaction dict to PredictionInput
        prediction_input = PredictionInput(**transaction_data)

        # Use the existing predict logic
        if not model_service.is_model_loaded():
            logger.error("Model not loaded")
            raise HTTPException(status_code=503, detail="Model not loaded")

        result = model_service.predict(prediction_input)

        logger.info(f"Transaction processed: {prediction_input.transaction_id}, "
                    f"fraud_probability={result.fraud_probability}")

        return {
            "status": "success",
            "transaction_id": prediction_input.transaction_id,
            "prediction": result.dict()
        }

    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=422, detail=f"Invalid transaction data: {str(e)}")
    except Exception as e:
        logger.error(f"Transaction processing error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Transaction processing failed: {str(e)}")


@app.get("/model/info")
async def model_info():
    """Get model information"""
    try:
        return {
            "model_loaded": model_service.is_model_loaded(),
            "model_version": getattr(model_service, 'model_version', None),
            "feature_names": getattr(model_service, 'feature_names', []),
            "model_path": settings.model_path,
            "server_info": {
                "host": settings.model_server_host if hasattr(settings, 'model_server_host') else settings.api_host,
                "port": settings.api_port,
                "title": settings.api_title
            }
        }
    except Exception as e:
        logger.error(f"Error getting model info: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get model info: {str(e)}")


@app.post("/model/reload")
async def reload_model():
    """Reload the model"""
    try:
        logger.info("Attempting to reload model...")
        success = model_service.load_model()

        if success:
            logger.info("Model reloaded successfully")
            return {
                "message": "Model reloaded successfully",
                "timestamp": datetime.utcnow(),
                "model_loaded": model_service.is_model_loaded()
            }
        else:
            logger.error("Failed to reload model")
            raise HTTPException(status_code=500, detail="Failed to reload model")

    except Exception as e:
        logger.error(f"Model reload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Model reload failed: {str(e)}")


@app.get("/stats")
async def get_stats():
    """Get API statistics"""
    return {
        "status": "running",
        "model_loaded": model_service.is_model_loaded(),
        "timestamp": datetime.utcnow(),
        "uptime": "N/A"  # You can implement uptime tracking if needed
    }


# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return {"error": "Endpoint not found", "detail": str(exc)}


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    logger.error(f"Internal server error: {str(exc)}")
    return {"error": "Internal server error", "detail": "Something went wrong"}


if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting server on {settings.api_host}:{settings.api_port}")

    uvicorn.run(
        "fraud_detection:app",  # Updated to match your file name
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
        log_level=settings.log_level.lower(),
        access_log=True
    )