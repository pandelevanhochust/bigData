from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime
import uvicorn

app = FastAPI(title="Fraud Detection API", version="1.0.0")

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173/", "https://54.251.172.36:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class Location(BaseModel):
    city: str
    country: str
    lat: float
    lon: float

class FraudPrediction(BaseModel):
    is_fraud: bool
    fraud_score: float
    confidence: str
    anomaly_score: Optional[float] = None

class Transaction(BaseModel):
    transaction_id: str
    user_id: str
    amount: float
    merchant_id: str
    merchant_category: str
    location: Location
    timestamp: str
    card_type: str
    payment_method: str
    hour: int
    day_of_week: int
    is_weekend: bool
    previous_transaction_minutes: int
    account_balance: float
    fraud_prediction: FraudPrediction
    processed_at: str
    processing_time_ms: int

class TransactionSummary(BaseModel):
    total_transactions: int
    fraud_transactions: int
    fraud_rate: float
    total_amount: float
    fraud_amount: float
    avg_processing_time: float

# In-memory storage (for demonstration only)
transactions_db: List[Dict] = []

@app.get("/")
async def root():
    return {"message": "Fraud Detection API", "status": "running"}

@app.post("/api/transactions")
async def create_transaction(transaction: Transaction):
    transactions_db.append(transaction.dict())
    return {"status": "success", "transaction_id": transaction.transaction_id}

@app.get("/api/transactions")
async def get_transactions():
    return transactions_db

@app.get("/api/transactions/summary", response_model=TransactionSummary)
async def get_transactions_summary():
    total = len(transactions_db)
    frauds = [t for t in transactions_db if t['fraud_prediction']['is_fraud']]
    fraud_total = sum(t['amount'] for t in frauds)
    total_amount = sum(t['amount'] for t in transactions_db)
    avg_time = sum(t['processing_time_ms'] for t in transactions_db) / total if total else 0
    fraud_rate = (len(frauds) / total) * 100 if total else 0

    return TransactionSummary(
        total_transactions=total,
        fraud_transactions=len(frauds),
        fraud_rate=round(fraud_rate, 2),
        total_amount=round(total_amount, 2),
        fraud_amount=round(fraud_total, 2),
        avg_processing_time=round(avg_time, 2),
    )

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
