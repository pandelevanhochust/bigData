from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime

class PredictionInput(BaseModel):
    features: Dict[str, Any]

class PredictionOutput(BaseModel):
    prediction: float
    probability: Optional[List[float]] = None

class KafkaMessage(BaseModel):
    data: Dict[str, Any]
    message_id: str
    timestamp: datetime
    source: Optional[str] = None

class HealthCheck(BaseModel):
    status: str
    timestamp: datetime
    model_loaded: bool
    kafka_connected: bool